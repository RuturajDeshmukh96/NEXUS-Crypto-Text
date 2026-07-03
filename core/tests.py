import uuid
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.contrib.messages import get_messages
from core.models import CryptoLog, DecryptionVerification, UserProfile, UserDeviceSession
from core import cipher
from core.forms import RegistrationForm, EncryptForm, DecryptForm, ProfileUpdateForm

# --- CIPHER TESTS ---
class CipherHelperTestCase(TestCase):
    def test_get_fernet_key(self):
        passphrase = "mySecretSecurePassphrase123!"
        key1 = cipher.get_fernet_key(passphrase)
        key2 = cipher.get_fernet_key(passphrase)
        self.assertEqual(key1, key2)
        # Fernet keys should be 32 bytes base64 encoded (which is 44 characters long)
        self.assertEqual(len(key1), 44)

    def test_generate_random_passphrase(self):
        passphrase = cipher.generate_random_passphrase(16)
        self.assertEqual(len(passphrase), 16)
        self.assertTrue(passphrase.isalnum())

    def test_encrypt_decrypt_cycle(self):
        text = "Hello World! This is a secret message."
        passphrase = "password123"
        encrypted = cipher.encrypt_text(text, passphrase)
        self.assertNotEqual(text, encrypted)
        
        # Test correct password decryption
        decrypted = cipher.decrypt_text(encrypted, passphrase)
        self.assertEqual(text, decrypted)
        
        # Test incorrect password decryption
        bad_decrypted = cipher.decrypt_text(encrypted, "wrongpassword")
        self.assertIsNone(bad_decrypted)


# --- MODEL & SIGNAL TESTS ---
class ModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='Password123!',
            first_name='Test',
            last_name='User'
        )
        self.profile = UserProfile.objects.create(user=self.user, mobile_number='1234567890')

    def test_string_representations(self):
        log = CryptoLog.objects.create(
            user=self.user,
            operation_type='ENCRYPT',
            text_fragment='Text fragment...',
            full_cipher='full_cipher_text',
            status='SUCCESS'
        )
        dec_verification = DecryptionVerification.objects.create(
            user=self.user,
            cipher_text='cipher_text',
            decryption_key='key'
        )
        session = UserDeviceSession.objects.create(
            user=self.user,
            ip_address='127.0.0.1',
            user_agent='Mozilla'
        )
        
        self.assertIn('testuser@example.com', str(log))
        self.assertIn('ENCRYPT', str(log))
        self.assertIn('Verification for testuser@example.com', str(dec_verification))
        self.assertIn('Profile for testuser@example.com', str(self.profile))
        self.assertIn('testuser@example.com at 127.0.0.1', str(session))

    def test_decryption_verification_expiration(self):
        verification = DecryptionVerification.objects.create(
            user=self.user,
            cipher_text='cipher',
            decryption_key='key'
        )
        # Brand new verification should not be expired
        self.assertFalse(verification.is_expired)
        
        # Mocking creation date to 20 minutes ago
        verification.created_at = timezone.now() - timezone.timedelta(minutes=20)
        verification.save()
        self.assertTrue(verification.is_expired)

    def test_user_logged_in_signal(self):
        # Log in through client to trigger the signal
        client = Client()
        client.login(username='testuser@example.com', password='Password123!')
        
        # Verify that UserDeviceSession was created
        sessions = UserDeviceSession.objects.filter(user=self.user)
        self.assertEqual(sessions.count(), 1)


# --- FORM TESTS ---
class FormTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='ExistingPassword123!',
            first_name='Existing',
            last_name='User'
        )

    def test_registration_form_validation(self):
        # Match passwords, new email -> Valid
        data = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!',
            'mobile_number': '1234567890'
        }
        form = RegistrationForm(data=data)
        self.assertTrue(form.is_valid())

        # Mismatch passwords -> Invalid
        data['confirm_password'] = 'DifferentPassword123!'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)

        # Duplicate email -> Invalid
        data['email'] = 'existing@example.com'
        data['confirm_password'] = 'NewPassword123!'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_profile_update_form_validation(self):
        # Update user profile with correct password confirmation -> Valid
        form_data = {
            'first_name': 'UpdatedName',
            'last_name': 'UpdatedLast',
            'email': 'existing@example.com',
            'password': 'ExistingPassword123!'  # correct validation password
        }
        form = ProfileUpdateForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

        # Update user profile with incorrect password confirmation -> Invalid
        form_data['password'] = 'IncorrectPassword!'
        form = ProfileUpdateForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)


