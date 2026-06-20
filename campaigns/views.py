import csv
import io
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.db.models import Count, Q
from .models import Campaign, ContactUpload, Contact, Task, ProofSubmission
from .forms import (CampaignForm, CampaignEditForm, CSVUploadForm,
                    ProofForm, TaskSearchForm, ContactUploadNameForm)


# ─── LOGIN ───────────────────────────────────────────────────────────────────

# Uses Django's built-in login view; template at registration/login.html


# ─── SIGNUP ──────────────────────────────────────────────────────────────────

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created! Welcome, {user.username}.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    campaigns = Campaign.objects.all().order_by('-created_at')
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='completed').count()
    pending_tasks = Task.objects.filter(status__in=['pending', 'visited']).count()
    rejected_tasks = Task.objects.filter(status='rejected').count()
    active_campaign = Campaign.objects.filter(status='active').first()
    contact_uploads = ContactUpload.objects.all().order_by('-created_at')

    completion_rate = 0
    if total_tasks > 0:
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)

    context = {
        'campaigns': campaigns,
        'active_campaign': active_campaign,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'rejected_tasks': rejected_tasks,
        'completion_rate': completion_rate,
        'contact_uploads': contact_uploads,
    }
    return render(request, 'campaigns/dashboard.html', context)


# ─── CONTACT UPLOAD (STANDALONE) ─────────────────────────────────────────────

@login_required
def contact_upload_list(request):
    uploads = ContactUpload.objects.all().order_by('-created_at')
    for u in uploads:
        u.contact_count = u.contacts.count()
    return render(request, 'campaigns/contact_upload_list.html', {'uploads': uploads})


@login_required
def contact_upload_csv(request):
    if request.method == 'POST':
        name_form = ContactUploadNameForm(request.POST)
        csv_form = CSVUploadForm(request.POST, request.FILES)
        if csv_form.is_valid() and name_form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            columns = reader.fieldnames

            if not columns:
                messages.error(request, 'CSV file has no columns.')
                return redirect('contact_upload_csv')

            request.session['csv_columns'] = columns
            request.session['csv_content'] = decoded
            request.session['csv_filename'] = csv_file.name
            request.session['csv_upload_name'] = name_form.cleaned_data.get('name', '')

            return redirect('contact_upload_map_columns')
    else:
        name_form = ContactUploadNameForm()
        csv_form = CSVUploadForm()

    return render(request, 'campaigns/contact_upload_csv.html', {
        'name_form': name_form,
        'csv_form': csv_form,
    })


@login_required
def contact_upload_map_columns(request):
    csv_columns = request.session.get('csv_columns', [])
    csv_content = request.session.get('csv_content')

    if not csv_columns or not csv_content:
        messages.error(request, 'Please upload a CSV file first.')
        return redirect('contact_upload_csv')

    variable_labels = {
        '': '-- Skip --', 'first_name': 'First Name', 'last_name': 'Last Name',
        'full_name': 'Full Name', 'email': 'Email', 'domain': 'Domain',
        'profile': 'Profile URL', 'company': 'Company', 'phone': 'Phone',
    }

    if request.method == 'POST':
        mapping = {}
        profile_found = False
        for col in csv_columns:
            var = request.POST.get(f'map_{col}', '')
            if var:
                mapping[col] = var
                if var == 'profile':
                    profile_found = True

        if not profile_found:
            messages.error(request, 'You must map at least one column to "Profile URL".')
            return redirect('contact_upload_map_columns')

        # Create the ContactUpload
        upload_name = request.session.get('csv_upload_name', '')
        filename = request.session.get('csv_filename', '')
        contact_upload = ContactUpload.objects.create(
            name=upload_name or filename,
            filename=filename,
        )

        # Process CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        contacts_created = 0
        for row in reader:
            data = {}
            for col, var in mapping.items():
                val = row.get(col, '').strip()
                data[var] = val

            if not data.get('profile'):
                continue

            Contact.objects.create(
                contact_upload=contact_upload,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                full_name=data.get('full_name', '') or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                email=data.get('email', ''),
                domain=data.get('domain', ''),
                profile_url=data['profile'],
                company=data.get('company', ''),
                phone=data.get('phone', ''),
            )
            contacts_created += 1

        # Clean up session
        for key in ['csv_columns', 'csv_content', 'csv_filename', 'csv_upload_name']:
            if key in request.session:
                del request.session[key]

        messages.success(request, f'Imported {contacts_created} contacts as "{contact_upload.name}"!')
        return redirect('contact_upload_list')

    context = {
        'csv_columns': csv_columns,
        'variable_labels': variable_labels,
        'upload_name': request.session.get('csv_upload_name', request.session.get('csv_filename', '')),
    }
    return render(request, 'campaigns/map_columns.html', context)


