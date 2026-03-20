from django import forms
from .models import Job


class JobForm(forms.ModelForm):
    """Form for creating/editing a job post."""
    SKILL_CHOICES = [
        ('Masonry', 'Masonry'),
        ('Carpentry', 'Carpentry'),
        ('Helper', 'Helper'),
        ('Painting', 'Painting'),
        ('Driver', 'Driver'),
    ]
    required_skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Job
        fields = ['title', 'city', 'daily_rate', 'required_skills', 'start_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
