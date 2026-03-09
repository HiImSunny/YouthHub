import os
import re

VIEWS_CODE = """
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
"""

LIST_TEMPLATE = """{% extends 'base.html' %}
{% block title %}HỌC KỲ — YOUTHHUB{% endblock %}

{% block header_actions %}
{% if user.role != 'STUDENT' %}
<a href="{% url 'core:semester_create' %}" class="bg-primary text-white border-3 border-black px-4 py-2 font-black uppercase shadow-brutal-sm brutal-btn flex items-center gap-2 text-sm">
    <span class="material-symbols-outlined text-lg">add</span> TẠO HỌC KỲ
</a>
{% endif %}
{% endblock %}

{% block content %}
<div class="mb-8">
    <h1 class="text-4xl md:text-5xl font-black uppercase tracking-tighter leading-none mb-2">📅 HỌC KỲ</h1>
    <p class="text-sm font-bold uppercase bg-primary text-white inline-block px-4 py-1 border-3 border-black shadow-brutal">QUẢN LÝ HỌC KỲ, NĂM HỌC</p>
</div>

<div class="bg-white border-3 border-black shadow-brutal-lg">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="border-b-3 border-black bg-slate-100">
                    <th class="p-4 font-black uppercase border-r-2 border-black text-sm w-16 text-center">#</th>
                    <th class="p-4 font-black uppercase border-r-2 border-black text-sm">HỌC KỲ - NĂM HỌC</th>
                    <th class="p-4 font-black uppercase border-r-2 border-black text-sm">TỔ CHỨC</th>
                    <th class="p-4 font-black uppercase border-r-2 border-black text-sm">THỜI GIAN</th>
                    <th class="p-4 font-black uppercase border-r-2 border-black text-sm">TRẠNG THÁI</th>
                    <th class="p-4 font-black uppercase text-sm text-center">THAO TÁC</th>
                </tr>
            </thead>
            <tbody>
                {% for s in semesters %}
                <tr class="border-b-2 border-black hover:bg-primary/5 transition-all">
                    <td class="p-4 border-r-2 border-black font-mono text-center">{{ forloop.counter }}</td>
                    <td class="p-4 border-r-2 border-black font-black uppercase">{{ s.name }} ({{ s.academic_year }})</td>
                    <td class="p-4 border-r-2 border-black">{{ s.organization.name }}</td>
                    <td class="p-4 border-r-2 border-black text-sm font-bold text-slate-600">
                        {{ s.start_date|date:"d/m/Y" }} - {{ s.end_date|date:"d/m/Y" }}
                    </td>
                    <td class="p-4 border-r-2 border-black text-xs font-black uppercase">
                        {% if s.is_current %}
                        <span class="bg-primary/20 text-primary px-2 py-1 border border-primary">ĐANG DIỄN RA</span>
                        {% else %}
                        <span class="bg-slate-200 text-slate-500 px-2 py-1 border border-slate-300">ĐÃ ĐÓNG</span>
                        {% endif %}
                    </td>
                    <td class="p-4 text-center">
                        <div class="flex items-center justify-center gap-2">
                            <a href="{% url 'core:semester_edit' s.pk %}" class="bg-accent-yellow border-2 border-black px-3 py-1 text-xs font-black uppercase brutal-btn">SỬA</a>
                            <form method="post" action="{% url 'core:semester_delete' s.pk %}" class="inline">
                                {% csrf_token %}
                                <button type="submit" onclick="return confirm('Xác nhận xóa học kỳ này?')" class="bg-accent-red text-white border-2 border-black px-3 py-1 text-xs font-black uppercase brutal-btn">XÓA</button>
                            </form>
                        </div>
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="6" class="p-10 text-center text-slate-400 font-bold uppercase">CHƯA CÓ HỌC KỲ NÀO ĐƯỢC TẠO</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

FORM_TEMPLATE = """{% extends 'base.html' %}
{% block title %}{% if is_edit %}SỬA{% else %}TẠO{% endif %} HỌC KỲ — YOUTHHUB{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto">
    <div class="mb-8">
        <h1 class="text-4xl md:text-5xl font-black uppercase tracking-tighter leading-none mb-2">{% if is_edit %}✏️ SỬA HỌC KỲ{% else %}⚡ TẠO HỌC KỲ MỚI{% endif %}</h1>
    </div>

    <form method="post" class="bg-white border-3 border-black shadow-brutal-lg p-6 space-y-6">
        {% csrf_token %}
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-black uppercase mb-2">TÊN HỌC KỲ <span class="text-accent-red">*</span></label>
                <input type="text" name="name" required value="{{ semester.name|default:'' }}" class="w-full border-3 border-black p-3 font-bold uppercase text-sm" placeholder="VD: HKI">
            </div>
            <div>
                <label class="block text-sm font-black uppercase mb-2">NĂM HỌC <span class="text-accent-red">*</span></label>
                <input type="text" name="academic_year" required value="{{ semester.academic_year|default:'' }}" class="w-full border-3 border-black p-3 font-bold uppercase text-sm" placeholder="VD: 2025-2026">
            </div>
        </div>

        <div>
            <label class="block text-sm font-black uppercase mb-2">THUỘC TỔ CHỨC <span class="text-accent-red">*</span></label>
            <select name="organization" required class="w-full border-3 border-black p-3 font-bold uppercase text-sm">
                {% for o in orgs %}
                <option value="{{ o.id }}" {% if semester.organization_id == o.id %}selected{% endif %}>{{ o.name }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-black uppercase mb-2">BẮT ĐẦU TỪ <span class="text-accent-red">*</span></label>
                <input type="date" name="start_date" required value="{{ semester.start_date|date:'Y-m-d'|default:'' }}" class="w-full border-3 border-black p-3 font-bold uppercase text-sm">
            </div>
            <div>
                <label class="block text-sm font-black uppercase mb-2">KẾT THÚC KHI <span class="text-accent-red">*</span></label>
                <input type="date" name="end_date" required value="{{ semester.end_date|date:'Y-m-d'|default:'' }}" class="w-full border-3 border-black p-3 font-bold uppercase text-sm">
            </div>
        </div>

        <div class="flex items-center gap-3 border-t-3 border-black pt-4">
            <input type="checkbox" name="is_current" id="is_current" class="w-5 h-5 border-3 border-black text-primary focus:ring-0" {% if semester.is_current %}checked{% endif %}>
            <label for="is_current" class="font-black uppercase text-sm cursor-pointer select-none">ĐẮC NGÔI (HỌC KỲ HIỆN TẠI)</label>
        </div>

        <div class="flex gap-4 pt-4">
            <button type="submit" class="flex-1 bg-primary text-white border-3 border-black p-3 font-black uppercase brutal-btn">LƯU HỌC KỲ</button>
            <a href="{% url 'core:semesters' %}" class="bg-white border-3 border-black p-3 font-black uppercase brutal-btn px-6">HỦY</a>
        </div>
    </form>
</div>
{% endblock %}
"""

def main():
    with open('core/views_semester.py', 'w', encoding='utf-8') as f:
        f.write(VIEWS_CODE)
        
    with open('templates/core/semester_list.html', 'w', encoding='utf-8') as f:
        f.write(LIST_TEMPLATE)
        
    with open('templates/core/semester_form.html', 'w', encoding='utf-8') as f:
        f.write(FORM_TEMPLATE)
        
    # Inject URLs back to core/urls.py
    with open('core/urls.py', 'r', encoding='utf-8') as f:
        urls_content = f.read()
    
    if 'semester_list' not in urls_content:
        import_stmt = "from .views_semester import semester_list, semester_create, semester_edit, semester_delete\n"
        urls_content = urls_content.replace("from . import views", "from . import views\n" + import_stmt)
        
        path_routing = """    
    path('semesters/', semester_list, name='semesters'),
    path('semesters/create/', semester_create, name='semester_create'),
    path('semesters/<int:pk>/edit/', semester_edit, name='semester_edit'),
    path('semesters/<int:pk>/delete/', semester_delete, name='semester_delete'),
]"""
        urls_content = urls_content.replace("]", path_routing)
        
        with open('core/urls.py', 'w', encoding='utf-8') as f:
            f.write(urls_content)

    # Inject Link in base.html
    base_html = 'templates/base.html'
    with open(base_html, 'r', encoding='utf-8') as f:
        base_content = f.read()
        
    if "{% url 'core:semesters' %}" not in base_content:
        # We will put it after point_category_list
        target = """        <a href="{% url 'point_categories:point_category_list' %}"
          class="flex items-center gap-3 px-4 py-3 font-black uppercase border-3 border-transparent hover:border-black hover:bg-primary/5 transition-all w-full text-left {% if request.resolver_match.view_name == 'point_categories:point_category_list' %}bg-primary/10 border-black text-primary{% endif %}">
          <span class="material-symbols-outlined shrink-0 text-xl">stars</span>
          <span class="truncate">Mục Điểm RL</span>
        </a>"""
        
        replacement = target + """
        <a href="{% url 'core:semesters' %}"
          class="flex items-center gap-3 px-4 py-3 font-black uppercase border-3 border-transparent hover:border-black hover:bg-primary/5 transition-all w-full text-left {% if 'semester' in request.resolver_match.view_name %}bg-primary/10 border-black text-primary{% endif %}">
          <span class="material-symbols-outlined shrink-0 text-xl">calendar_month</span>
          <span class="truncate">Học kỳ</span>
        </a>"""
        
        base_content = base_content.replace(target, replacement)
        with open(base_html, 'w', encoding='utf-8') as f:
            f.write(base_content)

if __name__ == '__main__':
    main()
