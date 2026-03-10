import os
import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
base_dir = r'd:\Code Project\Website Coding\Code - Đồ Án Cơ Sở 2\youth-hub\templates'

regex = re.compile(r'(<h1[^>]*>)(.*?)(</h1>)', re.DOTALL)
emojis = ['⚡', '📊', '👥', '⏳', '📅', '✏️', '🏛', '🔍', '📸', '💎', '🎓', '✦', '📄', '💰', '➕', '🗑️', '📥', '★', '👤', '🔒', '⚠']

changed_files = []

for filepath in glob.glob(base_dir + '/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    def replacer(match):
        h1_open = match.group(1)
        h1_content = match.group(2)
        h1_close = match.group(3)
        
        new_h1_content = h1_content
        for e in emojis:
            new_h1_content = new_h1_content.replace(e, '').strip()
            
        return f'{h1_open}{new_h1_content}{h1_close}'

    new_content, count = regex.subn(replacer, content)
    
    if count > 0 and new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        changed_files.append(filepath)

print('Updated files:')
for f in changed_files:
    print(os.path.relpath(f, base_dir))
