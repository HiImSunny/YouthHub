from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('', views.activity_list, name='list'),
    path('create/', views.activity_create, name='create'),
    path('<int:pk>/', views.activity_detail, name='detail'),
    path('<int:pk>/edit/', views.activity_edit, name='edit'),
    path('<int:pk>/delete/', views.activity_delete, name='delete'),
    path('<int:pk>/approve/', views.activity_approve, name='approve'),
    path('<int:pk>/reject/', views.activity_reject, name='reject'),
    path('<int:pk>/register/', views.activity_register, name='register'),
    path('<int:pk>/cancel-registration/', views.activity_cancel_registration, name='cancel_registration'),
]
