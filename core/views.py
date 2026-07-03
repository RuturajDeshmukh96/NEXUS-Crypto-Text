from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, CreateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging
import uuid

from .models import CryptoLog, DecryptionVerification, UserProfile
from . import cipher
from .forms import RegistrationForm, EncryptForm, DecryptForm, ProfileUpdateForm

logger = logging.getLogger(__name__)

# ─── Gemini AI helper ───────────────────────────────────────────────────────

def get_ai_analysis(text: str) -> dict:
    """
    Analyse decrypted text using Google Gemini (free tier).
    Returns a dict with keys: summary, sentiment, word_count, threat, language.
    Falls back gracefully if the API key is missing or quota is exceeded.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key or api_key == 'your-gemini-api-key-here':
        return _fallback_analysis(text)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = (
            "Analyse the following text and respond with ONLY a JSON object "
            "(no markdown, no code fences) with these exact keys:\n"
            "  summary     – one sentence summary (max 20 words)\n"
            "  sentiment   – one word: Positive | Neutral | Negative\n"
            "  word_count  – integer word count\n"
            "  threat      – boolean, true if message contains threats/harmful content\n"
            "  language    – detected language (e.g. English)\n\n"
            f"Text:\n{text[:2000]}"
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # strip markdown fences if model wraps in them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        import json
        data = json.loads(raw)
        data['ai_powered'] = True
        return data
    except Exception as e:
        logger.warning(f"Gemini AI analysis failed: {e}")
        return _fallback_analysis(text)


def _fallback_analysis(text: str) -> dict:
    """Basic local analysis when Gemini is unavailable."""
    words = text.split()
    return {
        'summary': text[:80] + ('...' if len(text) > 80 else ''),
        'sentiment': 'Neutral',
        'word_count': len(words),
        'threat': False,
        'language': 'Unknown',
        'ai_powered': False,
    }


# ─── Views ───────────────────────────────────────────────────────────────────

class LandingView(TemplateView):
    template_name = 'landing.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

class RegisterView(View):
    template_name = 'auth/register.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, {'form': RegistrationForm()})

    def post(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                from django.contrib.auth.models import User
                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )
                UserProfile.objects.create(user=user, mobile_number=form.cleaned_data['mobile_number'])
                login(request, user)
                return redirect('dashboard')
            except Exception as e:
                logger.error(f"Registration error: {e}")
                return render(request, self.template_name, {'form': form, 'error': 'Registration failed. Please try again.'})
        return render(request, self.template_name, {'form': form})

class ForgotPasswordView(TemplateView):
    template_name = 'auth/forgot_password.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = CryptoLog.objects.filter(user=self.request.user)
        context['total_encryptions'] = logs.filter(operation_type='ENCRYPT').count()
        context['total_decryptions'] = logs.filter(operation_type='DECRYPT').count()
        context['recent_logs'] = logs[:5]
        return context

class EncryptView(LoginRequiredMixin, View):
    template_name = 'dashboard/encrypt.html'

    def get(self, request):
        return render(request, self.template_name, {'form': EncryptForm()})

    def post(self, request):
        form = EncryptForm(request.POST)
        context = {'form': form}
        
        if form.is_valid():
            raw_text = form.cleaned_data['raw_text']
            encryption_key = form.cleaned_data['encryption_key']

            if not encryption_key:
                encryption_key = cipher.generate_random_passphrase(16)
                context['generated_key'] = encryption_key

            try:
                encrypted_val = cipher.encrypt_text(raw_text, encryption_key)
                context['encrypted_text'] = encrypted_val
                
                CryptoLog.objects.create(
                    user=request.user,
                    operation_type='ENCRYPT',
                    text_fragment=encrypted_val[:30] + '...',
                    full_cipher=encrypted_val,
                    status='SUCCESS'
                )
                messages.success(request, 'Data encrypted successfully.')
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                context['error'] = 'Encryption process failed.'
                CryptoLog.objects.create(
                    user=request.user,
                    operation_type='ENCRYPT',
                    text_fragment='ERROR',
                    full_cipher='FAILED',
                    status='FAILED'
                )

        return render(request, self.template_name, context)


class DecryptView(LoginRequiredMixin, View):
    """
    Direct AI-powered decryption — no email required.
    The cipher text is decrypted immediately with the provided key.
    After successful decryption the plaintext is analysed by Gemini AI.
    """
    template_name = 'dashboard/decrypt.html'

    def get(self, request):
        return render(request, self.template_name, {'form': DecryptForm()})

    def post(self, request):
        form = DecryptForm(request.POST)
        context = {'form': form}

        if form.is_valid():
            cipher_text    = form.cleaned_data['cipher_text']
            decryption_key = form.cleaned_data['decryption_key']

            decrypted_val = cipher.decrypt_text(cipher_text, decryption_key)

            if decrypted_val is not None:
                # ── AI analysis ─────────────────────────────────────────
                ai_analysis = get_ai_analysis(decrypted_val)
                context['ai_analysis'] = ai_analysis

                context['decrypted_text'] = decrypted_val
                context['cipher_text_submitted'] = cipher_text
                context['script_override'] = 'simulate_success'

                CryptoLog.objects.create(
                    user=request.user,
                    operation_type='DECRYPT',
                    text_fragment=cipher_text[:30] + '...',
                    full_cipher=decrypted_val,
                    status='SUCCESS'
                )
                messages.success(request, 'Message decrypted and analysed by AI successfully.')
            else:
                context['error'] = 'Decryption failed — invalid cipher text or wrong key.'
                CryptoLog.objects.create(
                    user=request.user,
                    operation_type='DECRYPT',
                    text_fragment=cipher_text[:30] + '...',
                    full_cipher='FAILED',
                    status='FAILED'
                )

        return render(request, self.template_name, context)


# VerifyDecryptionView is kept for backward-compat with existing DB tokens
class VerifyDecryptionView(LoginRequiredMixin, View):
    template_name = 'dashboard/decrypt.html'

    def get(self, request, token):
        verification = get_object_or_404(DecryptionVerification, token=token, is_used=False)
        context = {'form': DecryptForm()}

        if verification.is_expired:
            messages.error(request, 'The verification link has expired.')
            return redirect('decrypt')

        if verification.user != request.user:
            messages.error(request, 'Unauthorized access.')
            return redirect('dashboard')

        decrypted_val = cipher.decrypt_text(verification.cipher_text, verification.decryption_key)
        
        if decrypted_val is not None:
            verification.is_used = True
            verification.save()
            
            ai_analysis = get_ai_analysis(decrypted_val)
            context['ai_analysis'] = ai_analysis
            context['decrypted_text'] = decrypted_val
            context['cipher_text_submitted'] = verification.cipher_text
            context['script_override'] = 'simulate_success'
            
            CryptoLog.objects.create(
                user=request.user,
                operation_type='DECRYPT',
                text_fragment=verification.cipher_text[:30] + '...',
                full_cipher=decrypted_val,
                status='SUCCESS'
            )
            messages.success(request, 'Identity verified. Message decrypted.')
        else:
            messages.error(request, 'Decryption failed. Invalid cipher or key.')
            CryptoLog.objects.create(
                user=request.user,
                operation_type='DECRYPT',
                text_fragment=verification.cipher_text[:30] + '...',
                full_cipher='FAILED',
                status='FAILED'
            )
            return redirect('decrypt')

        return render(request, self.template_name, context)


class MessageHistoryView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/message_history.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        return CryptoLog.objects.filter(user=self.request.user)

class PasswordGeneratorView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/password_generator.html'

class ProfileView(LoginRequiredMixin, View):
    template_name = 'dashboard/profile.html'
    
    def get(self, request):
        return render(request, self.template_name, {'form': ProfileUpdateForm(instance=request.user)})
        
    def post(self, request):
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Operator profile updated successfully.')
            return redirect('profile')
        return render(request, self.template_name, {'form': form})

class SecurityCenterView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/security_center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import CryptoLog, UserDeviceSession
        logs = CryptoLog.objects.filter(user=self.request.user)
        total = logs.count()
        success = logs.filter(status='SUCCESS').count()
        context['security_score'] = int((success / total) * 100) if total > 0 else 100
        context['recent_threat'] = logs.filter(status='FAILED').first()
        context['sessions'] = UserDeviceSession.objects.filter(user=self.request.user)[:5]
        return context
