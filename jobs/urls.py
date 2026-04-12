from django.urls import path
from . import views, contract_views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('post/', views.post_job, name='post_job'),
    path('my-jobs/', views.employer_jobs, name='employer_jobs'),
    path(
        '<int:job_id>/reopen-after-vacancy/',
        views.reopen_job_after_vacancy,
        name='reopen_job_after_vacancy',
    ),
    path(
        '<int:job_id>/dismiss-vacancy-prompt/',
        views.dismiss_vacancy_prompt,
        name='dismiss_vacancy_prompt',
    ),
    path('<int:job_id>/applicants/', views.applicants, name='applicants'),
    path(
        '<int:job_id>/applicants/<int:worker_id>/portfolio/',
        views.employer_worker_portfolio,
        name='employer_worker_portfolio',
    ),
    path('portfolio/item/<int:item_id>/photo/', views.portfolio_item_photo, name='portfolio_item_photo'),
    path('portfolio/item/<int:item_id>/file/', views.portfolio_item_file, name='portfolio_item_file'),
    path('application/<int:application_id>/status/<str:status>/', views.update_application_status, name='update_application_status'),
    path('application/<int:application_id>/contract/upload/', contract_views.contract_employer_upload, name='contract_employer_upload'),
    path('application/<int:application_id>/contract/worker-accept/', contract_views.contract_worker_accept, name='contract_worker_accept'),
    path('application/<int:application_id>/contract/confirm/', contract_views.contract_employer_confirm, name='contract_employer_confirm'),
    path('application/<int:application_id>/contract/download/<str:file_kind>/', contract_views.contract_download, name='contract_download'),
    path('my-applications/', views.worker_applications, name='worker_applications'),
    path('<int:job_id>/toggle-status/', views.toggle_job_status, name='toggle_job_status'),
    # Rating URLs
    path('application/<int:application_id>/rate-worker/', views.rate_worker, name='rate_worker'),
    path('application/<int:application_id>/rate-employer/', views.rate_employer, name='rate_employer'),
    path('ratings/<int:user_id>/', views.view_ratings, name='view_ratings'),
]