# --- VIEW TESTS ---
class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'agent@ciphervault.io'
        self.password = 'SuperSecret123!'
        self.user = User.objects.create_user(
            username=self.username,
            email=self.username,
            password=self.password,
            first_name='Cipher',
            last_name='Agent'
        )
        self.profile = UserProfile.objects.create(user=self.user, mobile_number='+15555555555')

    def test_landing_view(self):
        # Unauthenticated client
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')

        # Authenticated client should redirect to dashboard
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('landing'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_register_view(self):
        # GET unauthenticated loads register page
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/register.html')

        # POST register a new user
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'mobile_number': '9876543210'
        }
        response = self.client.post(reverse('register'), data)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(email='jane.doe@example.com').exists())
        self.assertTrue(UserProfile.objects.filter(mobile_number='9876543210').exists())

    def test_dashboard_view_counts(self):
        self.client.login(username=self.username, password=self.password)
        
        # Create some logs
        CryptoLog.objects.create(user=self.user, operation_type='ENCRYPT', text_fragment='...', full_cipher='...', status='SUCCESS')
        CryptoLog.objects.create(user=self.user, operation_type='ENCRYPT', text_fragment='...', full_cipher='...', status='SUCCESS')
        CryptoLog.objects.create(user=self.user, operation_type='DECRYPT', text_fragment='...', full_cipher='...', status='SUCCESS')
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_encryptions'], 2)
        self.assertEqual(response.context['total_decryptions'], 1)
        self.assertEqual(len(response.context['recent_logs']), 3)

    def test_encrypt_view_generation_and_logging(self):
        self.client.login(username=self.username, password=self.password)
        
        # Test encryption with custom key
        encrypt_data = {
            'raw_text': 'This is a message to encrypt',
            'encryption_key': 'CustomKey123'
        }
        response = self.client.post(reverse('encrypt'), encrypt_data)
        self.assertEqual(response.status_code, 200)
        
        # Find the log and check properties
        log = CryptoLog.objects.filter(user=self.user, operation_type='ENCRYPT').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'SUCCESS')
        encrypted_text = response.context['encrypted_text']
        self.assertEqual(log.full_cipher, encrypted_text)
        
        # Verify it can be decrypted with the custom key
        self.assertEqual(cipher.decrypt_text(encrypted_text, 'CustomKey123'), 'This is a message to encrypt')

        # Test encryption with AUTO GENERATED key (empty encryption_key)
        encrypt_data_auto = {
            'raw_text': 'Auto key text',
            'encryption_key': ''
        }
        response_auto = self.client.post(reverse('encrypt'), encrypt_data_auto)
        self.assertEqual(response_auto.status_code, 200)
        generated_key = response_auto.context['generated_key']
        self.assertTrue(len(generated_key) > 0)
        encrypted_text_auto = response_auto.context['encrypted_text']
        
        # Verify validation of decryption of that auto text
        self.assertEqual(cipher.decrypt_text(encrypted_text_auto, generated_key), 'Auto key text')

    def test_decrypt_view_creates_verification_and_emails(self):
        self.client.login(username=self.username, password=self.password)
        
        raw_msg = "Decryption test message"
        cipher_msg = cipher.encrypt_text(raw_msg, "Key123!")
        
        decrypt_data = {
            'cipher_text': cipher_msg,
            'decryption_key': 'Key123!'
        }
        
        response = self.client.post(reverse('decrypt'), decrypt_data)
        # Should redirect back to 'decrypt' view
        self.assertRedirects(response, reverse('decrypt'))

        # Verify DecryptionVerification object is created
        verification = DecryptionVerification.objects.filter(user=self.user).last()
        self.assertIsNotNone(verification)
        self.assertEqual(verification.cipher_text, cipher_msg)
        self.assertEqual(verification.decryption_key, 'Key123!')
        self.assertFalse(verification.is_used)

        # Check that verification email was sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.username])
        verify_url = reverse('verify_decryption', kwargs={'token': verification.token})
        self.assertIn(str(verification.token), sent_email.body)
        self.assertIn(verify_url, sent_email.body)

    def test_verify_decryption_view(self):
        self.client.login(username=self.username, password=self.password)
        
        raw_msg = "Super secret vault content"
        key = "Key123!"
        cipher_msg = cipher.encrypt_text(raw_msg, key)
        
        verification = DecryptionVerification.objects.create(
            user=self.user,
            cipher_text=cipher_msg,
            decryption_key=key
        )
        
        # Verify valid decryption flow
        verify_url = reverse('verify_decryption', kwargs={'token': verification.token})
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/decrypt.html')
        self.assertEqual(response.context['decrypted_text'], raw_msg)
        
        # Verification check should mark it as used
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)
        
        # CryptoLog should be generated for DECRYPT operation
        log = CryptoLog.objects.filter(user=self.user, operation_type='DECRYPT').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'SUCCESS')
        self.assertEqual(log.full_cipher, raw_msg)

        # Accessing verified token again should redirect because is_used=True (404 triggered in get_object_or_404)
        response_used = self.client.get(verify_url)
        self.assertEqual(response_used.status_code, 404)

        # Testing with wrong key
        bad_verification = DecryptionVerification.objects.create(
            user=self.user,
            cipher_text=cipher_msg,
            decryption_key="wrong_key"
        )
        bad_verify_url = reverse('verify_decryption', kwargs={'token': bad_verification.token})
        response_bad = self.client.get(bad_verify_url)
        self.assertRedirects(response_bad, reverse('decrypt'))
        
        # Cryptolog should record a fail log
        fail_log = CryptoLog.objects.filter(user=self.user, operation_type='DECRYPT', status='FAILED').first()
        self.assertIsNotNone(fail_log)
        self.assertEqual(fail_log.full_cipher, 'FAILED')

    def test_verify_decryption_unauthorized_user(self):
        other_user = User.objects.create_user(
            username='other@ciphervault.io',
            email='other@ciphervault.io',
            password='Password123!'
        )
        UserProfile.objects.create(user=other_user, mobile_number='+15555555556')

        # Create verification for 'other_user'
        verification = DecryptionVerification.objects.create(
            user=other_user,
            cipher_text='some_cipher',
            decryption_key='key'
        )

        # Log in as primary test user and attempt to verify other_user's verification
        self.client.login(username=self.username, password=self.password)
        verify_url = reverse('verify_decryption', kwargs={'token': verification.token})
        response = self.client.get(verify_url)
        self.assertRedirects(response, reverse('dashboard'))

    def test_profile_view_update(self):
        self.client.login(username=self.username, password=self.password)
        
        # Initial view
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/profile.html')
        
        # Post valid profile updates with current password
        update_data = {
            'first_name': 'NewFirstName',
            'last_name': 'NewLastName',
            'email': 'new_email@ciphervault.io',
            'password': self.password
        }
        res_post = self.client.post(reverse('profile'), update_data)
        self.assertRedirects(res_post, reverse('profile'))
        
        # Refresh and verify
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'NewFirstName')
        self.assertEqual(self.user.last_name, 'NewLastName')
        self.assertEqual(self.user.email, 'new_email@ciphervault.io')

    def test_security_center_score(self):
        self.client.login(username=self.username, password=self.password)
        
        # No logs: should return 100
        response = self.client.get(reverse('security_center'))
        self.assertEqual(response.context['security_score'], 100)

        # 4 success logs, 1 failed log: should return 80% security score
        for _ in range(4):
            CryptoLog.objects.create(user=self.user, operation_type='ENCRYPT', status='SUCCESS')
        CryptoLog.objects.create(user=self.user, operation_type='DECRYPT', status='FAILED')
        
        response2 = self.client.get(reverse('security_center'))
        self.assertEqual(response2.context['security_score'], 80)
        self.assertEqual(response2.context['recent_threat'].status, 'FAILED')
