from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('auth/', include('users.urls')),
    path('activities/', include('activities.urls')),
    path('attendance/', include('attendance.urls')),
    path('ai/', include('ai_assistant.urls')),
    # Student portal — clean URLs at /student/
    path('student/', include('students.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
