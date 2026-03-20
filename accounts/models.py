from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model with role support."""
    ROLE_CHOICES = [
        ('worker', 'Worker'),
        ('employer', 'Employer'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')
    phone_number = models.CharField(max_length=20, blank=True, default='')

    def get_average_rating(self):
        avg = self.ratings_received.aggregate(avg=Avg('score'))['avg']
        return round(avg, 1) if avg else None

    def get_rating_count(self):
        return self.ratings_received.count()

    def __str__(self):
        return f"{self.username} ({self.role})"


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
    contact_number = models.CharField(max_length=20)
    years_experience = models.IntegerField(default=0)
    skills = models.JSONField(default=list)

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
    def all_requirements_met(self):
        return bool(self.doc_nbi_clearance) and self.national_id_status == 'verified'

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Worker Profile"
        verbose_name_plural = "Worker Profiles"


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
    contact_number = models.CharField(max_length=20)

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
