#!/usr/bin/env python3
"""
Snippet Knowledge Graph Builder
Automatically organizes code snippets into a navigable knowledge graph.
"""

import os
import re
import ast
import json
import hashlib
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher
import html

class Snippet:
    def __init__(self, filepath, content, language):
        self.filepath = filepath
        self.content = content
        self.language = language
        self.name = Path(filepath).stem
        self.topics = self._extract_topics()
        self.docstring = self._extract_docstring()
        self.checksum = hashlib.md5(content.encode()).hexdigest()
    
    def _extract_topics(self):
        """Extract topics from code content."""
        topics = set()
        topics.add(self.language.lower())
        if self.language == 'python':
            try:
                tree = ast.parse(self.content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        topics.add(node.name.lower())
                    elif isinstance(node, ast.ClassDef):
                        topics.add(node.name.lower())
            except:
                pass
        keywords = re.findall(r'\b(\w{4,})\b', self.content.lower())
        common = {'function', 'class', 'def', 'return', 'import', 'export', 
                  'const', 'var', 'let', 'if', 'else', 'for', 'while', 'try',
                  'except', 'catch', 'async', 'await', 'from', 'with', 'open'}
        topics.update(w for w in keywords if w not in common)
        return topics
    
    def _extract_docstring(self):
        """Extract first docstring found."""
        if self.language == 'python':
            try:
                tree = ast.parse(self.content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.Module)):
                        if ast.get_docstring(node):
                            return ast.get_docstring(node)
            except:
                pass
        match = re.search(r'"""(.*?)"""', self.content, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"'''(.*?)'''", self.content, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r'//\s*(.*?)$', self.content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        match = re.search(r'#\s*(.*?)$', self.content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "No description available"

def read_snippets(folder):
    """Read all code snippets from folder."""
    snippets = []
    ext_map = {
        '.py': 'python', '.js': 'javascript', '.sh': 'bash', '.bash': 'bash',
        '.ts': 'typescript', '.go': 'go', '.rs': 'rust', '.java': 'java',
        '.c': 'c', '.cpp': 'cpp', '.rb': 'ruby',
    }
    for root, dirs, files in os.walk(folder):
        for f in files:
            ext = Path(f).suffix
            if ext in ext_map:
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as fp:
                        content = fp.read()
                    if content.strip():
                        snippets.append(Snippet(path, content, ext_map[ext]))
                except Exception as e:
                    print(f"Warning: Could not read {path}: {e}")
    return snippets

def build_graph(snippets):
    """Build bidirectional knowledge graph."""
    graph = defaultdict(list)
    topic_map = defaultdict(list)
    for s in snippets:
        for topic in s.topics:
            topic_map[topic].append(s.filepath)
    for topic, paths in topic_map.items():
        if len(paths) > 1:
            for i, p1 in enumerate(paths):
                for p2 in paths[i+1:]:
                    graph[p1].append(p2)
                    graph[p2].append(p1)
    return graph, topic_map

def find_duplicates(snippets, threshold=0.7):
    """Find near-duplicate snippets using fuzzy matching."""
    duplicates = []
    for i, s1 in enumerate(snippets):
        for s2 in snippets[i+1:]:
            ratio = SequenceMatcher(None, s1.content, s2.content).ratio()
            if ratio >= threshold:
                duplicates.append({
                    'snippet1': s1.filepath,
                    'snippet2': s2.filepath,
                    'similarity': round(ratio * 100, 1)
                })
    return duplicates

def generate_markdown_report(snippets, graph, topic_map, duplicates, output_path):
    """Generate markdown knowledge graph report."""
    lines = [
        "# Snippet Knowledge Graph",
        "",
        f"**Total Snippets:** {len(snippets)}",
        f"**Total Topics:** {len(topic_map)}",
        f"**Links Generated:** {sum(len(v) for v in graph.values()) // 2}",
        f"**Duplicates Found:** {len(duplicates)}",
        "",
        "---",
        "",
        "## Snippet Index",
        "",
        "### By File"
    ]
    for s in sorted(snippets, key=lambda x: x.filepath):
        lines.append(f"- **{s.name}** ({s.language}) - {s.filepath}")
        lines.append(f"  - Topics: {', '.join(sorted(s.topics))}")
        lines.append(f"  - {s.docstring[:100]}")
        lines.append("")
    lines.append("### Topic Cloud")
    lines.append("")
    sorted_topics = sorted(topic_map.items(), key=lambda x: len(x[1]), reverse=True)
    for topic, paths in sorted_topics[:20]:
        lines.append(f"- `{topic}` ({len(paths)} snippets)")
    lines.append("")
    lines.append("## Bidirectional Links")
    lines.append("")
    for s in sorted(snippets, key=lambda x: x.filepath):
        links = graph.get(s.filepath, [])
        if links:
            lines.append(f"### {s.name}")
            lines.append(f"Connected to: {', '.join(Path(l).stem for l in links)}")
            lines.append("")
    if duplicates:
        lines.append("## Duplicate Detection")
        lines.append("")
        for dup in duplicates:
            lines.append(f"- **{Path(dup['snippet1']).stem}** <-> **{Path(dup['snippet2']).stem}** ({dup['similarity']}% similar)")
        lines.append("")
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

def generate_html_browser(snippets, graph, topic_map, output_path):
    """Generate interactive HTML knowledge browser."""
    snippet_data = [
        {
            'name': s.name, 'path': s.filepath, 'language': s.language,
            'topics': list(s.topics), 'docstring': s.docstring,
            'content': s.content, 'links': [Path(p).stem for p in graph.get(s.filepath, [])]
        }
        for s in snippets
    ]
    # Build static parts first, then f-string expressions only for variable data
    html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Snippet Knowledge Graph</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat { background: white; padding: 15px 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #333; }
        .topic { display: inline-block; background: #e9ecef; padding: 3px 10px; border-radius: 15px; margin: 3px; font-size: 0.85em; }
        .topic.python { background: #3776ab; color: white; }
        .topic.javascript { background: #f7df1e; color: black; }
        .topic.bash { background: #4eaa25; color: white; }
        .links { margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
        .link-item { color: #007bff; cursor: pointer; margin-right: 10px; }
        .link-item:hover { text-decoration: underline; }
        .content { background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; font-size: 0.9em; overflow-x: auto; }
        .search-box { width: 100%; padding: 15px; font-size: 1.1em; border: 2px solid #ddd; border-radius: 8px; margin-bottom: 20px; }
        .topic-section { background: white; padding: 20px; border-radius: 8px; margin: 15px 0; }
    </style>
</head>
<body>
    <h1>Snippet Knowledge Graph</h1>
    <input type="text" class="search-box" placeholder="Search snippets..." onkeyup="filterSnippets(this.value)">
    <div class="stats">
        <div class="stat"><div class="stat-value">''' + str(len(snippets)) + '''</div><div class="stat-label">Snippets</div></div>
        <div class="stat"><div class="stat-value">''' + str(len(topic_map)) + '''</div><div class="stat-label">Topics</div></div>
        <div class="stat"><div class="stat-value">''' + str(sum(len(v) for v in graph.values()) // 2) + '''</div><div class="stat-label">Connections</div></div>
    </div>
    <div class="topic-section">
        <h2>Topics</h2>
        <div id="topics">''' + ' '.join('<span class="topic ' + html.escape(t) + '">' + html.escape(t) + '</span>' for t in sorted(topic_map.keys())) + '''
        </div>
    </div>
    <h2>All Snippets</h2>
    <div id="snippets">
'''
    for s in snippets:
        # Pre-compute values that will be used in f-string to avoid backslash issues
        data_name = html.escape(s.name.lower())
        data_topics = html.escape(' '.join(s.topics))
        data_content = html.escape(s.content.lower())
        docstring_escaped = html.escape(s.docstring)
        topics_html = ' '.join('<span class="topic ' + html.escape(t) + '">' + html.escape(t) + '</span>' for t in s.topics)
        linked_names = [Path(p).stem for p in graph.get(s.filepath, [])]
        links_html = ' '.join('<span class="link-item" onclick="scrollTo(\'' + html.escape(l) + '\')">' + html.escape(l) + '</span>' for l in linked_names)
        content_escaped = html.escape(s.content)
        
        html_content += f'''
        <div class="card" data-name="{data_name}" data-topics="{data_topics}" data-content="{data_content}">
            <h3>{html.escape(s.name)} <span style="color:#666;font-size:0.7em">({html.escape(s.language)})</span></h3>
            <p><em>{docstring_escaped}</em></p>
            <div>Topics: {topics_html}</div>
            <div class="links">Linked to: {links_html}</div>
            <details>
                <summary>View Code</summary>
                <div class="content">{content_escaped}</div>
            </details>
        </div>
'''
    html_content += '''
    </div>
    <script>
    function filterSnippets(query) {
        query = query.toLowerCase();
        document.querySelectorAll('.card').forEach(card => {
            const match = card.dataset.name.includes(query) || card.dataset.topics.includes(query) || card.dataset.content.includes(query);
            card.style.display = match ? 'block' : 'none';
        });
    }
    function scrollTo(name) {
        const card = document.querySelector('[data-name="' + name + '"]');
        if (card) card.scrollIntoView({behavior: 'smooth'});
    }
    </script>
</body>
</html>'''
    with open(output_path, 'w') as f:
        f.write(html_content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build knowledge graph from code snippets')
    parser.add_argument('input_folder', help='Folder containing code snippets')
    parser.add_argument('-o', '--output', default='knowledge_base', help='Output folder')
    args = parser.parse_args()
    input_path = Path(args.input_folder)
    output_path = Path(args.output)
    output_path.mkdir(exist_ok=True)
    print(f"Reading snippets from: {input_path}")
    snippets = read_snippets(input_path)
    print(f"Found {len(snippets)} snippets")
    print("Building knowledge graph...")
    graph, topic_map = build_graph(snippets)
    print("Finding duplicates...")
    duplicates = find_duplicates(snippets)
    print("Generating reports...")
    generate_markdown_report(snippets, graph, topic_map, duplicates, output_path / 'knowledge_graph.md')
    generate_html_browser(snippets, graph, topic_map, output_path / 'browser.html')
    data = {
        'snippets': [{'name': s.name, 'path': s.filepath, 'language': s.language, 
                      'topics': list(s.topics), 'docstring': s.docstring} for s in snippets],
        'graph': {k: [Path(p).stem for p in v] for k, v in graph.items()},
        'topic_map': {k: [Path(p).stem for p in v] for k, v in topic_map.items()},
        'duplicates': duplicates
    }
    with open(output_path / 'data.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nKnowledge base generated in: {output_path}/")
    print(f"   - knowledge_graph.md (text report)")
    print(f"   - browser.html (interactive browser)")
    print(f"   - data.json (structured data)")

if __name__ == '__main__':
    main()
