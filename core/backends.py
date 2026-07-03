from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from core.models import UserProfile

class ServerlessFallbackBackend(ModelBackend):
    """
    On Vercel, the /tmp SQLite database is ephemeral and can be wiped or run on a different
    container between requests. This causes logged-in users to suddenly lose their session 
    and get redirected to the login page when request.user fails to find their ID in the database.
    
    This backend auto-recreates the user from their session ID if they go missing, 
    so the app remains functional for demonstrations on Vercel.
    """
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            user = User(
                id=user_id, 
                username=f"demo_recovered_{user_id}", 
                email=f"demo_recovered_{user_id}@nexus.com"
            )
            # Create user in the current ephemeral database
            user.save()
            # Restore their profile too to avoid related errors
            UserProfile.objects.get_or_create(user=user, defaults={'mobile_number': '0000000000'})
            return user
