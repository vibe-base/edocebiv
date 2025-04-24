from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile

class Command(BaseCommand):
    help = 'Creates UserProfile objects for users that do not have one'

    def handle(self, *args, **options):
        users_without_profile = []
        for user in User.objects.all():
            try:
                # If the user has a profile, this will not raise an exception
                user.profile
            except UserProfile.DoesNotExist:
                users_without_profile.append(user)
                UserProfile.objects.create(user=user)
        
        if users_without_profile:
            self.stdout.write(self.style.SUCCESS(f'Created {len(users_without_profile)} user profiles'))
            for user in users_without_profile:
                self.stdout.write(f'  - Created profile for {user.email or user.username}')
        else:
            self.stdout.write(self.style.SUCCESS('All users already have profiles'))
