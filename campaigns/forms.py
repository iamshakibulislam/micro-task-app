from django import forms
from .models import Campaign, ContactUpload

VARIABLE_CHOICES = [
    ('first_name', 'First Name'),
    ('last_name', 'Last Name'),
    ('full_name', 'Full Name'),
    ('email', 'Email'),
    ('domain', 'Domain'),
    ('profile', 'Profile URL'),
    ('company', 'Company'),
    ('phone', 'Phone'),
]


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'custom_instruction', 'message_template', 'proof_type', 'contact_upload']
        widgets = {
            'custom_instruction': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'message_template': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'proof_type': forms.Select(attrs={'class': 'form-select'}),
            'contact_upload': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contact_upload'].queryset = ContactUpload.objects.all()
        self.fields['contact_upload'].empty_label = "-- Select Contact Upload --"
        self.fields['contact_upload'].required = False
        self.fields['contact_upload'].label = 'Contacts'


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Upload CSV',
        help_text='Upload a CSV file with your contacts',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )


class CampaignEditForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'custom_instruction', 'message_template', 'proof_type', 'status', 'contact_upload']
        widgets = {
            'custom_instruction': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'message_template': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'proof_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'contact_upload': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contact_upload'].queryset = ContactUpload.objects.all()
        self.fields['contact_upload'].empty_label = "-- Select Contact Upload --"
        self.fields['contact_upload'].required = False
        self.fields['contact_upload'].label = 'Contacts'


class TaskSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by proof code, name, or email...'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + [('pending', 'Pending'), ('visited', 'Visited'),
                                          ('pending_review', 'Pending Review'),
                                          ('completed', 'Completed'), ('rejected', 'Rejected')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ProofForm(forms.Form):
    """Proof form — proof_type is determined by the campaign, not the user."""
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter your proof text...'})
    )

    def __init__(self, *args, campaign_proof_type='image', **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign_proof_type = campaign_proof_type

    def clean(self):
        cleaned_data = super().clean()
        ptype = self.campaign_proof_type
        image = cleaned_data.get('image')
        text = cleaned_data.get('text')

        if ptype in ('image', 'both') and not image:
            raise forms.ValidationError("Please upload a screenshot as proof.")
        if ptype in ('text', 'both') and not text:
            raise forms.ValidationError("Please enter your proof text.")
        return cleaned_data


class ContactUploadNameForm(forms.ModelForm):
    class Meta:
        model = ContactUpload
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Batch 1 - Tech CEOs'})
        }
