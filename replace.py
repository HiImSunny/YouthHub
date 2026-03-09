import os
import glob

def find_and_replace():
    search_str = 'point_categories:point_category_'
    replace_str = 'point_categories:point_category_'
    
    # paths to look at
    python_files = glob.glob('**/*.py', recursive=True)
    html_files = glob.glob('**/*.html', recursive=True)
    
    all_files = python_files + html_files
    
    for filename in all_files:
        if 'venv' in filename or '.git' in filename or 'migrations' in filename:
            continue
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if search_str in content:
                content = content.replace(search_str, replace_str)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Replaced in {filename}")
        except Exception as e:
            print(f"Skipping {filename} due to {e}")

if __name__ == "__main__":
    find_and_replace()
