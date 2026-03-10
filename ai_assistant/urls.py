from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    # Main chat/generate page
    path('', views.chat_view, name='chat'),
    path('generate/', views.generate_view, name='generate'),
    path('status/', views.ollama_status_api, name='status'),
    path('suggest/', views.ai_suggest_api, name='suggest'),
    path('pull/', views.pull_model_api, name='pull'),

    # Async task polling
    path('task-status/<int:document_id>/', views.task_status_api, name='task_status'),

    # Document management
    path('documents/', views.documents_list, name='documents'),
    path('documents/<int:pk>/', views.document_detail, name='document_detail'),
    path('documents/<int:pk>/save/', views.document_save, name='document_save'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
]

