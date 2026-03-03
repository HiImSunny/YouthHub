from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    # Main chat/generate page
    path('', views.chat_view, name='chat'),
    path('generate/', views.generate_view, name='generate'),
    path('status/', views.ollama_status_api, name='status'),

    # Document management
    path('documents/', views.documents_list, name='documents'),
    path('documents/<int:pk>/', views.document_detail, name='document_detail'),
    path('documents/<int:pk>/save/', views.document_save, name='document_save'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
]
