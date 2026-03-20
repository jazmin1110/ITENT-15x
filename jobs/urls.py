from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('post/', views.post_job, name='post_job'),
    path('my-jobs/', views.employer_jobs, name='employer_jobs'),
    path('<int:job_id>/applicants/', views.applicants, name='applicants'),
    path('application/<int:application_id>/status/<str:status>/', views.update_application_status, name='update_application_status'),
    path('my-applications/', views.worker_applications, name='worker_applications'),
    path('<int:job_id>/toggle-status/', views.toggle_job_status, name='toggle_job_status'),
    # Rating URLs
    path('application/<int:application_id>/rate-worker/', views.rate_worker, name='rate_worker'),
    path('application/<int:application_id>/rate-employer/', views.rate_employer, name='rate_employer'),
    path('ratings/<int:user_id>/', views.view_ratings, name='view_ratings'),
]
