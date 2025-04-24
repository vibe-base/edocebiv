from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """Model representing a user's profile with additional information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    openai_api_key = models.CharField(max_length=255, blank=True, null=True, help_text="Your OpenAI API key")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"

    def has_api_key(self):
        """Check if the user has set an API key."""
        return bool(self.openai_api_key)

# Create UserProfile automatically when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Project(models.Model):
    """Model representing a user's project with Docker container integration."""
    # Project information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')

    # Container information
    container_id = models.CharField(max_length=64, blank=True, null=True,
                                   help_text="Docker container ID")
    container_status = models.CharField(max_length=20, blank=True, null=True,
                                       help_text="Current status of the container")
    container_created_at = models.DateTimeField(blank=True, null=True,
                                              help_text="When the container was created")
    container_image = models.CharField(max_length=100, default="python:latest",
                                     help_text="Docker image used for the container")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_data_directory(self):
        """Return the path to the project's data directory."""
        import os
        from django.conf import settings

        # Create the base data directory if it doesn't exist
        base_dir = os.path.join(settings.BASE_DIR, 'data')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # Create the project-specific directory
        project_dir = os.path.join(base_dir, f'project_{self.id}')
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir

    def is_container_running(self):
        """Check if the container is currently running."""
        return self.container_status == 'running'

    def has_container(self):
        """Check if a container has been created for this project."""
        return bool(self.container_id)
