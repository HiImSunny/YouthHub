
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Semester, Organization
from .permissions import get_point_category_orgs

def can_manage_semester(user, semester):
    if user.role == 'ADMIN': return True
    if user.role == 'STUDENT': return False
    return get_point_category_orgs(user).filter(pk=semester.organization_id).exists()

@login_required
def semester_list(request):
    if request.user.role == 'STUDENT': return redirect('students:portal')
    
    orgs = get_point_category_orgs(request.user)
    semesters = Semester.objects.filter(organization__in=orgs).select_related('organization').order_by('-start_date')
    
    return render(request, 'core/semester_list.html', {'semesters': semesters})

@login_required
def semester_create(request):
    if request.user.role == 'STUDENT': return redirect('students:portal')
    
    orgs = get_point_category_orgs(request.user)
    if not orgs.exists():
        messages.error(request, 'Bạn không quản lý tổ chức nào để thêm học kỳ.')
        return redirect('core:semesters')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        academic_year = request.POST.get('academic_year')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_current = request.POST.get('is_current') == 'on'
        org_id = request.POST.get('organization')
        
        org = get_object_or_404(Organization, pk=org_id)
        if not orgs.filter(pk=org.pk).exists():
            messages.error(request, 'Lỗi quyền hạn!')
            return redirect('core:semesters')
            
        if is_current:
            Semester.objects.filter(organization=org).update(is_current=False)
            
        Semester.objects.create(
            name=name, academic_year=academic_year,
            start_date=start_date, end_date=end_date,
            is_current=is_current, organization=org
        )
        messages.success(request, 'Tạo học kỳ thành công.')
        return redirect('core:semesters')
        
    return render(request, 'core/semester_form.html', {'orgs': orgs})

@login_required
def semester_edit(request, pk):
    sem = get_object_or_404(Semester, pk=pk)
    if not can_manage_semester(request.user, sem):
        messages.error(request, 'Lỗi quyền hạn!')
        return redirect('core:semesters')
        
    orgs = get_point_category_orgs(request.user)
    if request.method == 'POST':
        sem.name = request.POST.get('name')
        sem.academic_year = request.POST.get('academic_year')
        sem.start_date = request.POST.get('start_date')
        sem.end_date = request.POST.get('end_date')
        is_current = request.POST.get('is_current') == 'on'
        
        org_id = request.POST.get('organization')
        org = get_object_or_404(Organization, pk=org_id)
        sem.organization = org
        
        if is_current and not sem.is_current:
            Semester.objects.filter(organization=org).update(is_current=False)
            
        sem.is_current = is_current
        sem.save()
        messages.success(request, 'Cập nhật học kỳ thành công.')
        return redirect('core:semesters')
        
    return render(request, 'core/semester_form.html', {'semester': sem, 'orgs': orgs, 'is_edit': True})

@login_required
def semester_delete(request, pk):
    sem = get_object_or_404(Semester, pk=pk)
    if not can_manage_semester(request.user, sem):
        messages.error(request, 'Lỗi quyền hạn!')
        return redirect('core:semesters')
        
    if request.method == 'POST':
        sem.delete()
        messages.success(request, 'Đã xóa học kỳ.')
        return redirect('core:semesters')
    return redirect('core:semesters')
