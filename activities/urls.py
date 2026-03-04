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
    path('pending/', views.activity_pending_list, name='pending_list'),
    # C1/C2: Student activity portal
    path('student/activities/', views.student_activity_list, name='student_list'),
    # C3: Student dashboard
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    # D1/D2/D3: Budget management
    path('<int:activity_pk>/budget/', views.budget_detail, name='budget_detail'),
    path('<int:activity_pk>/budget/create/', views.budget_create, name='budget_create'),
    path('<int:activity_pk>/budget/add-item/', views.budget_add_item, name='budget_add_item'),
    path('<int:activity_pk>/budget/delete-item/<int:item_pk>/', views.budget_delete_item, name='budget_delete_item'),
    path('<int:activity_pk>/budget/submit/', views.budget_submit, name='budget_submit'),
    path('<int:activity_pk>/budget/approve/', views.budget_approve, name='budget_approve'),
    path('<int:activity_pk>/budget/reject/', views.budget_reject, name='budget_reject'),
]
