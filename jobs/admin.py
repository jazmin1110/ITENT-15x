from django.contrib import admin
from .models import Job, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'city', 'daily_rate', 'status', 'employer', 'created_at']
    list_filter = ['status', 'city']
    search_fields = ['title', 'city']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['worker', 'job', 'status', 'created_at']
    list_filter = ['status']