@login_required
def contact_upload_detail(request, upload_id):
    upload = get_object_or_404(ContactUpload, id=upload_id)
    contacts = upload.contacts.all()
    campaign_count = upload.campaigns.count()
    context = {
        'upload': upload,
        'contacts': contacts,
        'campaign_count': campaign_count,
    }
    return render(request, 'campaigns/contact_upload_detail.html', context)


@login_required
def contact_upload_delete(request, upload_id):
    upload = get_object_or_404(ContactUpload, id=upload_id)
    if request.method == 'POST':
        # Remove reference from any campaigns
        upload.campaigns.all().update(contact_upload=None)
        upload.delete()
        messages.success(request, 'Contact upload deleted.')
        return redirect('contact_upload_list')
    return render(request, 'campaigns/contact_upload_confirm_delete.html', {'upload': upload})


# ─── CAMPAIGN CRUD ───────────────────────────────────────────────────────────

@login_required
def campaign_create(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, f'Campaign "{campaign.name}" created!')
            return redirect('campaign_detail', campaign_id=campaign.id)
    else:
        form = CampaignForm()
    return render(request, 'campaigns/campaign_form.html', {'form': form, 'title': 'Create Campaign'})


@login_required
def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    contacts = campaign.contact_upload.contacts.all() if campaign.contact_upload else Contact.objects.none()
    tasks = campaign.tasks.all().order_by('-created_at')

    total = tasks.count()
    completed = tasks.filter(status='completed').count()
    pending = tasks.filter(status='pending').count()
    visited = tasks.filter(status='visited').count()
    rejected = tasks.filter(status='rejected').count()

    from django.contrib.sites.shortcuts import get_current_site
    site_url = f"{request.scheme}://{get_current_site(request)}"

    context = {
        'campaign': campaign,
        'contacts': contacts,
        'tasks': tasks[:50],
        'total_tasks': total,
        'completed_tasks': completed,
        'pending_tasks': pending,
        'visited_tasks': visited,
        'rejected_tasks': rejected,
        'site_url': site_url,
    }
    return render(request, 'campaigns/campaign_detail.html', context)


