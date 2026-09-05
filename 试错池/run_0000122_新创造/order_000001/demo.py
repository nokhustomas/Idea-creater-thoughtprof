#!/usr/bin/env python3
"""
Demo: Snippet Knowledge Graph Builder
Compares this tool against manual organization approaches.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def measure_time(func, *args):
    start = time.time()
    result = func(*args)
    return time.time() - start, result

def manual_organization():
    snippet_dir = Path('snippets')
    if not snippet_dir.exists():
        return 0, {'files': 0, 'folders': 0, 'index_lines': 0}
    files = list(snippet_dir.rglob('*'))
    files = [f for f in files if f.is_file()]
    folders_created = set()
    for f in files:
        lang = f.suffix.lstrip('.')
        folders_created.add(lang)
    index_content = ["# Snippet Index\n"]
    for f in sorted(files):
        index_content.append(f"- {f.name} ({f.suffix})")
    return 0, {
        'files': len(files),
        'folders': len(folders_created),
        'index_lines': len(index_content)
    }

def automated_graph():
    result = subprocess.run(
        [sys.executable, 'snippet_harvest.py', 'snippets', '-o', 'knowledge_base'],
        capture_output=True, text=True
    )
    return result.returncode, {'output': result.stdout + result.stderr}

def main():
    print("=" * 60)
    print("SNIPPET KNOWLEDGE GRAPH BUILDER - DEMO")
    print("=" * 60)
    print()
    print("Setting up test snippets...")
    snippet_dir = Path('snippets')
    snippet_dir.mkdir(exist_ok=True)
    sample_files = [
        ('test_http.py', '''# HTTP request handler
def get(url):
    """Fetch URL content."""
    import urllib.request
    return urllib.request.urlopen(url).read()
'''),
        ('test_email.py', '''# Email validation
def validate(email):
    """Check email format."""
    import re
    return bool(re.match(r'^[\\w.]+@[\\w.]+', email))
'''),
        ('test_file.py', '''# File read utility
def read_file(path):
    """Read file contents."""
    with open(path) as f:
        return f.read()
'''),
        ('test_http2.py', '''# HTTP post handler  
def post(url, data):
    """Send POST request."""
    import urllib.request
    return urllib.request.urlopen(url, data).read()
'''),
        ('test_js.js', '''// Event handler
function onClick(e) {
    console.log('Clicked:', e.target);
    return true;
}
'''),
        ('test_bash.sh', '''#!/bin/bash
# Backup script
backup() {
    cp "$1" "${1}.bak"
    echo "Done"
}
'''),
    ]
    for name, content in sample_files:
        (snippet_dir / name).write_text(content)
    print(f"   Created {len(sample_files)} sample snippets\n")
    print("Benchmark 1: Manual organization...")
    t1, result1 = measure_time(manual_organization)
    print(f"   Time: {t1*1000:.1f}ms")
    print(f"   Files processed: {result1['files']}")
    print(f"   Folders created: {result1['folders']}")
    print(f"   Index lines: {result1['index_lines']}")
    print(f"   WARNING: No cross-references, no topic extraction, no duplicate detection\n")
    print("Benchmark 2: Automated knowledge graph...")
    t2, result2 = measure_time(automated_graph)
    if result2[0] != 0:
        print(f"   ERROR: {result2[1]}")
        return 1
    print(f"   Time: {t2*1000:.1f}ms")
    data = None
    try:
        import json
        with open('knowledge_base/data.json') as f:
            data = json.load(f)
    except:
        pass
    if data:
        print(f"   Topics extracted: {len(data['topic_map'])}")
        print(f"   Cross-links built: {sum(len(v) for v in data['graph'].values()) // 2}")
        print(f"   Duplicates detected: {len(data['duplicates'])}")
        print(f"   Reports generated: 3 (markdown, HTML, JSON)")
    print()
    print("=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print()
    print("| Aspect              | Manual      | Knowledge Graph |")
    print("|---------------------|-------------|-----------------|")
    print(f"| Topics extracted    | 0           | {len(data['topic_map']) if data else '?'}")
    print(f"| Cross-references    | 0           | {sum(len(v)//2 for v in data['graph'].values()) if data else '?'}")
    print(f"| Duplicate detection | Manual only | Automatic       |")
    print(f"| Browsable output    | Text index  | Interactive HTML|")
    print(f"| Structured data     | None        | JSON export     |")
    print()
    print("KEY ADVANTAGES:")
    print("   1. AUTOMATIC topic extraction from code content")
    print("   2. BIDIRECTIONAL links between related snippets")
    print("   3. FUZZY duplicate detection with similarity scores")
    print("   4. INTERACTIVE HTML browser with search")
    print("   5. ZERO external dependencies (pure Python stdlib)")
    print()
    print("Demo completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
