import os
import zipfile
import logging
from datetime import datetime
from django.conf import settings
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def ensure_backup_dir():
    backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def list_backups():
    backup_dir = ensure_backup_dir()
    files = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        f_path = os.path.join(backup_dir, f)
        if os.path.isfile(f_path):
            stat = os.stat(f_path)
            ftype = 'data' if f.endswith('.json') else 'media' if f.endswith('.zip') else 'unknown'
            if f.endswith('.json') and 'media' in f: ftype = 'media' # Just in case
            if ftype == 'unknown': continue
            files.append({
                'name': f,
                'path': f_path,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime),
                'type': ftype
            })
    return files

def create_database_backup(prefix=''):
    backup_dir = ensure_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}data_backup_{timestamp}.json" if prefix else f"data_backup_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            call_command(
                'dumpdata',
                natural_foreign=True,
                natural_primary=True,
                exclude=['contenttypes', 'auth.permission', 'admin.logentry', 'sessions.session', 'core.auditlog'],
                indent=2,
                stdout=f
            )
        return filepath
    except Exception as e:
        logger.error(f"Backup Database Error: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        raise e

def create_media_backup(prefix=''):
    backup_dir = ensure_backup_dir()
    media_root = settings.MEDIA_ROOT
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}media_backup_{timestamp}.zip" if prefix else f"media_backup_{timestamp}.zip"
    filepath = os.path.join(backup_dir, filename)

    exclude_dirs = {'backups', '__pycache__', '.git', 'node_modules'}
    
    try:
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(media_root):
                for dirname, subdirs, files in os.walk(media_root):
                    subdirs[:] = [d for d in subdirs if d not in exclude_dirs]
                    for fname in files:
                        f_path = os.path.join(dirname, fname)
                        arcname = os.path.relpath(f_path, media_root)
                        zf.write(f_path, arcname)
        return filepath
    except Exception as e:
        logger.error(f"Backup Media Error: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        raise e

def create_full_backup(prefix=''):
    db_path = create_database_backup(prefix)
    try:
        media_path = create_media_backup(prefix)
        return {'db': db_path, 'media': media_path}
    except Exception as e:
        if os.path.exists(db_path):
            os.remove(db_path)
        raise e

def restore_database(filepath):
    # Clear ContentType before loading to avoid conflict
    ContentType.objects.all().delete()
    call_command('loaddata', filepath, verbosity=1)

def restore_media(filepath):
    media_root = settings.MEDIA_ROOT
    if not zipfile.is_zipfile(filepath):
        raise ValueError("File is not a valid ZIP")
        
    with zipfile.ZipFile(filepath, 'r') as zf:
        for member in zf.namelist():
            member_path = os.path.realpath(os.path.join(media_root, member))
            if not member_path.startswith(os.path.realpath(media_root)):
                raise ValueError(f"Path traversal detected: {member}")
        zf.extractall(media_root)

def safe_restore(restore_file_path, restore_type):
    """
    Restore an toàn với auto-backup trước.
    NẾU auto-backup thất bại -> DỪNG restore, thông báo Admin.
    """
    try:
        backup_result = create_full_backup(prefix='auto_before_restore_')
        logger.info(f"Auto-backup thành công: {backup_result}")
    except Exception as e:
        logger.error(f"Auto-backup thất bại: {e}")
        raise RuntimeError(f"Không thể tạo auto-backup trước khi restore. Quá trình restore đã bị HỦY để bảo vệ dữ liệu hiện tại. Chi tiết lỗi: {e}")
        
    try:
        if restore_type == 'data':
            restore_database(restore_file_path)
        elif restore_type == 'media':
            restore_media(restore_file_path)
        elif restore_type == 'full':
            restore_database(restore_file_path['db'])
            restore_media(restore_file_path['media'])
    except Exception as e:
        logger.error(f"Restore thất bại: {e}")
        raise e
