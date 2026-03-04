from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Sessions management
    path('', views.sessions_view, name='sessions'),
    path('create/', views.session_create, name='session_create'),
    path('<int:pk>/', views.session_detail, name='session_detail'),
    path('<int:pk>/qr/', views.session_qr, name='session_qr'),
    path('<int:pk>/close/', views.session_close, name='session_close'),

    # Check-in (student side)
    path('checkin/<str:token>/', views.checkin_view, name='checkin'),
    path('checkin/<str:token>/submit/', views.checkin_submit, name='checkin_submit'),

    # Records management (staff side)
    path('records/<int:session_pk>/', views.records_list, name='records_list'),
    path('records/<int:pk>/approve/', views.record_approve, name='record_approve'),
    path('records/<int:pk>/reject/', views.record_reject, name='record_reject'),

    # Points
    path('points/', views.points_view, name='points'),

    # Phase 3: Activity-level attendance verification matrix
    path('activity/<int:activity_pk>/verify/', views.activity_attendance_verify, name='activity_verify'),

    # Phase 4: Award points (individual + bulk)
    path('activity/<int:activity_pk>/award/<int:student_pk>/', views.award_student_points, name='award_student'),
    path('activity/<int:activity_pk>/award/bulk/', views.award_bulk_points, name='award_bulk'),
]
