from django import forms
from .models import Job, Rating
from .skill_utils import PREDEFINED_SKILL_CHOICES


class JobForm(forms.ModelForm):
    """Form for creating/editing a job post."""
    SKILL_CHOICES = PREDEFINED_SKILL_CHOICES
    required_skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    working_hours = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Halimbawa: 7am–4pm o 8 oras',
        }),
    )
    short_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Maikling paglalarawan (opsyonal)',
        }),
    )
    positions_needed = forms.IntegerField(
        min_value=1,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        label='Bilang ng mga kailangan',
    )

    class Meta:
        model = Job
        fields = [
            'title',
            'city',
            'daily_rate',
            'rate_type',
            'working_hours',
            'short_description',
            'positions_needed',
            'start_date',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'rate_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'title': 'Job Title',
            'city': 'Lungsod / Bayan',
            'daily_rate': 'Halaga (₱)',
            'rate_type': 'Araw-araw o buwan-buwan',
            'start_date': 'Start Date',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for code, label in self.SKILL_CHOICES:
            self.fields[f'years_{code}'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=80,
                label=f'{label} — taon ng karanasan (opsyonal)',
                widget=forms.NumberInput(attrs={
                    'class': 'form-control form-control-sm',
                    'min': 0,
                    'placeholder': '—',
                }),
            )

    @property
    def skill_rows(self):
        return [
            (code, label, self[f'years_{code}'])
            for code, label in self.SKILL_CHOICES
        ]

    def clean_working_hours(self):
        w = (self.cleaned_data.get('working_hours') or '').strip()
        if not w:
            raise forms.ValidationError('Kailangan ang working hours.')
        return w

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected = self.cleaned_data['required_skills']
        instance.required_skills = []
        for skill in selected:
            raw_y = self.cleaned_data.get(f'years_{skill}')
            years = int(raw_y) if raw_y is not None and raw_y != '' else None
            instance.required_skills.append({
                'skill': skill,
                'years_experience': years,
            })
        if commit:
            instance.save()
        return instance


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
