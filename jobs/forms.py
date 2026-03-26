from django import forms
from .models import Job, Rating
from .skill_utils import (
    PREDEFINED_SKILL_CHOICES,
    PREDEFINED_SKILL_CODES,
    canonical_predefined_skill,
    normalize_skill_entries,
)

JOB_MAX_CUSTOM_SKILLS = 10
JOB_CUSTOM_SKILL_NAME_MAX_LEN = 80


def _multi_get(data, key: str) -> list:
    """Like QueryDict.getlist — supports dict POST data in tests."""
    if hasattr(data, 'getlist'):
        return data.getlist(key)
    v = data.get(key)
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]


class JobForm(forms.ModelForm):
    """Form for creating/editing a job post (predefined + custom skills)."""
    SKILL_CHOICES = PREDEFINED_SKILL_CHOICES
    required_skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
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

        if self.is_bound:
            self.custom_skills_initial = self._custom_rows_from_data(self.data)
        else:
            self.custom_skills_initial = self._custom_rows_from_instance()

    def _custom_rows_from_data(self, data) -> list[dict]:
        names = _multi_get(data, 'custom_skill_name')
        years = _multi_get(data, 'custom_skill_years')
        n = max(len(names), len(years))
        rows = []
        for i in range(n):
            name = (names[i] if i < len(names) else '') or ''
            yraw = years[i] if i < len(years) else ''
            name = name.strip()
            ystr = (str(yraw).strip() if yraw is not None else '')
            if name or ystr:
                rows.append({'name': name, 'years': yraw if yraw is not None else ''})
        return rows

    def _custom_rows_from_instance(self) -> list[dict]:
        if not self.instance or not self.instance.pk or not self.instance.required_skills:
            return []
        rows = []
        for entry in normalize_skill_entries(self.instance.required_skills):
            name = entry['skill']
            if canonical_predefined_skill(name) is not None:
                continue
            y = entry['years_experience']
            rows.append({
                'name': name,
                'years': '' if y is None else y,
            })
        return rows

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

    def _coerce_custom_skill_years(self, raw) -> int | None:
        if raw is None or raw == '':
            return None
        try:
            y = int(raw)
        except (TypeError, ValueError):
            raise forms.ValidationError('Ilagay ang tamang bilang ng taon sa custom skill.')
        if y < 0 or y > 80:
            raise forms.ValidationError('Dapat 0–80 na taon ang karanasan sa bawat skill.')
        return y

    def clean(self):
        cleaned = super().clean()

        post_skill_vals = [
            str(s).strip()
            for s in _multi_get(self.data, 'required_skills')
            if str(s).strip()
        ]
        selected = []
        seen_sel: set[str] = set()
        for s in post_skill_vals:
            if s not in PREDEFINED_SKILL_CODES:
                self.add_error('required_skills', 'Pumili ng wastong skill sa listahan.')
                return cleaned
            key = s.lower()
            if key in seen_sel:
                continue
            seen_sel.add(key)
            selected.append(s)
        cleaned['required_skills'] = selected
        predefined_lower = {c.lower() for c in PREDEFINED_SKILL_CODES}

        names = _multi_get(self.data, 'custom_skill_name')
        years = _multi_get(self.data, 'custom_skill_years')
        custom_out: list[tuple[str, int | None]] = []
        seen_custom: set[str] = set()

        for i, raw_name in enumerate(names):
            name = (raw_name or '').strip()
            y_raw = years[i] if i < len(years) else ''
            if not name:
                if y_raw not in (None, ''):
                    self.add_error(
                        'required_skills',
                        'May taon ng karanasan na nakalagay nang walang pangalan ng skill sa isa sa mga karagdagang row.',
                    )
                    return cleaned
                continue

            if len(name) > JOB_CUSTOM_SKILL_NAME_MAX_LEN:
                self.add_error(
                    'required_skills',
                    f'Masyado ang haba ng pangalan ng skill (max {JOB_CUSTOM_SKILL_NAME_MAX_LEN} na karakter).',
                )
                return cleaned
            key = name.lower()
            if key in predefined_lower:
                self.add_error(
                    'required_skills',
                    f'Ang "{name}" ay nasa listahan na — piliin ang checkbox sa itaas imbes na ilagay bilang custom skill.',
                )
                return cleaned
            if key in seen_custom:
                self.add_error('required_skills', f'May duplicate na custom skill: "{name}".')
                return cleaned
            seen_custom.add(key)

            try:
                y_val = self._coerce_custom_skill_years(y_raw)
            except forms.ValidationError as exc:
                self.add_error(
                    'required_skills',
                    exc.messages[0] if getattr(exc, 'messages', None) else str(exc),
                )
                return cleaned
            custom_out.append((name, y_val))

        if len(custom_out) > JOB_MAX_CUSTOM_SKILLS:
            self.add_error(
                'required_skills',
                f'Masyadong maraming custom skill (max {JOB_MAX_CUSTOM_SKILLS}).',
            )
            return cleaned

        if not selected and not custom_out:
            self.add_error(
                'required_skills',
                'Pumili ng kahit isang skill sa listahan o magdagdag ng custom skill.',
            )
            return cleaned

        payload: list[dict] = []
        for code in selected:
            y = cleaned.get(f'years_{code}')
            payload.append({'skill': code, 'years_experience': y})

        for name, y in custom_out:
            payload.append({'skill': name, 'years_experience': y})

        self._skills_payload = payload
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.required_skills = self._skills_payload
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
