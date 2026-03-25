from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, WorkerProfile, EmployerProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['phone_number', 'email', 'role', 'is_active', 'username']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Phone', {'fields': ('role', 'phone_number')}),
    )


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'city', 'years_experience', 'verification_status', 'user']
    list_filter = ['verification_status', 'national_id_status']
    search_fields = ['full_name', 'city']


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'city', 'verification_status', 'user']
    list_filter = ['verification_status']
    search_fields = ['company_name', 'city']
