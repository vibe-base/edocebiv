from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Project(models.Model):
    """Model representing a user's project."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