@login_required
def campaign_edit(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if request.method == 'POST':
        form = CampaignEditForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaign updated!')
            return redirect('campaign_detail', campaign_id=campaign.id)
    else:
        form = CampaignEditForm(instance=campaign)
    return render(request, 'campaigns/campaign_form.html', {'form': form, 'campaign': campaign, 'title': 'Edit Campaign'})


@login_required
def campaign_delete(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'Campaign deleted!')
        return redirect('dashboard')
    return render(request, 'campaigns/campaign_confirm_delete.html', {'campaign': campaign})


@login_required
def campaign_activate(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if campaign.status == 'completed':
        messages.error(request, 'Cannot activate a completed campaign.')
        return redirect('campaign_detail', campaign_id=campaign.id)

    if campaign.status == 'active':
        messages.warning(request, 'Campaign is already active.')
        return redirect('campaign_detail', campaign_id=campaign.id)

    # Need contacts to activate
    if not campaign.contact_upload:
        messages.error(request, 'No contacts assigned. Upload contacts first.')
        return redirect('campaign_edit', campaign_id=campaign.id)

    if campaign.contact_upload.contacts.count() == 0:
        messages.error(request, 'The selected contact upload has no contacts.')
        return redirect('campaign_edit', campaign_id=campaign.id)

    # Deactivate all other campaigns
    Campaign.objects.filter(status='active').update(status='draft')

    # Create tasks from the contact upload contacts
    tasks_created = 0
    for contact in campaign.contact_upload.contacts.all():
        task, created = Task.objects.get_or_create(
            contact=contact,
            campaign=campaign,
            defaults={'status': 'pending'}
        )
        if created:
            tasks_created += 1

    campaign.status = 'active'
    campaign.save()

    messages.success(
        request,
        f'Campaign "{campaign.name}" is now active with {tasks_created} tasks!'
    )
    return redirect('campaign_detail', campaign_id=campaign.id)


@login_required
def campaign_complete(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if request.method == 'POST':
        campaign.status = 'completed'
        campaign.save()
        campaign.tasks.filter(status__in=['pending', 'visited']).update(
            ip_address=None, locked_at=None, status='completed'
        )
        messages.success(request, 'Campaign marked as completed!')
        return redirect('dashboard')
    return render(request, 'campaigns/campaign_confirm_complete.html', {'campaign': campaign})


# ─── STATISTICS ──────────────────────────────────────────────────────────────

@login_required
def campaign_statistics(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    tasks = campaign.tasks.all()

    total = tasks.count()
    status_counts = tasks.values('status').annotate(count=Count('id')).order_by('status')
    status_data = {}
    for item in status_counts:
        status_data[item['status']] = item['count']

    completed = status_data.get('completed', 0)
    completion_rate = round((completed / total * 100), 1) if total > 0 else 0

    overdue = tasks.filter(
        status__in=['pending', 'visited'],
        locked_at__isnull=False,
        locked_at__lte=timezone.now() - timezone.timedelta(minutes=10)
    ).count()

    active_tasks = tasks.filter(
        status__in=['pending', 'visited'],
        locked_at__isnull=False,
        locked_at__gt=timezone.now() - timezone.timedelta(minutes=10)
    ).count()

    context = {
        'campaign': campaign,
        'total': total,
        'status_data': status_data,
        'status_labels': dict(Task.STATUS_CHOICES),
        'completion_rate': completion_rate,
        'overdue': overdue,
        'active_tasks': active_tasks,
        'pending_unlocked': status_data.get('pending', 0),
    }
    return render(request, 'campaigns/statistics.html', context)


# ─── TASK MANAGEMENT ─────────────────────────────────────────────────────────

@login_required
def campaign_tasks(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    tasks = campaign.tasks.all().order_by('-created_at')

    form = TaskSearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data.get('query', '')
        status_filter = form.cleaned_data.get('status', '')

        if query:
            tasks = tasks.filter(
                Q(proof_code__icontains=query) |
                Q(contact__full_name__icontains=query) |
                Q(contact__email__icontains=query) |
                Q(contact__profile_url__icontains=query)
            )
        if status_filter:
            tasks = tasks.filter(status=status_filter)

    paginated = tasks[:100]

    context = {
        'campaign': campaign,
        'tasks': paginated,
        'form': form,
        'total': tasks.count(),
    }
    return render(request, 'campaigns/task_list.html', context)


@login_required
def task_update_status(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        if new_status in ['completed', 'rejected', 'pending', 'pending_review']:
            if new_status in ['rejected', 'pending']:
                task.contact.status = 'pending'
                task.contact.save(update_fields=['status'])
                task.ip_address = None
                task.locked_at = None
                if new_status == 'rejected':
                    task.proof_code = None
            elif new_status == 'completed':
                task.contact.status = 'completed'
                task.contact.save(update_fields=['status'])

            task.status = new_status
            task.save()
            messages.success(request, f'Task marked as {new_status}!')

    return redirect(request.META.get('HTTP_REFERER', 'campaign_detail'))


# ─── SEARCH PROOF ────────────────────────────────────────────────────────────

@login_required
def search_proof(request):
    code = request.GET.get('code', '')
    task = None
    if code:
        try:
            task = Task.objects.get(proof_code=code)
        except Task.DoesNotExist:
            messages.error(request, 'No task found with that proof code.')

    context = {
        'task': task,
        'code': code,
    }
    return render(request, 'campaigns/search_proof.html', context)


@login_required
def proof_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    proofs = task.proofs.all()

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'approve':
            task.status = 'completed'
            task.contact.status = 'completed'
            task.save()
            task.contact.save(update_fields=['status'])
            task.proofs.all().update(status='approved')
            messages.success(request, 'Task approved!')
        elif action == 'reject':
            task.status = 'pending'
            task.contact.status = 'pending'
            task.ip_address = None
            task.locked_at = None
            task.proof_code = None
            task.save()
            task.contact.save(update_fields=['status'])
            task.proofs.all().update(status='rejected')
            messages.success(request, 'Task rejected and released for retry.')
        return redirect('search_proof')

    context = {
        'task': task,
        'proofs': proofs,
    }
    return render(request, 'campaigns/proof_detail.html', context)


# ─── PUBLIC TASK VIEW (NO AUTH REQUIRED) ─────────────────────────────────────

def release_expired_tasks(campaign):
    """Release all visited tasks whose 10-minute lock has expired."""
    cutoff = timezone.now() - timezone.timedelta(minutes=10)
    for t in Task.objects.filter(campaign=campaign, status='visited', locked_at__lte=cutoff):
        t.release_if_expired()


def show_task_root(request):
    """Entry point for workers. Assigns a random available task from the active campaign."""
    active_campaign = Campaign.objects.filter(status='active').first()
    if not active_campaign:
        return render(request, 'campaigns/public_inactive.html', {
            'message': 'No campaign is currently active.'
        })

    # Release expired locks before assigning
    release_expired_tasks(active_campaign)

    # Check if session already owns a task
    assigned_uuid = request.session.get('assigned_task_id')
    if assigned_uuid:
        try:
            existing = Task.objects.get(unique_id=assigned_uuid)
            existing.release_if_expired()
            existing.refresh_from_db()
            if existing.status in ('pending', 'visited'):
                return redirect('show_task_detail', unique_id=existing.unique_id)
        except Task.DoesNotExist:
            pass

    # Assign a random pending task
    task = Task.objects.filter(
        campaign=active_campaign,
        status='pending',
        locked_at__isnull=True,
    ).order_by('?').first()

    if not task:
        return render(request, 'campaigns/public_inactive.html', {
            'message': 'All tasks are currently assigned. Please try again later.'
        })

    now = timezone.now()
    task.ip_address = request.META.get('REMOTE_ADDR', '')
    task.locked_at = now
    task.status = 'visited'
    task.contact.status = 'active'
    task.save()
    task.contact.save(update_fields=['status'])

    request.session['assigned_task_id'] = str(task.unique_id)
    request.session.set_expiry(600)

    return redirect('show_task_detail', unique_id=task.unique_id)


def show_task_detail(request, unique_id):
    task = get_object_or_404(Task, unique_id=unique_id)

    if task.campaign.status != 'active':
        return render(request, 'campaigns/public_inactive.html', {'message': 'This campaign is no longer active.'})

    assigned = request.session.get('assigned_task_id')
    if not assigned or str(unique_id) != str(assigned):
        return redirect('show_task_root')

    task.release_if_expired()
    task.refresh_from_db()

    if task.status == 'pending':
        if 'assigned_task_id' in request.session:
            del request.session['assigned_task_id']
        return redirect('show_task_root')

    if task.status in ('completed', 'rejected', 'pending_review'):
        if 'assigned_task_id' in request.session:
            del request.session['assigned_task_id']
        return render(request, 'campaigns/public_inactive.html', {
            'message': 'This task has already been completed or rejected.'
        })

    contact = task.contact

    def process_vars(text):
        text = text.replace('{first_name}', contact.first_name)
        text = text.replace('{last_name}', contact.last_name)
        text = text.replace('{full_name}', contact.full_name)
        text = text.replace('{email}', contact.email)
        text = text.replace('{domain}', contact.domain)
        text = text.replace('{company}', contact.company)
        text = text.replace('{phone}', contact.phone)
        text = text.replace('{profile}', contact.profile_url)
        return text

    message = process_vars(task.campaign.message_template)
    processed_instruction = process_vars(task.campaign.custom_instruction)

    context = {
        'task': task,
        'contact': contact,
        'campaign': task.campaign,
        'message': message,
        'processed_instruction': processed_instruction,
        'time_remaining': 10,
    }
    return render(request, 'campaigns/public_task.html', context)


def task_done(request, unique_id):
    task = get_object_or_404(Task, unique_id=unique_id)

    if task.campaign.status != 'active':
        return render(request, 'campaigns/public_inactive.html', {'message': 'This campaign is no longer active.'})

    # Verify session ownership
    assigned = request.session.get('assigned_task_id')
    if not assigned or str(unique_id) != str(assigned):
        return render(request, 'campaigns/public_inactive.html', {'message': 'Unauthorized access.'})

    return redirect('submit_proof', unique_id=task.unique_id)


def submit_proof(request, unique_id):
    task = get_object_or_404(Task, unique_id=unique_id)

    if task.status in ('completed', 'pending_review'):
        return render(request, 'campaigns/public_inactive.html', {
            'message': 'Proof already submitted for this task.'
        })

    error = None
    campaign_proof_type = task.campaign.proof_type

    if request.method == 'POST':
        image_file = request.FILES.get('image')
        text_proof = request.POST.get('text', '').strip()
        got_image = bool(image_file)
        got_text = bool(text_proof)

        # Validate based on campaign proof_type
        if campaign_proof_type in ('image', 'both') and not got_image:
            error = 'Please upload a screenshot as proof.'
        elif campaign_proof_type in ('text', 'both') and not got_text:
            error = 'Please enter your proof text.'
        else:
            # Save proof
            ProofSubmission.objects.create(
                task=task,
                image=image_file,
                text=text_proof or '',
            )

            # Generate 9-digit code
            code = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            while Task.objects.filter(proof_code=code).exists():
                code = ''.join([str(random.randint(0, 9)) for _ in range(9)])

            task.proof_code = code
            task.status = 'pending_review'
            task.save()

            # Clear session
            for key in ['assigned_task_id', 'visitor_id']:
                if key in request.session:
                    del request.session[key]

            return redirect('thank_you', code=code)

    context = {
        'task': task,
        'proof_type': campaign_proof_type,
        'error': error,
    }
    return render(request, 'campaigns/submit_proof.html', context)


def thank_you(request, code):
    task = get_object_or_404(Task, proof_code=code)
    context = {
        'task': task,
        'code': code,
    }
    return render(request, 'campaigns/thank_you.html', context)
