from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model with role support."""
    ROLE_CHOICES = [
        ('worker', 'Worker'),
        ('employer', 'Employer'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')

    def __str__(self):
        return f"{self.username} ({self.role})"


class WorkerProfile(models.Model):
    """Extended profile for workers."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    full_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    years_experience = models.IntegerField(default=0)
    skills = models.JSONField(default=list)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Worker Profile"
        verbose_name_plural = "Worker Profiles"


class EmployerProfile(models.Model):
    """Extended profile for employers."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    verified = models.BooleanField(default=False)
    doc_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.company_name

    class Meta:
        verbose_name = "Employer Profile"
        verbose_name_plural = "Employer Profiles"
