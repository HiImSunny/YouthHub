from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from core.decorators import admin_required

User = get_user_model()


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.status == 'LOCKED':
                messages.error(request, 'Tài khoản đã bị khóa. Vui lòng liên hệ Admin.')
            else:
                login(request, user)
                next_url = request.GET.get('next', 'core:dashboard')
                return redirect(next_url)
        else:
            messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu.')

    return render(request, 'users/login.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'Đã đăng xuất thành công.')
    return redirect('users:login')


@login_required
def profile_view(request):
    """View and update own user profile."""
    if request.method == 'POST':
        user = request.user
        user.full_name = request.POST.get('full_name', user.full_name)
        user.phone = request.POST.get('phone', user.phone)
        user.save(update_fields=['full_name', 'phone', 'updated_at'])
        messages.success(request, 'Cập nhật thông tin thành công!')
        return redirect('users:profile')

    return render(request, 'users/profile.html')


# ─── User Management (ADMIN only) ─────────────────────────────────────────────

@admin_required
def user_management_view(request):
    """List all users with filters. ADMIN only."""
    users = User.objects.all().order_by('role', 'full_name')

    # Filters
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)

    status_filter = request.GET.get('status')
    if status_filter:
        users = users.filter(status=status_filter)

    search = request.GET.get('q')
    if search:
        users = users.filter(full_name__icontains=search) | users.filter(username__icontains=search)

    context = {
        'users': users,
        'role_choices': User.Role.choices,
        'status_choices': User.Status.choices,
        'current_role': role_filter or '',
        'current_status': status_filter or '',
        'search_query': search or '',
        'total_users': User.objects.count(),
        'total_admin': User.objects.filter(role='ADMIN').count(),
        'total_staff': User.objects.filter(role='STAFF').count(),
        'total_student': User.objects.filter(role='STUDENT').count(),
    }
    return render(request, 'users/management.html', context)


@admin_required
def user_toggle_status(request, pk):
    """Toggle ACTIVE/LOCKED status for a user. ADMIN only."""
    target_user = get_object_or_404(User, pk=pk)

    if target_user == request.user:
        messages.error(request, 'Bạn không thể khóa chính tài khoản của mình.')
        return redirect('users:management')

    if request.method == 'POST':
        if target_user.status == 'ACTIVE':
            target_user.status = 'LOCKED'
            target_user.is_active = False
            messages.success(request, f'Đã khóa tài khoản "{target_user.full_name}".')
        else:
            target_user.status = 'ACTIVE'
            target_user.is_active = True
            messages.success(request, f'Đã mở khóa tài khoản "{target_user.full_name}".')
        target_user.save(update_fields=['status', 'is_active', 'updated_at'])

    return redirect('users:management')


@admin_required
def user_change_role(request, pk):
    """Change user role. ADMIN only."""
    target_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        valid_roles = [r[0] for r in User.Role.choices]
        if new_role in valid_roles:
            old_role = target_user.role
            target_user.role = new_role
            target_user.save(update_fields=['role', 'updated_at'])
            messages.success(
                request,
                f'Đã đổi quyền "{target_user.full_name}" từ {old_role} → {new_role}.'
            )
        else:
            messages.error(request, 'Role không hợp lệ.')

    return redirect('users:management')
