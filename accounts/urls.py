from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('worker-profile/', views.worker_profile, name='worker_profile'),
    path('verify-national-id/', views.verify_national_id, name='verify_national_id'),
    path('submit-worker-verification/', views.submit_worker_verification, name='submit_worker_verification'),

    path('employer-profile/', views.employer_profile, name='employer_profile'),
    path('submit-verification/', views.submit_verification, name='submit_verification'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('approve-employer/<int:employer_id>/', views.approve_employer, name='approve_employer'),
    path('reject-employer/<int:employer_id>/', views.reject_employer, name='reject_employer'),
    path('revoke-employer/<int:employer_id>/', views.revoke_employer, name='revoke_employer'),

    path('admin-workers/', views.admin_worker_dashboard, name='admin_worker_dashboard'),
    path('approve-worker/<int:worker_id>/', views.approve_worker, name='approve_worker'),
    path('reject-worker/<int:worker_id>/', views.reject_worker, name='reject_worker'),
    path('revoke-worker/<int:worker_id>/', views.revoke_worker, name='revoke_worker'),
]
