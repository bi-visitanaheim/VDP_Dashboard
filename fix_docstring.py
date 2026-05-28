# =============================================================================
# Copyright (c) 2026 Wilton John Picou, GloCon Solutions LLC.
# All rights reserved. Proprietary and confidential.
#
# Authored, developed, and owned solely by Wilton John Picou of GloCon
# Solutions LLC. Licensed exclusively and perpetually to Visit Dana Point as
# the sole authorized user. No part of this software may be copied, reproduced,
# modified, published, distributed, sublicensed, or used by any other person or
# entity without the prior express written consent of the copyright holder.
# Unauthorized use, reproduction, or distribution is strictly prohibited and
# constitutes a violation of U.S. and international copyright law
# (17 U.S.C. Sec. 101 et seq.).
#
# Attribution to "Wilton John Picou, GloCon Solutions LLC" must be retained.
# See the LICENSE file at the repository root for the full, binding terms.
# =============================================================================

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
