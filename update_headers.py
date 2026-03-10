import os
import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
base_dir = r"d:\Code Project\Website Coding\Code - Đồ Án Cơ Sở 2\youth-hub\templates"

emojis = ['⚡', '📊', '👥', '⏳', '📅', '✏️', '🏛', '🔍', '📸', '💎', '🎓', '✦', '📄', '💰', '➕', '🗑️', '📥', '★', '👤', '🔒', '⚠', '➕']

changed_files = set()

# Regex to find {% block breadcrumb %} ... {% endblock %}
breadcrumb_re = re.compile(r'({%\s*block\s+breadcrumb\s*%})(.*?)({%\s*endblock\s*%})', re.DOTALL)
# Regex to find material symbols span
material_re = re.compile(r'<span class="material-symbols-outlined[^>]*>.*?</span>\s*', re.DOTALL)

def remove_icons(content):
    changed = False
    
    def repl_breadcrumb(match):
        nonlocal changed
        inner = match.group(2)
        old_inner = inner
        # remove emojis
        for e in emojis:
            inner = inner.replace(e, '')
        # remove material symbols
        inner = material_re.sub('', inner)
        
        # trim any leading spaces inside the span tag that might have been left over
        # e.g., <span class="...">   Tổ chức</span> -> <span class="...">Tổ chức</span>
        inner = re.sub(r'(<span[^>]*>)\s+', r'\1', inner)
        
        if inner != old_inner:
            changed = True
            
        return f"{match.group(1)}{inner}{match.group(3)}"

    new_content = breadcrumb_re.sub(repl_breadcrumb, content)
    return new_content, changed

h1_re = re.compile(r'(<h1[^>]*>.*?</h1>)', re.DOTALL)

for filepath in glob.glob(base_dir + '/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()

    new_content, breadcrumb_changed = remove_icons(original_content)

    parts = []
    last_end = 0
    h1_changed = False
    
    for match in h1_re.finditer(new_content):
        # We only care about main h1 with text-4xl or larger
        h1_str = match.group(1)
        if 'text-4xl' not in h1_str and 'text-5xl' not in h1_str and 'text-6xl' not in h1_str and 'text-7xl' not in h1_str:
            parts.append(new_content[last_end:match.end()])
            last_end = match.end()
            continue

        parts.append(new_content[last_end:match.end()])
        rest_of_file = new_content[match.end():]
        
        spaces_match = re.match(r'^(\s*)', rest_of_file)
        spaces = spaces_match.group(1) if spaces_match else ''
        
        # Check if following content starts with an if statement or directly the box
        # Sometimes there's {% if profile %} then the box.
        rest_stripped = rest_of_file.lstrip()
        
        if not (rest_stripped.startswith('<p class="text-sm font-bold uppercase bg-primary') or 
                rest_stripped.startswith('{% if') and '<p class="text-sm font-bold uppercase bg-primary' in rest_stripped[:300]):
            
            h1_text_match = re.search(r'>([^<]+)<', h1_str)
            h1_text = h1_text_match.group(1).strip() if h1_text_match else "YOUTHHUB"
            
            # Map header to subtitle
            h1_text_upper = h1_text.upper()
            if 'PROFILE' in h1_text_upper:
                subtitle_text = "THÔNG TIN CÁ NHÂN"
            elif 'MẬT KHẨU' in h1_text_upper:
                subtitle_text = "BẢO MẬT TÀI KHOẢN"
            elif 'XÓA' in h1_text_upper or 'DELETE' in h1_text_upper:
                subtitle_text = "NGUY HIỂM · POTENTIALLY DESTRUCTIVE"
            elif 'SỬA' in h1_text_upper or 'EDIT' in h1_text_upper:
                subtitle_text = "CHỈNH SỬA THÔNG TIN"
            elif 'TẠO' in h1_text_upper or 'CREATE' in h1_text_upper:
                subtitle_text = "THÊM MỚI DỮ LIỆU"
            elif 'QUẢN LÝ ĐIỂM DANH' in h1_text_upper:
                subtitle_text = "ATTENDANCE SESSIONS"
            elif 'PHIÊN ĐIỂM DANH' in h1_text_upper:
                subtitle_text = "SESSIONS MANAGEMENT"
            elif 'THÀNH VIÊN' in h1_text_upper:
                subtitle_text = "STAFF MANAGEMENT"
            elif 'NGÂN SÁCH' in h1_text_upper:
                subtitle_text = "BUDGET OVERVIEW"
            elif 'VĂN BẢN AI' in h1_text_upper or 'TRỢ LÝ AI' in h1_text_upper:
                subtitle_text = "AI ASSISTANT"
            elif 'YOUTH HUB' in h1_text_upper: 
                subtitle_text = "SYSTEM LOGIN"
            else:
                subtitle_text = h1_text_upper + " SYSTEM"
            
            new_box = f'\n        <p class="text-sm font-bold uppercase bg-primary text-white inline-block px-4 py-1 border-3 border-black shadow-brutal">\n            {subtitle_text}\n        </p>'
            parts.append(new_box)
            h1_changed = True
            
        last_end = match.end()
        
    parts.append(new_content[last_end:])
    final_content = "".join(parts)
    
    if breadcrumb_changed or h1_changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        changed_files.add(filepath)

print('Updated files:')
for f in changed_files:
    print(os.path.relpath(f, base_dir))
