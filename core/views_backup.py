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
        uploaded_file = request.FILES.get('backup_file') # For restoring from uploaded file
        restore_option = request.POST.get('restore_option') # For restoring from existing file ('single:filename' or 'full:dbname:medianame')
        
        backup_dir = ensure_backup_dir()
        file_path = None
        restore_type = None
        
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
        elif restore_option:
            if restore_option.startswith('full:'):
                parts = restore_option.split(':')
                if len(parts) == 3:
                    _, db_name, media_name = parts
                    db_path = os.path.join(backup_dir, db_name)
                    media_path = os.path.join(backup_dir, media_name)
                    if not os.path.exists(db_path) or not os.path.exists(media_path):
                        messages.error(request, "Một trong các file phục hồi tổng hợp không tồn tại.")
                        return redirect('core:backup_dashboard')
                    file_path = {'db': db_path, 'media': media_path}
                    restore_type = 'full'
                else:
                    messages.error(request, "Định dạng tùy chọn full không hợp lệ.")
                    return redirect('core:backup_dashboard')
            elif restore_option.startswith('single:'):
                filename = restore_option.split(':', 1)[1]
                if '..' in filename or filename.startswith('/'):
                    return HttpResponseBadRequest("Invalid filename")
                file_path = os.path.join(backup_dir, filename)
                if not os.path.exists(file_path):
                    messages.error(request, "File phục hồi nội bộ không tồn tại.")
                    return redirect('core:backup_dashboard')
                restore_type = 'data' if filename.endswith('.json') else 'media'
            else:
                messages.error(request, "Tùy chọn không hợp lệ.")
                return redirect('core:backup_dashboard')
        else:
             messages.error(request, "Không có tham số nào được cung cấp để phục hồi.")
             return redirect('core:backup_dashboard')
             
        try:
            safe_restore(file_path, restore_type)
            messages.success(request, f"Phục hồi hệ thống ({restore_type}) thành công. Lưu ý: Có thể bạn sẽ phải đăng nhập lại nếu phục hồi dữ liệu.")
        except Exception as e:
            messages.error(request, f"Lỗi phục hồi: {e}")
        finally:
            if uploaded_file and file_path and isinstance(file_path, str) and os.path.exists(file_path):
                # Clean up temp file
                os.remove(file_path)
                
        return redirect('core:backup_dashboard')

    # GET Request: Prepare data for select box
    files = list_backups()
    timestamps = {}
    for f in files:
        name = f['name']
        if '_backup_' in name:
            ts = name.split('_backup_')[-1].split('.')[0]
            if ts not in timestamps:
                timestamps[ts] = {'data': None, 'media': None, 'ts': ts}
            if f['type'] == 'data': timestamps[ts]['data'] = name
            if f['type'] == 'media': timestamps[ts]['media'] = name
            
    full_backups = [v for v in timestamps.values() if v['data'] and v['media']]
    full_backups.sort(key=lambda x: x['ts'], reverse=True)

    return render(request, 'core/backup_restore.html', {
        'backups': files,
        'full_backups': full_backups
    })
