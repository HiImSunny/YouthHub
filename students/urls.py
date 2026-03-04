from django.urls import path
from activities import views as activity_views

app_name = 'students'

urlpatterns = [
    # C1/C2: Student activity portal
    path('activities/', activity_views.student_activity_list, name='portal'),
    # C3: Student dashboard
    path('dashboard/', activity_views.student_dashboard, name='dashboard'),
]
