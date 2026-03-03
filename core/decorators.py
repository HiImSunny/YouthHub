"""
RBAC Decorators for YouthHub.
Enforce role-based access control on views.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect


def admin_required(view_func):
    """Allow only ADMIN role. Redirect others with error message."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            messages.error(request, 'Bạn không có quyền truy cập trang này. Chỉ Admin mới được phép.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def staff_required(view_func):
    """Allow ADMIN and STAFF roles. Block STUDENT."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role == 'STUDENT':
            messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def student_required(view_func):
    """Allow only STUDENT role."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != 'STUDENT':
            messages.error(request, 'Tính năng này chỉ dành cho Sinh viên.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped
