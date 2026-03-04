from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    # Admin: User Management
    path('management/', views.user_management_view, name='management'),
    path('management/<int:pk>/toggle-status/', views.user_toggle_status, name='toggle_status'),
    path('management/<int:pk>/change-role/', views.user_change_role, name='change_role'),
]
