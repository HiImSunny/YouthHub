from django.http import JsonResponse
from core.models import Organization
from django.contrib.auth.decorators import login_required

@login_required
def get_organizations_api(request):
    """
    API endpoint to fetch organizations.
    Accepts 'parent' query parameter to filter by parent_id.
    """
    parent_id = request.GET.get('parent')
    
    # We should only return organizations the user is allowed to see
    from core.permissions import get_manageable_orgs
    # In point categories context, the user is likely an admin to be hitting this
    manageable_orgs = get_manageable_orgs(request.user)
    
    orgs = manageable_orgs.filter(status=True)
    
    if parent_id:
        include_descendants = request.GET.get('include_descendants') == 'true'
        from django.db.models import Q
        if include_descendants:
            # We want all orgs that have the parent_id as an ancestor
            # Since our tree is mostly 3 levels (School -> Faculty -> Class)
            # We can do a simpler filter if parent_id is a root school
            orgs = orgs.filter(
                Q(parent_id=parent_id) | 
                Q(parent__parent_id=parent_id) |
                Q(parent__parent__parent_id=parent_id)
            )
        else:
            orgs = orgs.filter(parent_id=parent_id)
            
    # Always order by name
    orgs = orgs.order_by('name')
    
    # Format for JSON
    data = [
        {'id': org.id, 'name': org.name} 
        for org in orgs
    ]
    
    return JsonResponse(data, safe=False)
