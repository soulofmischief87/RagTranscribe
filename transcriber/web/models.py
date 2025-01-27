from django.db import models
from django.utils import timezone


class TranscriptionJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    audio_file = models.FileField(upload_to='audio/')
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transcript = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    speaker_count = models.IntegerField(default=2)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transcription Job {self.id} - {self.status}"
