from django.urls import path
from . import views

app_name = 'point_categories'

urlpatterns = [
    path('', views.point_category_list, name='point_category_list'),
    path('create/', views.point_category_create, name='point_category_create'),
    path('<int:pk>/edit/', views.point_category_edit, name='point_category_edit'),
    path('<int:pk>/delete/', views.point_category_delete, name='point_category_delete'),
]
