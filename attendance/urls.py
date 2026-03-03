from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.sessions_view, name='sessions'),
]
