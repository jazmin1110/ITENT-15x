from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('worker-profile/', views.worker_profile, name='worker_profile'),
    path('employer-profile/', views.employer_profile, name='employer_profile'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('toggle-verification/<int:employer_id>/', views.toggle_verification, name='toggle_verification'),
]
