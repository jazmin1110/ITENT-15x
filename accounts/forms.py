from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, WorkerProfile, EmployerProfile


class SignUpForm(UserCreationForm):
    """Registration form with role selection."""
    role = forms.ChoiceField(choices=User.ROLE_CHOICES[:2])  # worker or employer only

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


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
        fields = ['full_name', 'city', 'contact_number', 'years_experience', 'skills']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'years_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class EmployerProfileForm(forms.ModelForm):
    """Form for employer profile details."""
    class Meta:
        model = EmployerProfile
        fields = ['company_name', 'city', 'contact_person', 'contact_number', 'doc_url']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'doc_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Link to business document'}),
        }
