from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

class NoNewUsersAccountAdapter(DefaultAccountAdapter):
    """
    Adapter to disable direct email signup and login.
    Redirects all attempts to the social login page.
    """

    def is_open_for_signup(self, request):
        """
        Disable standard signup - only allow social signup
        """
        return False

    def login(self, request, user):
        """
        Only allow social login
        """
        # Check if this is a social login
        sociallogin = getattr(user, 'socialaccount_set', None)
        if sociallogin and sociallogin.exists():
            # This is a social login, proceed normally
            logger.info(f"Social login successful for user: {user.email}")
            return super().login(request, user)
        else:
            # This is a direct login attempt, redirect to social login
            logger.warning(f"Direct login attempt blocked for user: {user.email}")
            messages.error(request, "Direct login is disabled. Please use Google to sign in.")
            return HttpResponseRedirect(reverse('account_login'))

    def authenticate(self, request, **credentials):
        """
        Prevent direct authentication
        """
        # Always return None to prevent direct authentication
        return None

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter to ensure Google sign-ups work properly.
    """

    def is_open_for_signup(self, request, sociallogin):
        """
        Always allow social signup
        """
        logger.info(f"Social signup attempt from provider: {sociallogin.account.provider}")
        return True

    def pre_social_login(self, request, sociallogin):
        """
        Log social login attempts for debugging
        """
        provider = sociallogin.account.provider
        uid = sociallogin.account.uid
        logger.info(f"Pre-social login: Provider={provider}, UID={uid}")
        return super().pre_social_login(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        """
        Save the user and log the action
        """
        user = super().save_user(request, sociallogin, form)
        logger.info(f"Social user saved: {user.email} from provider {sociallogin.account.provider}")
        return user
