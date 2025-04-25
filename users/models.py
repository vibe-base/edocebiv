from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """Model representing a user's profile with additional information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    openai_api_key = models.CharField(max_length=255, blank=True, null=True, help_text="Your OpenAI API key")
    is_assistant_window_open = models.BooleanField(default=True, help_text="Whether the assistant window is open")
    is_reasoning_mode_on = models.BooleanField(default=False, help_text="Whether reasoning mode is enabled")
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

    # Web server preview information
    web_server_port = models.IntegerField(blank=True, null=True,
                                        help_text="Port for web server preview")
    web_server_internal_port = models.IntegerField(default=8000,
                                                help_text="Internal container port for web server")
    web_server_path = models.CharField(max_length=100, default="/",
                                     help_text="Path to append to URL for web server preview")

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


class ChatMessage(models.Model):
    """Model representing a message in a chat conversation."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role} message in {self.project.title} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class ReasoningSession(models.Model):
    """Model representing an AI reasoning session with multiple steps."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reasoning_sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reasoning session: {self.title} for {self.project.title}"


class ReasoningStep(models.Model):
    """Model representing a step in an AI reasoning session."""
    session = models.ForeignKey(ReasoningSession, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField()
    step_type = models.CharField(max_length=50, choices=[
        ('planning', 'Planning'),
        ('analysis', 'Analysis'),
        ('code_generation', 'Code Generation'),
        ('code_execution', 'Code Execution'),
        ('testing', 'Testing'),
        ('refinement', 'Refinement'),
        ('conclusion', 'Conclusion')
    ])
    prompt = models.TextField()
    response = models.TextField(blank=True)
    model_used = models.CharField(max_length=50, default='gpt-4o')
    tool_calls = models.JSONField(null=True, blank=True)
    tool_results = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=False)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['session', 'step_number']
        unique_together = ['session', 'step_number']

    def __str__(self):
        return f"Step {self.step_number}: {self.step_type} in {self.session.title}"
