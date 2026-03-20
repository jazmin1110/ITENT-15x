from django import forms
from .models import Job, Rating


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


class RatingForm(forms.ModelForm):
    """Form for rating a user."""
    SCORE_CHOICES = [(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)]

    score = forms.ChoiceField(
        choices=SCORE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Rating"
    )

    class Meta:
        model = Rating
        fields = ['score', 'review']
        widgets = {
            'review': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Share your experience (optional)...'
            }),
        }

    def clean_score(self):
        return int(self.cleaned_data['score'])
