#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeDiff - 对比两个 Python 文件的 AST 结构差异。
输出人类可读的结构变更报告（函数/类/导入的增删改）。
运行: python codediff.py old.py new.py
"""
import ast
import os
import sys


def parse_file(path):
    """解析一个 Python 文件为 AST。文件不存在抛 FileNotFoundError，语法错误返回 None。"""
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    return ast.parse(source, filename=path)


def collect_nodes(tree):
    """遍历 AST，提取函数、类、import 节点。
    返回 dict: {qualified_name: info}
    info 中包含 'type', 'name', 'param_count'(函数), 'methods'(类), 'param_list'(函数)
    """
    nodes = {}
    if tree is None:
        return nodes

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.scope_stack = []

        @property
        def scope(self):
            return '.'.join(self.scope_stack)

        def _add(self, key, info):
            nodes[key] = info

        def _visit_func(self, node, is_async=False):
            qualified = (self.scope + '.' if self.scope else '') + node.name
            params = [a.arg for a in node.args.args]
            defaults_count = len(node.args.defaults)
            self._add(qualified, {
                'type': 'async_function' if is_async else 'function',
                'name': node.name,
                'param_list': params,
                'param_count': len(params),
                'defaults': defaults_count,
                'decorators': len(node.decorator_list),
            })
            self.scope_stack.append(node.name)
            for stmt in node.body:
                self.visit(stmt)
            self.scope_stack.pop()

        def visit_FunctionDef(self, node):
            self._visit_func(node, is_async=False)

        def visit_AsyncFunctionDef(self, node):
            self._visit_func(node, is_async=True)

        def visit_ClassDef(self, node):
            qualified = (self.scope + '.' if self.scope else '') + node.name
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
            self._add(qualified, {
                'type': 'class',
                'name': node.name,
                'methods': methods,
                'method_count': len(methods),
                'bases': [ast.unparse(b) if hasattr(ast, 'unparse') else '' for b in node.bases],
            })
            self.scope_stack.append(node.name)
            for stmt in node.body:
                self.visit(stmt)
            self.scope_stack.pop()

        def visit_Import(self, node):
            for alias in node.names:
                shown = alias.asname or alias.name
                key = f"<import> {shown}"
                self._add(key, {
                    'type': 'import',
                    'name': shown,
                    'module': alias.name,
                })

        def visit_ImportFrom(self, node):
            module = node.module or ''
            for alias in node.names:
                shown = alias.asname or alias.name
                key = f"<import> {module}.{shown}"
                self._add(key, {
                    'type': 'import',
                    'name': f"{module}.{shown}" if module else shown,
                    'module': f"{module}.{alias.name}" if module else alias.name,
                })

    v = Visitor()
    v.visit(tree)
    return nodes


def compare_nodes(old_nodes, new_nodes):
    """对比两个节点字典，返回变更列表（字符串）。"""
    changes = []
    old_keys = set(old_nodes.keys())
    new_keys = set(new_nodes.keys())

    # 新增
    for key in sorted(new_keys - old_keys):
        n = new_nodes[key]
        kind = n['type']
        if kind in ('function', 'async_function'):
            changes.append(f"+ 函数名: {n['name']} (参数{n['param_count']}个)")
        elif kind == 'class':
            changes.append(f"+ 类名: {n['name']} (方法{n['method_count']}个)")
        else:
            changes.append(f"+ 导入: {n['name']}")

    # 删除
    for key in sorted(old_keys - new_keys):
        n = old_nodes[key]
        kind = n['type']
        if kind in ('function', 'async_function'):
            changes.append(f"- 函数名: {n['name']} (参数{n['param_count']}个)")
        elif kind == 'class':
            changes.append(f"- 类名: {n['name']} (方法{n['method_count']}个)")
        else:
            changes.append(f"- 导入: {n['name']}")

    # 修改
    for key in sorted(old_keys & new_keys):
        o = old_nodes[key]
        n = new_nodes[key]
        if o == n:
            continue
        kind = n['type']
        if kind in ('function', 'async_function') and o['type'] in ('function', 'async_function'):
            oc, nc = o['param_count'], n['param_count']
            changes.append(f"~ 函数名: {n['name']} (参数从{oc}个变为{nc}个)")
        elif kind == 'class' and o['type'] == 'class':
            om = set(o.get('methods', []))
            nm = set(n.get('methods', []))
            added = sorted(nm - om)
            removed = sorted(om - nm)
            parts = []
            if added:
                parts.append("新增方法 " + ','.join(added))
            if removed:
                parts.append("删除方法 " + ','.join(removed))
            if not parts:
                parts.append("结构调整")
            changes.append(f"~ 类名: {n['name']} ({'; '.join(parts)})")
        else:
            changes.append(f"~ {n['name']} (类型或内容变更)")

    return changes


def diff_files(old_path, new_path):
    """对比两个文件，返回 (changes_list, error_str or None)。"""
    if not os.path.isfile(old_path):
        return None, f"File not found: {old_path}"
    if not os.path.isfile(new_path):
        return None, f"File not found: {new_path}"

    old_ast = None
    new_ast = None
    old_err = None
    new_err = None
    try:
        old_ast = parse_file(old_path)
    except SyntaxError as e:
        old_err = f"{old_path}:{e.lineno}: 语法错误 {e.msg}"
    except FileNotFoundError:
        return None, f"File not found: {old_path}"

    try:
        new_ast = parse_file(new_path)
    except SyntaxError as e:
        new_err = f"{new_path}:{e.lineno}: 语法错误 {e.msg}"
    except FileNotFoundError:
        return None, f"File not found: {new_path}"

    warnings = []
    if old_err:
        warnings.append(f"[警告] {old_err}")
    if new_err:
        warnings.append(f"[警告] {new_err}")

    if old_ast is None and new_ast is None:
        return [], "两个文件均无法解析" + ('; '.join(warnings) if warnings else '')

    old_nodes = collect_nodes(old_ast) if old_ast is not None else {}
    new_nodes = collect_nodes(new_ast) if new_ast is not None else {}
    changes = compare_nodes(old_nodes, new_nodes)
    return changes, ('; '.join(warnings) if warnings else None)


def format_report(old_path, new_path, changes):
    """生成结构化报告文本。"""
    lines = []
    lines.append("=" * 60)
    lines.append("CodeDiff 结构差异报告")
    lines.append("=" * 60)
    lines.append(f"旧文件: {old_path}")
    lines.append(f"新文件: {new_path}")
    lines.append(f"变更数: {len(changes)}")
    lines.append("-" * 60)
    if not changes:
        lines.append("(无结构差异)")
    else:
        for c in changes:
            lines.append(c)
    lines.append("=" * 60)
    return "\n".join(lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) != 3:
        prog = argv[0] if argv else 'codediff.py'
        print(f"用法: python {prog} old_file.py new_file.py", file=sys.stderr)
        return 1

    old_path, new_path = argv[1], argv[2]
    changes, error = diff_files(old_path, new_path)
    if error is not None and changes is None:
        print(error, file=sys.stderr)
        return 1

    report = format_report(old_path, new_path, changes or [])
    if error:
        print(error, file=sys.stderr)
    print(report)

    try:
        with open('diff_report.txt', 'w', encoding='utf-8') as f:
            f.write(report + "\n")
    except OSError as e:
        print(f"[警告] 写入 diff_report.txt 失败: {e}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())