from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.LandingView.as_view(), name='landing'),
    
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    
    # Dashboard features
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('encrypt/', views.EncryptView.as_view(), name='encrypt'),
    path('decrypt/', views.DecryptView.as_view(), name='decrypt'),
    path('history/', views.MessageHistoryView.as_view(), name='message_history'),
    path('password-generator/', views.PasswordGeneratorView.as_view(), name='password_generator'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('security-center/', views.SecurityCenterView.as_view(), name='security_center'),
    path('verify-decryption/<uuid:token>/', views.VerifyDecryptionView.as_view(), name='verify_decryption'),
]
