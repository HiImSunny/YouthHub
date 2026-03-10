from django.urls import path
from . import views
from .views_semester import semester_list, semester_create, semester_edit, semester_delete
from . import views_backup


app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('organizations/', views.organizations_view, name='organizations'),
    path('organizations/create/', views.organization_create, name='org_create'),
    path('organizations/<int:org_pk>/edit/', views.organization_edit, name='org_edit'),
    path('organizations/<int:org_pk>/delete/', views.organization_delete, name='org_delete'),
    path('organizations/<int:org_pk>/staff/', views.org_staff_view, name='org_staff'),
    path('organizations/<int:org_pk>/import/', views.import_members_to_org, name='org_import_members'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
    path('import-students/', views.import_students_view, name='import_students'),
    path('import-students/template/', views.download_import_template, name='import_students_template'),
    path('pending/', views.unified_pending_view, name='unified_pending'),
    
    path('semesters/', semester_list, name='semesters'),
    path('semesters/create/', semester_create, name='semester_create'),
    path('semesters/<int:pk>/edit/', semester_edit, name='semester_edit'),
    path('semesters/<int:pk>/delete/', semester_delete, name='semester_delete'),
    
    path('backup/', views_backup.backup_dashboard_view, name='backup_dashboard'),
    path('backup/create/', views_backup.backup_create_view, name='backup_create'),
    path('backup/download/<str:filename>/', views_backup.backup_download_view, name='backup_download'),
    path('backup/delete/<str:filename>/', views_backup.backup_delete_view, name='backup_delete'),
    path('backup/restore/', views_backup.backup_restore_view, name='backup_restore'),
]
