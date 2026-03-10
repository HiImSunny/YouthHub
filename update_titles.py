import os
import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
base_dir = r'd:\Code Project\Website Coding\Code - Đồ Án Cơ Sở 2\youth-hub\templates'

# Pattern to find h1 with big text and the following p
# Group 1: space/indentation before h1
# Group 2: <h1 ...> to </h1>
# Group 3: spaces between h1 and p
# Group 4: <p ...> to </p>
regex = re.compile(r'(<h1[^>]*>)(.*?)(</h1>)(\s*)(<p[^>]*>)(.*?)(</p>)', re.DOTALL)

emojis = ['⚡', '📊', '👥', '⏳', '📅', '✏️', '🏛', '🔍', '📸', '💎', '🎓', '✦', '📄', '💰', '➕', '🗑️', '📥', '★']

p_class_target = 'text-sm font-bold uppercase bg-primary text-white inline-block px-4 py-1 border-3 border-black shadow-brutal'

changed_files = []

for filepath in glob.glob(base_dir + '/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    def replacer(match):
        h1_open = match.group(1)
        h1_content = match.group(2)
        h1_close = match.group(3)
        between = match.group(4)
        p_open = match.group(5)
        p_content = match.group(6)
        p_close = match.group(7)
        
        # We only want to process headers that have the specific visual styling
        if 'font-black' not in h1_open and 'text-5xl' not in h1_open and 'text-4xl' not in h1_open:
            return match.group(0)

        # Do not modify if it looks like a user profile or other specialized p class that shouldn't be boxed
        if '{{ target_user.username }}' in p_content:
            new_h1_content = h1_content
            for e in emojis:
                new_h1_content = new_h1_content.replace(e, '').strip()
            return h1_open + new_h1_content + h1_close + between + p_open + p_content + p_close
            
        new_h1_content = h1_content
        for e in emojis:
            new_h1_content = new_h1_content.replace(e, '').strip()
            
        new_p_open = f'<p class="{p_class_target}">'
        
        # Remove empty line/padding in p_content if making it inline boxed
        p_content_clean = p_content.strip()

        return f'{h1_open}{new_h1_content}{h1_close}{between}{new_p_open}\n            {p_content_clean}\n        {p_close}'

    new_content, count = regex.subn(replacer, content)
    
    if count > 0 and new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        changed_files.append(filepath)

print('Updated files:')
for f in changed_files:
    print(os.path.relpath(f, base_dir))
