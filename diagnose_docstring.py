import re

with open('dashboard/app.py', 'r') as f:
    lines = f.readlines()

# Search for ALL st.write/markdown/text calls
print("=== All st.write/markdown/text calls ===\n")
found = False
for i, line in enumerate(lines, 1):
    if re.search(r'st\.(write|markdown|text)\s*\(', line):
        found = True
        print(f"Line {i}: {line.rstrip()}")

if not found:
    print("No st.write/markdown/text found")

# Search for the docstring text itself
print("\n\n=== Searching for docstring text ===\n")
docstring_parts = ['Pivot fact_str_metrics', 'Return a persistent SQLite', 'Creates the database file']
for part in docstring_parts:
    for i, line in enumerate(lines, 1):
        if part in line and not line.strip().startswith('"""'):
            print(f"Line {i}: {line.rstrip()}")
