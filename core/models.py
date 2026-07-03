from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

class CryptoLog(models.Model):
    OPERATION_CHOICES = (
        ('ENCRYPT', 'Encrypt'),
        ('DECRYPT', 'Decrypt'),
    )
    STATUS_CHOICES = (
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crypto_logs')
    operation_type = models.CharField(max_length=10, choices=OPERATION_CHOICES)
    text_fragment = models.CharField(max_length=50)
    full_cipher = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SUCCESS')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.operation_type} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

import uuid
from django.utils import timezone

class DecryptionVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decryption_verifications')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cipher_text = models.TextField()
    decryption_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=15)

    def __str__(self):
        return f"Verification for {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile_number = models.CharField(max_length=20)

    def __str__(self):
        return f"Profile for {self.user.username}"

class UserDeviceSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_sessions')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} at {self.ip_address}"

@receiver(user_logged_in)
def log_user_device(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    UserDeviceSession.objects.create(user=user, ip_address=ip, user_agent=user_agent[:250])
