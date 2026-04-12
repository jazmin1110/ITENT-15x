from datetime import date

from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import AbstractUser

from itent.choices import GENDER_CHOICES, MARITAL_STATUS_CHOICES


class User(AbstractUser):
    """Custom user model with role support."""
    ROLE_CHOICES = [
        ('worker', 'Worker'),
        ('employer', 'Employer'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')
    phone_number = models.CharField(max_length=20, unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    def get_average_rating(self):
        avg = self.ratings_received.aggregate(avg=Avg('score'))['avg']
        return round(avg, 1) if avg else None

    def get_rating_count(self):
        return self.ratings_received.count()

    @property
    def display_name(self) -> str:
        """Navbar / UI label: profile name when available, else full name, else phone."""
        if self.role == 'worker':
            try:
                n = (self.worker_profile.full_name or '').strip()
                if n:
                    return n
            except WorkerProfile.DoesNotExist:
                pass
        elif self.role == 'employer':
            try:
                n = (self.employer_profile.company_name or '').strip()
                if n:
                    return n
            except EmployerProfile.DoesNotExist:
                pass
        full = (self.get_full_name() or '').strip()
        if full:
            return full
        if self.phone_number:
            return self.phone_number
        return (self.username or '')

    def __str__(self):
        return f"{self.phone_number} ({self.role})"


class WorkerProfile(models.Model):
    """Extended profile for workers."""
    VERIFICATION_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    NATIONAL_ID_CHOICES = [
        ('not_verified', 'Not Verified'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    full_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=120)
    years_experience = models.IntegerField(default=0)
    skills = models.JSONField(default=list)

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    marital_status = models.CharField(
        max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, default='',
    )
    nationality = models.CharField(max_length=100, blank=True, default='')
    religion = models.CharField(max_length=100, blank=True, default='')
    languages_known = models.TextField(blank=True, default='')

    doc_nbi_clearance = models.FileField(upload_to='worker_docs/', blank=True)
    national_id_number = models.CharField(max_length=30, blank=True, default='')
    national_id_status = models.CharField(
        max_length=20, choices=NATIONAL_ID_CHOICES, default='not_verified'
    )

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default='not_submitted'
    )
    rejection_reason = models.TextField(blank=True, default='')

    @property
    def verified(self):
        return self.verification_status == 'verified'

    @property
    def age(self):
        """Whole years since date_of_birth; None if DOB not set."""
        if not self.date_of_birth:
            return None
        today = date.today()
        born = self.date_of_birth
        years = today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )
        return max(0, years)

    @property
    def all_requirements_met(self):
        return bool(self.doc_nbi_clearance) and self.national_id_status == 'verified'

    def __str__(self):
        return self.full_name

    @property
    def skill_entries_normalized(self):
        from jobs.skill_utils import normalize_skill_entries

        return normalize_skill_entries(self.skills)

    class Meta:
        verbose_name = "Worker Profile"
        verbose_name_plural = "Worker Profiles"


class WorkerPortfolioItem(models.Model):
    """Photos and optional document proof of past work (served via permission-checked views)."""

    worker_profile = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='portfolio_items',
    )
    title = models.CharField(max_length=255, blank=True, default='')
    caption = models.TextField(blank=True, default='')
    related_skill = models.CharField(max_length=255, blank=True, default='')
    photo = models.ImageField(upload_to='worker_portfolio/')
    proof_file = models.FileField(upload_to='worker_portfolio/', blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = "Worker portfolio item"
        verbose_name_plural = "Worker portfolio items"

    def __str__(self):
        return self.title or f"Portfolio #{self.pk}"


class EmployerProfile(models.Model):
    """Extended profile for employers."""
    VERIFICATION_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=120)

    doc_sec_dti = models.FileField(upload_to='employer_docs/', blank=True)
    doc_barangay_clearance = models.FileField(upload_to='employer_docs/', blank=True)
    doc_mayors_permit = models.FileField(upload_to='employer_docs/', blank=True)
    doc_bir = models.FileField(upload_to='employer_docs/', blank=True)
    doc_employer_registrations = models.FileField(upload_to='employer_docs/', blank=True)

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default='not_submitted'
    )
    rejection_reason = models.TextField(blank=True, default='')

    @property
    def verified(self):
        return self.verification_status == 'verified'

    @property
    def all_docs_uploaded(self):
        return all([
            self.doc_sec_dti,
            self.doc_barangay_clearance,
            self.doc_mayors_permit,
            self.doc_bir,
            self.doc_employer_registrations,
        ])

    def __str__(self):
        return self.company_name

    class Meta:
        verbose_name = "Employer Profile"
        verbose_name_plural = "Employer Profiles"
