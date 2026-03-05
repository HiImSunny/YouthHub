from django.urls import path
from . import views

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
]
