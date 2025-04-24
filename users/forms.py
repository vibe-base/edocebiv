from django import forms
from .models import Project, UserProfile

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information."""

    class Meta:
        model = UserProfile
        fields = ['openai_api_key']
        widgets = {
            'openai_api_key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your OpenAI API key',
                'autocomplete': 'off'
            }),
        }
        help_texts = {
            'openai_api_key': 'Your OpenAI API key will be stored securely and used for AI-powered features.'
        }

class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects."""

    class Meta:
        model = Project
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
