from django.contrib import admin
from .models import Organization, OrganizationMember, Semester


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type', 'parent', 'status')
    list_filter = ('type', 'status')
    search_fields = ('name', 'code')


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'position', 'is_officer', 'joined_at')
    list_filter = ('is_officer', 'organization')


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'academic_year')
