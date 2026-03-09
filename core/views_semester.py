
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Semester, Organization
from .permissions import get_point_category_orgs, group_orgs_by_root

def can_manage_semester(user, semester):
    if user.role == 'ADMIN': return True
    if user.role == 'STUDENT': return False
    return get_point_category_orgs(user).filter(pk=semester.organization_id).exists()

@login_required
def semester_list(request):
    if request.user.role == 'STUDENT': return redirect('students:portal')
    
    orgs = get_point_category_orgs(request.user)
    semesters = Semester.objects.filter(organization__in=orgs).select_related('organization')
    
    # Dropdown data
    years = Semester.objects.filter(organization__in=orgs).values_list('academic_year', flat=True).distinct().order_by('-academic_year')
    organizations = Organization.objects.filter(id__in=orgs.values_list('id', flat=True)).order_by('name')
    
    q = request.GET.get('q')
    org_id = request.GET.get('org')
    year = request.GET.get('year')
    status = request.GET.get('status')
    
    if q:
        semesters = semesters.filter(name__icontains=q)
    if org_id:
        semesters = semesters.filter(organization_id=org_id)
    if year:
        semesters = semesters.filter(academic_year=year)
        
    if status == 'ONGOING':
        semesters = semesters.filter(is_current=True, end_date__gte=timezone.localdate())
    elif status == 'CLOSED':
        semesters = semesters.filter(Q(end_date__lt=timezone.localdate()) | Q(is_current=False, start_date__lte=timezone.localdate()))
    elif status == 'UPCOMING':
        semesters = semesters.filter(is_current=False, start_date__gt=timezone.localdate())
        
    semesters = semesters.order_by('organization__name', '-start_date')
    context = {
        'semesters': semesters,
        'years': years,
        'organizations': organizations,
        'org_groups': group_orgs_by_root(organizations),
        'current_q': q or '',
        'current_org': org_id or '',
        'current_year': year or '',
        'current_status': status or ''
    }
    return render(request, 'core/semester_list.html', context)

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
        
    return render(request, 'core/semester_form.html', {
        'orgs': orgs,
        'org_groups': group_orgs_by_root(orgs)
    })

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
        
    return render(request, 'core/semester_form.html', {
        'semester': sem, 
        'orgs': orgs, 
        'org_groups': group_orgs_by_root(orgs),
        'is_edit': True
    })

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
