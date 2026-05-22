import re

with open('dashboard/app.py', 'r') as f:
    content = f.read()

lines = content.split('\n')
fixes = []

for i, line in enumerate(lines, 1):
    if re.search(r'st\.(write|markdown|text)\s*\(\s*(load|get|build|compute)\w+\s*\)(?!\()', line):
        fixes.append((i, line))

if fixes:
    print(f"Found {len(fixes)} problematic lines:")
    for line_num, line_text in fixes:
        print(f"  Line {line_num}: {line_text.strip()}")
    
    for line_num, old_line in fixes:
        new_line = re.sub(
            r'(st\.(write|markdown|text)\s*\(\s*(load|get|build|compute)\w+)\)(?!\()',
            r'\1())',
            old_line
        )
        content = content.replace(old_line, new_line)
    
    with open('dashboard/app.py', 'w') as f:
        f.write(content)
    
    print(f"\n✅ Fixed all {len(fixes)} lines!")
else:
    print("No issues found")
