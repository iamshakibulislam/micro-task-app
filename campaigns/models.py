import uuid
import random
from django.db import models
from django.utils import timezone


def generate_proof_code():
    return ''.join([str(random.randint(0, 9)) for _ in range(9)])


class ContactUpload(models.Model):
    """A batch of contacts imported from a single CSV file."""
    name = models.CharField(max_length=255, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.filename or f"Upload #{self.id}"


class Campaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('disabled', 'Disabled'),
    ]
    PROOF_CHOICES = [
        ('image', 'Image Screenshot'),
        ('text', 'Text Proof'),
        ('both', 'Image + Text'),
    ]

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    custom_instruction = models.TextField(
        blank=True,
        help_text="Instructions shown to visitors on the task page"
    )
    message_template = models.TextField(
        blank=True,
        help_text="Use variables like {first_name}, {last_name}, {full_name}, {email}, {domain}, {company}, {phone}, {profile}"
    )
    proof_type = models.CharField(max_length=20, choices=PROOF_CHOICES, default='image')
    contact_upload = models.ForeignKey(
        ContactUpload, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='campaigns',
        help_text="Select the uploaded contacts to use for this campaign"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Contact(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    contact_upload = models.ForeignKey(
        ContactUpload, on_delete=models.CASCADE, related_name='contacts'
    )
    first_name = models.CharField(max_length=255, blank=True, default='')
    last_name = models.CharField(max_length=255, blank=True, default='')
    full_name = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    domain = models.CharField(max_length=255, blank=True, default='')
    profile_url = models.URLField(max_length=500)
    company = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name or self.profile_url


class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('visited', 'Visited'),
        ('pending_review', 'Pending Review'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='tasks')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='tasks')
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    locked_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    proof_code = models.CharField(max_length=9, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Task {self.unique_id} - {self.contact}"

    def is_locked(self):
        if not self.locked_at:
            return False
        return timezone.now() < self.locked_at + timezone.timedelta(minutes=10)

    def release_if_expired(self):
        if self.locked_at and timezone.now() >= self.locked_at + timezone.timedelta(minutes=10):
            self.ip_address = None
            self.locked_at = None
            self.status = 'pending'
            self.contact.status = 'pending'
            self.contact.save(update_fields=['status'])
            self.save(update_fields=['ip_address', 'locked_at', 'status'])
            return True
        return False


class ProofSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='proofs')
    image = models.ImageField(upload_to='proofs/', blank=True, null=True)
    text = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Proof for {self.task}"
