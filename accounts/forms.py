import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import User, WorkerProfile, EmployerProfile

PH_PHONE_RE = re.compile(r'^(09\d{9}|\+639\d{9})$')


class SignUpForm(UserCreationForm):
    """Registration form with role selection."""
    role = forms.ChoiceField(choices=User.ROLE_CHOICES[:2])
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 09171234567',
            'type': 'tel',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password1', 'password2', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['email'].widget.input_type = 'email'
        self.fields['phone_number'].required = False
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            return email
        try:
            validate_email(email)
        except DjangoValidationError:
            raise forms.ValidationError('Invalid na email address. Suriin at subukan ulit.')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ginagamit na ang email na ito.')
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            return phone
        if not PH_PHONE_RE.match(phone):
            raise forms.ValidationError(
                'Invalid na phone number. Gamitin ang 09XXXXXXXXX o +639XXXXXXXXX format.'
            )
        # Normalize +639 → 09 for consistent lookups
        if phone.startswith('+63'):
            phone = '0' + phone[3:]
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError('Ginagamit na ang phone number na ito.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone_number')
        if not email and not phone:
            raise forms.ValidationError(
                'Kailangan ng email o phone number. Maglagay ng kahit isa.'
            )
        return cleaned_data


class WorkerProfileForm(forms.ModelForm):
    """Form for worker profile details."""
    SKILL_CHOICES = [
        ('Masonry', 'Masonry'),
        ('Carpentry', 'Carpentry'),
        ('Helper', 'Helper'),
        ('Painting', 'Painting'),
        ('Driver', 'Driver'),
    ]
    skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = WorkerProfile
        fields = [
            'full_name', 'city', 'contact_number', 'years_experience', 'skills',
            'doc_nbi_clearance', 'national_id_number',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'years_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'doc_nbi_clearance': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. XXXX-XXXX-XXXX-XXXX'}),
        }
        labels = {
            'doc_nbi_clearance': 'NBI Clearance',
            'national_id_number': 'Philippine National ID (PhilSys) Number',
        }


class EmployerProfileForm(forms.ModelForm):
    """Form for employer profile details."""
    class Meta:
        model = EmployerProfile
        fields = [
            'company_name', 'city', 'contact_person', 'contact_number',
            'doc_sec_dti', 'doc_barangay_clearance', 'doc_mayors_permit',
            'doc_bir', 'doc_employer_registrations',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'doc_sec_dti': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_barangay_clearance': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_mayors_permit': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_bir': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'doc_employer_registrations': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }
        labels = {
            'doc_sec_dti': 'SEC (Corporation) o DTI (Sole Proprietor) Registration',
            'doc_barangay_clearance': 'Barangay Clearance',
            'doc_mayors_permit': "Mayor's Business Permit",
            'doc_bir': 'BIR Registration',
            'doc_employer_registrations': 'Employer Registrations (SSS, PhilHealth, Pag-IBIG)',
        }
