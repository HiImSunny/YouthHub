"""
Permission helper functions for role-based access control.
No database schema changes - uses existing User.role, OrganizationMember.is_officer,
and Organization.parent hierarchy.
"""

from core.models import Organization, OrganizationMember


# ─── Staff Org Helpers ────────────────────────────────────────────────────────

def get_officer_orgs(user):
    """
    Return queryset of orgs where this user is an officer (is_officer=True).
    Used for: what orgs can a Staff create activities for.
    """
    if user.role == 'ADMIN':
        return Organization.objects.filter(status=True)
    return Organization.objects.filter(
        members__user=user,
        members__is_officer=True,
        status=True,
    )


def get_child_orgs(org):
    """Return direct children of an org (one level deep)."""
    return org.children.filter(status=True)


def get_all_child_orgs(org):
    """
    Recursively get all descendant orgs of a given org.
    Returns a flat list of Organization objects.
    """
    result = []
    for child in org.children.filter(status=True):
        result.append(child)
        result.extend(get_all_child_orgs(child))
    return result


def get_manageable_orgs(user):
    """
    Orgs the user can manage as a parent Staff:
    - Admin: all orgs
    - Staff: orgs they are officer of + all their child orgs
    """
    if user.role == 'ADMIN':
        return Organization.objects.filter(status=True)

    officer_orgs = get_officer_orgs(user)
    all_ids = set(officer_orgs.values_list('id', flat=True))
    for org in officer_orgs:
        for child in get_all_child_orgs(org):
            all_ids.add(child.id)

    return Organization.objects.filter(id__in=all_ids, status=True)


def get_approvable_orgs(user):
    """
    Orgs whose activities this user can approve:
    - Admin: all orgs
    - Staff: child orgs of the orgs they are officer of (parent approves child)
    """
    if user.role == 'ADMIN':
        return Organization.objects.filter(status=True)

    officer_orgs = get_officer_orgs(user)
    child_ids = set()
    for org in officer_orgs:
        for child in get_all_child_orgs(org):
            child_ids.add(child.id)

    return Organization.objects.filter(id__in=child_ids, status=True)


# ─── Permission Checkers ───────────────────────────────────────────────────────

def can_create_activity(user, org):
    """Check if user can create activity for this org."""
    if user.role == 'ADMIN':
        return True
    if user.role == 'STUDENT':
        return False
    return OrganizationMember.objects.filter(
        user=user, organization=org, is_officer=True
    ).exists()


def can_edit_activity(user, activity):
    """Check if user can edit this activity."""
    if user.role == 'ADMIN':
        return True
    if user.role == 'STUDENT':
        return False
    # Staff can edit activities in their officer orgs
    return OrganizationMember.objects.filter(
        user=user, organization=activity.organization, is_officer=True
    ).exists()


def can_approve_activity(user, activity):
    """
    Check if user can approve this activity.
    Logic (Method 2): Parent Org Staff can approve Child Org activities.
    """
    if user.role == 'ADMIN':
        return True
    if user.role == 'STUDENT':
        return False

    # Get all orgs the user is an officer of
    officer_orgs = get_officer_orgs(user)

    # Check if the activity's org is a child of any org the user officers
    activity_org = activity.organization
    if activity_org is None:
        return False

    # Walk up the parent chain to see if any parent is in officer_orgs
    current = activity_org.parent
    while current is not None:
        if officer_orgs.filter(pk=current.pk).exists():
            return True
        current = current.parent

    return False


def can_manage_org_staff(user, org):
    """
    Check if user can add/remove staff members for this org.
    - Admin: yes for all
    - Staff: orgs they are officer of + all their descendant orgs
    """
    if user.role == 'ADMIN':
        return True
    if user.role == 'STUDENT':
        return False

    return get_manageable_orgs(user).filter(pk=org.pk).exists()


def can_create_org(user):
    """Only admin can create orgs."""
    return user.role == 'ADMIN'


# ─── Point Category Permission Helpers ────────────────────────────────────────

def get_root_org(org):
    """
    Walk up the parent chain to find the root (top-level) organization.
    PointCategory is managed at the root (UNION_SCHOOL) level.
    """
    current = org
    while current.parent is not None:
        current = current.parent
    return current


def group_orgs_by_root(orgs_queryset):
    """
    Given a queryset of organizations, groups them into a dictionary by their root organization name.
    Useful for displaying organized <optgroup> dropdowns.
    """
    # Optimize query by fetching parents if possible to avoid N+1 inside get_root_org
    # Assuming at most 3 levels, so parent__parent is enough.
    from collections import OrderedDict
    orgs = list(orgs_queryset.select_related('parent', 'parent__parent'))
    
    # Sort them first by name to ensure inner elements are sorted
    orgs.sort(key=lambda x: x.name)
    
    grouped = OrderedDict()
    for org in orgs:
        root = get_root_org(org)
        if root.name not in grouped:
            grouped[root.name] = []
        grouped[root.name].append(org)
        
    # Sort groups by root name
    return OrderedDict(sorted(grouped.items()))


def get_point_category_orgs(user):
    """
    Return the set of Organizations whose PointCategories
    this user is allowed to manage.
    - ADMIN: all orgs
    - STAFF: orgs they are officer of + child orgs
    - STUDENT: none
    """
    if user.role == 'STUDENT':
        return Organization.objects.none()
    return get_officer_orgs(user)

def get_usable_point_category_orgs(user):
    """
    Return orgs whose PointCategories the user can USE (for activities).
    Includes manageable orgs + all ancestor orgs.
    """
    if user.role == 'ADMIN':
        return Organization.objects.filter(status=True)
    if user.role == 'STUDENT':
        return Organization.objects.none()
    
    manageable = get_manageable_orgs(user)
    usable_ids = set(manageable.values_list('id', flat=True))
    
    for org in manageable:
        current = org.parent
        while current is not None:
            usable_ids.add(current.id)
            current = current.parent
            
    return Organization.objects.filter(id__in=usable_ids, status=True)

def can_manage_point_category(user, point_category):
    """
    Check if user can create/edit/delete a specific PointCategory.
    """
    if user.role == 'ADMIN':
        return True
    if user.role == 'STUDENT':
        return False
    manageable_orgs = get_point_category_orgs(user)
    return manageable_orgs.filter(pk=point_category.organization_id).exists()

