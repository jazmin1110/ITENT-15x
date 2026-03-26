from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Job(models.Model):
    """Job posting by an employer."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]
    RATE_TYPE_DAILY = 'daily'
    RATE_TYPE_MONTHLY = 'monthly'
    RATE_TYPE_CHOICES = [
        (RATE_TYPE_DAILY, 'Daily'),
        (RATE_TYPE_MONTHLY, 'Monthly'),
    ]

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_jobs'
    )
    title = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    rate_type = models.CharField(
        max_length=20,
        choices=RATE_TYPE_CHOICES,
        default=RATE_TYPE_DAILY,
    )
    working_hours = models.CharField(max_length=255, blank=True, default='')
    short_description = models.TextField(blank=True)
    required_skills = models.JSONField(default=list)
    start_date = models.DateField()
    positions_needed = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    auto_closed_when_filled = models.BooleanField(default=False)
    employer_acknowledged_vacancy_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.city}"

    @property
    def skill_entries_normalized(self):
        from .skill_utils import normalize_skill_entries
        return normalize_skill_entries(self.required_skills)

    @property
    def rate_suffix_tagalog(self) -> str:
        """Short suffix for listings (e.g. /araw vs /buwan)."""
        if self.rate_type == self.RATE_TYPE_MONTHLY:
            return '/buwan'
        return '/araw'

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

    @property
    def hire_allowed_by_contract(self) -> bool:
        """True if employer may set status to hired (contract workflow complete)."""
        try:
            return self.contract.is_complete
        except ApplicationContract.DoesNotExist:
            return False

    @property
    def contract_or_none(self):
        try:
            return self.contract
        except ApplicationContract.DoesNotExist:
            return None


class ApplicationContract(models.Model):
    """Contract PDF + acceptance workflow before hire."""

    STATUS_NONE = 'none'
    STATUS_EMPLOYER_UPLOADED = 'employer_uploaded'
    STATUS_WORKER_RESPONDED = 'worker_responded'
    STATUS_COMPLETE = 'complete'

    CONTRACT_STATUS_CHOICES = [
        (STATUS_NONE, 'None'),
        (STATUS_EMPLOYER_UPLOADED, 'Employer uploaded'),
        (STATUS_WORKER_RESPONDED, 'Worker responded'),
        (STATUS_COMPLETE, 'Complete'),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='contract',
    )
    contract_status = models.CharField(
        max_length=30,
        choices=CONTRACT_STATUS_CHOICES,
        default=STATUS_NONE,
    )
    employer_contract_file = models.FileField(
        upload_to='application_contracts/employer/',
        blank=True,
        null=True,
    )
    worker_signed_file = models.FileField(
        upload_to='application_contracts/worker/',
        blank=True,
        null=True,
    )
    worker_accepted_terms = models.BooleanField(default=False)
    worker_accepted_at = models.DateTimeField(null=True, blank=True)
    employer_confirmed_at = models.DateTimeField(null=True, blank=True)
    contract_sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Contract for application {self.application_id} ({self.contract_status})'

    @property
    def is_complete(self) -> bool:
        return self.contract_status == self.STATUS_COMPLETE

    @property
    def can_employer_upload(self) -> bool:
        app = self.application
        if app.status in ('hired', 'completed'):
            return False
        return app.status == 'shortlisted' and self.contract_status in (
            self.STATUS_NONE,
            self.STATUS_EMPLOYER_UPLOADED,
        )

    @property
    def can_worker_respond(self) -> bool:
        return self.contract_status == self.STATUS_EMPLOYER_UPLOADED

    @property
    def can_employer_confirm(self) -> bool:
        return self.contract_status == self.STATUS_WORKER_RESPONDED


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
