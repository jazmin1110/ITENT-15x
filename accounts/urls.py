from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import staff_views, views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('worker-profile/', views.worker_profile, name='worker_profile'),
    path('verify-national-id/', views.verify_national_id, name='verify_national_id'),
    path('submit-worker-verification/', views.submit_worker_verification, name='submit_worker_verification'),

    path('employer-profile/', views.employer_profile, name='employer_profile'),
    path('submit-verification/', views.submit_verification, name='submit_verification'),

    path('staff/', staff_views.staff_home, name='staff_home'),
    path('staff/jobs/', staff_views.staff_jobs, name='staff_jobs'),
    path('staff/applications/', staff_views.staff_applications, name='staff_applications'),
    path('staff/users/', staff_views.staff_users, name='staff_users'),
    path('staff/conversations/', staff_views.staff_conversations, name='staff_conversations'),
    path('staff/conversations/<int:pk>/', staff_views.staff_conversation_detail, name='staff_conversation_detail'),

    path('staff/verification/employers/', views.admin_dashboard, name='staff_verification_employers'),
    path('staff/verification/workers/', views.admin_worker_dashboard, name='staff_verification_workers'),

    path(
        'admin-dashboard/',
        RedirectView.as_view(pattern_name='staff_verification_employers', permanent=False),
    ),
    path('approve-employer/<int:employer_id>/', views.approve_employer, name='approve_employer'),
    path('reject-employer/<int:employer_id>/', views.reject_employer, name='reject_employer'),
    path('revoke-employer/<int:employer_id>/', views.revoke_employer, name='revoke_employer'),

    path(
        'admin-workers/',
        RedirectView.as_view(pattern_name='staff_verification_workers', permanent=False),
    ),
    path('approve-worker/<int:worker_id>/', views.approve_worker, name='approve_worker'),
    path('reject-worker/<int:worker_id>/', views.reject_worker, name='reject_worker'),
    path('revoke-worker/<int:worker_id>/', views.revoke_worker, name='revoke_worker'),
]
