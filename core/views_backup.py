import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, Http404, HttpResponseBadRequest, FileResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .utils_backup import list_backups, create_database_backup, create_media_backup, create_full_backup, safe_restore, ensure_backup_dir

def is_superuser(user):
    return user.is_active and user.is_superuser

@user_passes_test(is_superuser)
def backup_dashboard_view(request):
    files = list_backups()
    return render(request, 'core/backup_dashboard.html', {'backups': files})

@user_passes_test(is_superuser)
@require_POST
def backup_create_view(request):
    backup_type = request.POST.get('type')
    try:
        if backup_type == 'data':
            create_database_backup()
            messages.success(request, "Đã tạo bản sao lưu dữ liệu (Database) thành công.")
        elif backup_type == 'media':
            create_media_backup()
            messages.success(request, "Đã tạo bản sao lưu tệp đính kèm (Media) thành công.")
        elif backup_type == 'full':
            create_full_backup()
            messages.success(request, "Đã tạo bản sao lưu toàn bộ (Full Backup) thành công.")
        else:
            messages.error(request, "Loại backup không hợp lệ.")
    except Exception as e:
        messages.error(request, f"Lỗi tạo backup: {e}")
    return redirect('core:backup_dashboard')

@user_passes_test(is_superuser)
def backup_download_view(request, filename):
    if '..' in filename or filename.startswith('/'):
        return HttpResponseBadRequest("Invalid filename")
    
    backup_dir = ensure_backup_dir()
    file_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(file_path):
        raise Http404("File không tồn tại")
        
    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    return response

@user_passes_test(is_superuser)
@require_POST
def backup_delete_view(request, filename):
    if '..' in filename or filename.startswith('/'):
        return HttpResponseBadRequest("Invalid filename")
        
    backup_dir = ensure_backup_dir()
    file_path = os.path.join(backup_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        messages.success(request, f"Đã xóa bản sao lưu {filename}.")
    else:
        messages.error(request, "File không tồn tại.")
        
    return redirect('core:backup_dashboard')

@user_passes_test(is_superuser)
def backup_restore_view(request):
    if request.method == 'POST':
        restore_type = request.POST.get('type') # 'data' or 'media'
        filename = request.POST.get('filename') # For restoring from existing file
        uploaded_file = request.FILES.get('backup_file') # For restoring from uploaded file
        
        if not restore_type and filename:
            restore_type = 'data' if filename.endswith('.json') else 'media'
            
        backup_dir = ensure_backup_dir()
        file_path = None
        
        if uploaded_file:
            # Save uploaded file temporarily
            temp_path = os.path.join(backup_dir, f"temp_upload_{uploaded_file.name}")
            with open(temp_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            file_path = temp_path
            
            # auto detect type
            if uploaded_file.name.endswith('.json'):
                restore_type = 'data'
            elif uploaded_file.name.endswith('.zip'):
                restore_type = 'media'
            else:
                messages.error(request, "Định dạng file không hỗ trợ. Sử dụng .json cho Data và .zip cho Media.")
                os.remove(temp_path)
                return redirect('core:backup_dashboard')
        elif filename:
            if '..' in filename or filename.startswith('/'):
                return HttpResponseBadRequest("Invalid filename")
            file_path = os.path.join(backup_dir, filename)
            if not os.path.exists(file_path):
                messages.error(request, "File phục hồi nội bộ không tồn tại.")
                return redirect('core:backup_dashboard')
        else:
             messages.error(request, "Không có file nào được cung cấp để phục hồi.")
             return redirect('core:backup_dashboard')
             
        try:
            safe_restore(file_path, restore_type)
            messages.success(request, f"Phục hồi hệ thống ({restore_type}) thành công. Lưu ý: Có thể bạn sẽ phải đăng nhập lại.")
        except Exception as e:
            messages.error(request, f"Lỗi phục hồi: {e}")
        finally:
            if uploaded_file and file_path and os.path.exists(file_path):
                # Clean up temp file
                os.remove(file_path)
                
        return redirect('core:backup_dashboard')

    return render(request, 'core/backup_restore.html')
