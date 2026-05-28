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
