from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

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
            return super().login(request, user)
        else:
            # This is a direct login attempt, redirect to social login
            messages.error(request, "Direct login is disabled. Please use Google to sign in.")
            return HttpResponseRedirect(reverse('account_login'))
    
    def authenticate(self, request, **credentials):
        """
        Prevent direct authentication
        """
        # Always return None to prevent direct authentication
        return None
