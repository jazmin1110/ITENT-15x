import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import User, WorkerProfile, EmployerProfile

PH_PHONE_RE = re.compile(r'^(09\d{9}|\+639\d{9})$')

AVATAR_MAX_BYTES = 2 * 1024 * 1024


def clean_profile_email(email: str, user: User | None) -> str:
    """Validate optional profile email; enforce uniqueness excluding current user."""
    email = (email or '').strip()
    if not email:
        return ''
    try:
        validate_email(email)
    except DjangoValidationError:
        raise forms.ValidationError('Invalid na email address. Suriin at subukan ulit.')
    qs = User.objects.filter(email=email)
    if user and user.pk:
        qs = qs.exclude(pk=user.pk)
    if qs.exists():
        raise forms.ValidationError('Ginagamit na ang email na ito.')
    return email


class SignUpForm(UserCreationForm):
    """Registration form with role selection."""
    role = forms.ChoiceField(choices=User.ROLE_CHOICES[:2])
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 09171234567',
            'type': 'tel',
        }),
    )

    class Meta:
        model = User
        fields = ['phone_number', 'email', 'password1', 'password2', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['email'].widget.input_type = 'email'
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
            raise forms.ValidationError('Kailangan ng phone number.')
        if not PH_PHONE_RE.match(phone):
            raise forms.ValidationError(
                'Invalid na phone number. Gamitin ang 09XXXXXXXXX o +639XXXXXXXXX format.'
            )
        if phone.startswith('+63'):
            phone = '0' + phone[3:]
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError('Ginagamit na ang phone number na ito.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['phone_number']
        if commit:
            user.save()
        return user


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
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'optional@email.com',
            'autocomplete': 'email',
        }),
        label='Email',
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/gif,image/webp',
        }),
        label='Profile picture',
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
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
            'years_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'doc_nbi_clearance': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. XXXX-XXXX-XXXX-XXXX'}),
        }
        labels = {
            'doc_nbi_clearance': 'NBI Clearance',
            'national_id_number': 'Philippine National ID (PhilSys) Number',
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user:
            self.fields['email'].initial = user.email or ''
            if self._should_prefill_contact():
                self.fields['contact_number'].initial = user.phone_number

    def _should_prefill_contact(self):
        if not self.instance or not self.instance.pk:
            return True
        return not (self.instance.contact_number or '').strip()

    def clean_email(self):
        return clean_profile_email(self.cleaned_data.get('email', ''), self.user)

    def clean_avatar(self):
        f = self.cleaned_data.get('avatar')
        if not f:
            return f
        if f.size > AVATAR_MAX_BYTES:
            raise forms.ValidationError('Masyadong malaki ang larawan (max 2MB).')
        return f


class EmployerProfileForm(forms.ModelForm):
    """Form for employer profile details."""
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'optional@email.com',
            'autocomplete': 'email',
        }),
        label='Email',
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/gif,image/webp',
        }),
        label='Profile picture',
    )

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
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
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

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['contact_number'].label = 'Company contact number'
        if user:
            self.fields['email'].initial = user.email or ''

    def clean_email(self):
        return clean_profile_email(self.cleaned_data.get('email', ''), self.user)

    def clean_avatar(self):
        f = self.cleaned_data.get('avatar')
        if not f:
            return f
        if f.size > AVATAR_MAX_BYTES:
            raise forms.ValidationError('Masyadong malaki ang larawan (max 2MB).')
        return f
