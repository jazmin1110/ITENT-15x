from django.contrib import admin
from .models import ApplicationSkillRating, Job, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'city',
        'daily_rate',
        'rate_type',
        'positions_needed',
        'status',
        'auto_closed_when_filled',
        'employer',
        'created_at',
    ]
    list_filter = ['status', 'city', 'auto_closed_when_filled']
    search_fields = ['title', 'city']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['worker', 'job', 'status', 'created_at']
    list_filter = ['status']


@admin.register(ApplicationSkillRating)
class ApplicationSkillRatingAdmin(admin.ModelAdmin):
    list_display = ['application', 'skill_name', 'score', 'updated_at']
    list_filter = ['score']
    search_fields = ['skill_name']
