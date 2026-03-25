from django.db import models
from django.conf import settings
from jobs.models import Job


class Conversation(models.Model):
    """Chat thread between a worker and employer for a job."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='conversations')
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='worker_conversations'
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employer_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat: {self.worker.phone_number} & {self.employer.phone_number} - {self.job.title}"

    class Meta:
        unique_together = ['job', 'worker', 'employer']
        ordering = ['-created_at']


class Message(models.Model):
    """Individual message in a conversation."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.phone_number}: {self.content[:50]}"

    class Meta:
        ordering = ['created_at']
