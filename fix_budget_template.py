import re

D1 = 'templates/activities/budget_detail.html'
D2 = 'templates/activities/detail.html'

def fix_budget_detail():
    with open(D1, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('budget.items.count', 'budget_items|length')
    content = content.replace('budget.items.all', 'budget_items')
    content = content.replace('item_pk=item.pk', 'item_index=item._index')
    
    with open(D1, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_activity_detail():
    with open(D2, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('budget.items.count', 'budget.items|length')
    content = content.replace('budget.get_status_display', "budget.status|default:'—'")

    with open(D2, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_budget_detail()
    fix_activity_detail()
    print("Fixed templates")
