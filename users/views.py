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
                messages.error(request, 'Tai khoan da bi khoa. Vui long lien he Admin.')
            else:
                login(request, user)
                # Honour 'next' param if provided, otherwise use role-based redirect
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('users:post_login_redirect')
        else:
            messages.error(request, 'Sai ten dang nhap/email hoac mat khau.')

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
        faculty = request.POST.get('faculty', '').strip()
        class_name = request.POST.get('class_name', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        # Validation
        errors = []
        if not username:
            errors.append('Username khong duoc de trong.')
        if not email:
            errors.append('Email khong duoc de trong.')
        if not full_name:
            errors.append('Ho ten khong duoc de trong.')
        if not student_code:
            errors.append('Ma sinh vien khong duoc de trong.')
        if not faculty:
            errors.append('Khoa khong duoc de trong.')
        if len(password) < 6:
            errors.append('Mat khau phai it nhat 6 ky tu.')
        if password != password2:
            errors.append('Mat khau xac nhan khong khop.')

        if User.objects.filter(username__iexact=username).exists():
            errors.append('Username da ton tai.')
        if User.objects.filter(email__iexact=email).exists():
            errors.append('Email da duoc su dung.')
        if StudentProfile.objects.filter(student_code__iexact=student_code).exists():
            errors.append('Ma sinh vien da ton tai.')

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
                faculty=faculty,
                class_name=class_name,
            )
            messages.success(request, 'Dang ky thanh cong! Hay dang nhap.')
            return redirect('users:login')
        except IntegrityError:
            messages.error(request, 'Loi tao tai khoan. Vui long thu lai.')

    return render(request, 'users/register.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'Da dang xuat thanh cong.')
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
        messages.success(request, 'Cap nhat thong tin thanh cong!')
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
            messages.error(request, 'Mat khau hien tai khong dung.')
        elif len(new_password) < 6:
            messages.error(request, 'Mat khau moi phai it nhat 6 ky tu.')
        elif new_password != confirm_password:
            messages.error(request, 'Mat khau xac nhan khong khop.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Doi mat khau thanh cong!')
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
        messages.error(request, 'Ban khong the khoa chinh tai khoan cua minh.')
        return redirect('users:management')

    if request.method == 'POST':
        if target_user.status == 'ACTIVE':
            target_user.status = 'LOCKED'
            target_user.is_active = False
            msg = 'Da khoa tai khoan.'
        else:
            target_user.status = 'ACTIVE'
            target_user.is_active = True
            msg = 'Da mo khoa tai khoan.'
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
            messages.success(request, 'Da doi quyen thanh cong.')
        else:
            messages.error(request, 'Role khong hop le.')

    return redirect('users:management')
