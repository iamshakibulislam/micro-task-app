from django.contrib import admin
from .models import Campaign, ContactUpload, Contact, Task, ProofSubmission


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    readonly_fields = ['created_at']
    can_delete = False


@admin.register(ContactUpload)
class ContactUploadAdmin(admin.ModelAdmin):
    list_display = ['name', 'filename', 'created_at', 'contact_count']
    inlines = [ContactInline]

    def contact_count(self, obj):
        return obj.contacts.count()
    contact_count.short_description = 'Contacts'


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'contact_upload', 'proof_type', 'created_at']
    list_filter = ['status']
    search_fields = ['name']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'contact_upload', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['full_name', 'email', 'profile_url']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['unique_id', 'contact', 'campaign', 'status', 'ip_address', 'locked_at']
    list_filter = ['status', 'campaign']
    search_fields = ['proof_code', 'contact__full_name', 'contact__email']


@admin.register(ProofSubmission)
class ProofSubmissionAdmin(admin.ModelAdmin):
    list_display = ['task', 'status', 'submitted_at']
    list_filter = ['status']
