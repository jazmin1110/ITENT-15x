from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Job(models.Model):
    """Job posting by an employer."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_jobs'
    )
    title = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    required_skills = models.JSONField(default=list)
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.city}"

    class Meta:
        ordering = ['-created_at']


class Application(models.Model):
    """Worker application for a job."""
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('shortlisted', 'Shortlisted'),
        ('hired', 'Hired'),
        ('completed', 'Completed'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    hired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.worker.phone_number} -> {self.job.title}"

    class Meta:
        ordering = ['-created_at']


class Rating(models.Model):
    """Rating given after job completion."""
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_given'
    )
    ratee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_received'
    )
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['application', 'rater']

    def __str__(self):
        return f"{self.rater.phone_number} rated {self.ratee.phone_number}: {self.score}/5"
