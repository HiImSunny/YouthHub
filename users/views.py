from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


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
                messages.error(request, 'Tai khoan da bi khoa. Vui long lien he Admin.')
            else:
                login(request, user)
                next_url = request.GET.get('next', 'core:dashboard')
                return redirect(next_url)
        else:
            messages.error(request, 'Sai ten dang nhap hoac mat khau.')

    return render(request, 'users/login.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'Da dang xuat thanh cong.')
    return redirect('users:login')


@login_required
def profile_view(request):
    """View and update user profile."""
    if request.method == 'POST':
        user = request.user
        user.full_name = request.POST.get('full_name', user.full_name)
        user.phone = request.POST.get('phone', user.phone)
        user.save(update_fields=['full_name', 'phone', 'updated_at'])
        messages.success(request, 'Cap nhat thong tin thanh cong!')
        return redirect('users:profile')

    return render(request, 'users/profile.html')
