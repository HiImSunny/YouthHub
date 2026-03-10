from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

from core.decorators import admin_required
from users.models import StudentProfile

User = get_user_model()


# ─── Authentication ────────────────────────────────────────────────────────────

def login_view(request):
    """Handle user login (supports username OR email)."""
    if request.user.is_authenticated:
        # Route already-logged-in users to the correct dashboard by role
        if request.user.role == 'STUDENT':
            return redirect('students:dashboard')
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
                # Honour 'next' param if provided, otherwise use role-based redirect
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('users:post_login_redirect')
        else:
            messages.error(request, 'Sai tên đăng nhập/email hoặc mật khẩu.')

    return render(request, 'users/login.html')


def register_view(request):
    """Register a new STUDENT account."""
    if request.user.is_authenticated:
        if request.user.role == 'STUDENT':
            return redirect('students:dashboard')
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        student_code = request.POST.get('student_code', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        # Validation
        errors = []
        if not username:
            errors.append('Username không được để trống.')
        if not email:
            errors.append('Email không được để trống.')
        if not full_name:
            errors.append('Họ tên không được để trống.')
        if not student_code:
            errors.append('Mã sinh viên không được để trống.')
        if len(password) < 6:
            errors.append('Mật khẩu phải ít nhất 6 ký tự.')
        if password != password2:
            errors.append('Mật khẩu xác nhận không khớp.')

        if User.objects.filter(username__iexact=username).exists():
            errors.append('Username đã tồn tại.')
        if User.objects.filter(email__iexact=email).exists():
            errors.append('Email đã được sử dụng.')
        if StudentProfile.objects.filter(student_code__iexact=student_code).exists():
            errors.append('Mã sinh viên đã tồn tại.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'users/register.html', {
                'form_data': request.POST,
            })

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role='STUDENT',
                status='ACTIVE',
            )
            StudentProfile.objects.create(
                user=user,
                student_code=student_code,
            )
            messages.success(request, 'Đăng ký thành công! Hãy đăng nhập.')
            return redirect('users:login')
        except IntegrityError:
            messages.error(request, 'Lỗi tạo tài khoản. Vui lòng thử lại.')

    return render(request, 'users/register.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'Đã đăng xuất thành công.')
    return redirect('users:login')


@login_required
def post_login_redirect(request):
    """Role-based redirect after login. Used as LOGIN_REDIRECT_URL target."""
    if request.user.role == 'STUDENT':
        return redirect('students:dashboard')
    return redirect('core:dashboard')


# ─── Profile & Password ───────────────────────────────────────────────────────

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


@login_required
def change_password_view(request):
    """Change current user's password."""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_password):
            messages.error(request, 'Mật khẩu hiện tại không đúng.')
        elif len(new_password) < 6:
            messages.error(request, 'Mật khẩu mới phải ít nhất 6 ký tự.')
        elif new_password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('users:profile')

    return render(request, 'users/change_password.html')


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
        from django.db.models import Q
        users = users.filter(Q(full_name__icontains=search) | Q(username__icontains=search))

    org_filter = request.GET.get('org')
    if org_filter:
        users = users.filter(memberships__organization_id=org_filter).distinct()

    from core.models import Organization
    from core.permissions import group_orgs_by_root
    organizations = Organization.objects.filter(status=True).order_by('name')

    context = {
        'users': users,
        'role_choices': User.Role.choices,
        'status_choices': User.Status.choices,
        'org_groups': group_orgs_by_root(organizations),
        'current_role': role_filter or '',
        'current_status': status_filter or '',
        'current_org': org_filter or '',
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
            msg = 'Đã khóa tài khoản.'
        else:
            target_user.status = 'ACTIVE'
            target_user.is_active = True
            msg = 'Đã mở khóa tài khoản.'
        target_user.save(update_fields=['status', 'is_active', 'updated_at'])
        messages.success(request, msg)

    return redirect('users:management')


@admin_required
def user_change_role(request, pk):
    """Change user role. ADMIN only."""
    target_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        valid_roles = [r[0] for r in User.Role.choices]
        if new_role in valid_roles:
            target_user.role = new_role
            target_user.save(update_fields=['role', 'updated_at'])
            messages.success(request, 'Đã đổi quyền thành công.')
        else:
            messages.error(request, 'Role không hợp lệ.')

    return redirect('users:management')


@admin_required
def login_as_user(request, pk):
    """Allow ADMIN to login as another user for troubleshooting."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=pk)
        
        if target_user == request.user:
            messages.warning(request, 'Bạn đang đăng nhập bằng tài khoản này rồi.')
            return redirect('users:management')
        
        # Logout the current admin
        from django.contrib.auth import login
        
        # Login as the target user (requires specifying backend since authenticate() was bypassed)
        login(request, target_user, backend='users.backends.EmailOrUsernameBackend')
        messages.success(request, f'Đã đăng nhập dưới quyền của {target_user.full_name}.')
        
        if target_user.role == 'STUDENT':
            return redirect('students:dashboard')
        return redirect('core:dashboard')
        
    return redirect('users:management')


@login_required
def user_detail_view(request, pk):
    """View details of a specific user. Available to STAFF and ADMIN."""
    # Strict role check: STUDENTs generally shouldn't view arbitrary profiles
    if request.user.role not in ['ADMIN', 'STAFF']:
        messages.error(request, 'Bạn không có quyền xem thông tin người dùng khác.')
        return redirect('students:dashboard' if request.user.role == 'STUDENT' else 'core:dashboard')

    target_user = get_object_or_404(User, pk=pk)
    memberships = target_user.memberships.select_related('organization').all()
    
    from activities.models import ActivityParticipation
    from django.core.paginator import Paginator
    
    participations_qs = ActivityParticipation.objects.filter(student=target_user).select_related(
        'activity', 'activity__semester', 'activity__organization'
    ).order_by('-activity__semester__start_date', '-activity__start_time')

    paginator = Paginator(participations_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'target_user': target_user,
        'memberships': memberships,
        'participations': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'users/user_detail.html', context)
