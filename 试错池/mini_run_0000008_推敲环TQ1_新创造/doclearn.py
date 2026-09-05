#!/usr/bin/env python3
"""
doclearn.py - 纯本地语义检索文档问答工具
使用关键词共现+段落重要性评分，无需外部依赖，可离线运行
"""

import os
import sys
import argparse
import re
import time
from pathlib import Path

# 尝试导入jieba，如果不可用则使用简单的分词
try:
    import jieba
    jieba.setLogLevel(jieba.logging.INFO)
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False


def simple_tokenize(text):
    """简单的中英文分词"""
    # 提取英文单词
    english_words = re.findall(r'[a-zA-Z]+', text)
    # 提取中文词（简单按字符分词）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    # 合并结果
    tokens = english_words
    for chars in chinese_chars:
        tokens.extend(list(chars))
    return [t.lower() for t in tokens if len(t) > 1]


def tokenize(text):
    """分词函数"""
    if HAS_JIEBA:
        return list(jieba.cut(text))
    return simple_tokenize(text)


def extract_keywords(text, topk=10):
    """提取关键词（基于词频）"""
    tokens = tokenize(text)
    # 过滤停用词
    stopwords = {'的', '是', '在', '了', '和', '与', '或', '以及', '等', '包括', '以及', '对', '为', '以', '及', '其', '可', '能', '将', '要', '会', '有', '这', '那', '个', '不', '也', '都', '还', '而', '于', '就', '说', '把', '被', '让', '给', '同', '从', '到', '由', '但', '却', '因为', '所以', '如果', '虽然', '但是', '而且', '并且', '或者', '一个', '我们', '你们', '他们', '她们', '它们', '自己', '什么', '怎么', '如何', '为什么', '哪', '哪个', '哪些', '哪里', '谁', '多少', '几'}
    tokens = [t for t in tokens if t not in stopwords and len(t) > 1]
    
    # 词频统计
    freq = {}
    for token in tokens:
        token_lower = token.lower()
        freq[token_lower] = freq.get(token_lower, 0) + 1
    
    # 返回top-k高频词
    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_freq[:topk]]


def calculate_relevance(paragraph, query_keywords, position, total_paragraphs):
    """
    计算段落相关性分数
    - 关键词共现评分
    - 段落长度权重（适中长度更可能包含有效信息）
    - 段落位置权重（开头结尾通常更重要）
    """
    para_tokens = set(tokenize(paragraph.lower()))
    query_tokens = set(query_keywords)
    
    # 关键词共现评分
    matches = para_tokens & query_tokens
    co_occurrence_score = len(matches) / (len(query_tokens) + 1)
    
    # 关键词在段落中的位置评分
    position_score = 0
    para_lower = paragraph.lower()
    for keyword in query_keywords:
        if keyword.lower() in para_lower:
            # 关键词越靠前，位置分数越高
            idx = para_lower.find(keyword.lower())
            position_score += 1.0 - (idx / max(len(para_lower), 1))
    
    position_score = position_score / (len(query_keywords) + 1)
    
    # 段落长度权重（50-200字符最佳）
    length = len(paragraph)
    if 50 <= length <= 200:
        length_score = 1.0
    elif length < 50:
        length_score = length / 50
    else:
        length_score = max(0.3, 1.0 - (length - 200) / 500)
    
    # 位置权重（开头和结尾更重要）
    position_weight = 1.0
    if position < 2:  # 前两段
        position_weight = 1.2
    elif position > total_paragraphs - 3:  # 最后三段
        position_weight = 1.1
    
    # 综合评分
    final_score = (
        co_occurrence_score * 0.5 +
        position_score * 0.2 +
        length_score * 0.15 +
        position_weight * 0.15
    )
    
    return final_score, len(matches)


def split_paragraphs(content):
    """将文本分割成段落"""
    # 按换行分割
    paragraphs = [p.strip() for p in re.split(r'\n+', content)]
    # 过滤空段落和太短的段落
    paragraphs = [p for p in paragraphs if len(p) >= 20]
    return paragraphs


def read_document(filepath):
    """读取文档内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                return f.read()
        except:
            return None


def search_documents(path, query, topk=3):
    """
    搜索文档，返回最相关的段落
    """
    path = Path(path)
    
    # 收集所有txt和md文件
    files = list(path.glob('*.txt')) + list(path.glob('*.md'))
    
    if not files:
        return []
    
    # 提取查询关键词
    query_keywords = extract_keywords(query, topk=10)
    print(f"[doclearn] 查询关键词: {', '.join(query_keywords)}", file=sys.stderr)
    
    all_paragraphs = []
    
    # 读取所有文档
    for filepath in files:
        content = read_document(filepath)
        if content:
            paragraphs = split_paragraphs(content)
            for i, para in enumerate(paragraphs):
                all_paragraphs.append({
                    'text': para,
                    'file': filepath.name,
                    'position': i
                })
    
    if not all_paragraphs:
        return []
    
    # 计算每个段落的相关性
    total = len(all_paragraphs)
    for para in all_paragraphs:
        score, matches = calculate_relevance(
            para['text'], query_keywords, para['position'], total
        )
        para['score'] = score
        para['matches'] = matches
    
    # 按相关性排序
    all_paragraphs.sort(key=lambda x: (x['score'], x['matches']), reverse=True)
    
    # 返回top-k结果
    return all_paragraphs[:topk]


def main():
    parser = argparse.ArgumentParser(
        description='doclearn - 纯本地语义检索文档问答工具'
    )
    parser.add_argument('--path', required=True, help='文档文件夹路径')
    parser.add_argument('--query', required=True, help='查询内容')
    parser.add_argument('--topk', type=int, default=3, help='返回结果数量')
    
    args = parser.parse_args()
    
    # 检查路径是否存在
    if not os.path.isdir(args.path):
        print(f"错误: 路径不存在: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    start_time = time.time()
    
    # 搜索文档
    results = search_documents(args.path, args.query, args.topk)
    
    elapsed = time.time() - start_time
    
    # 输出结果
    if results:
        print(f"\n找到 {len(results)} 个相关段落:\n")
        for i, result in enumerate(results, 1):
            print(f"{'='*60}")
            print(f"[{i}] 文件: {result['file']}")
            print(f"    匹配关键词数: {result['matches']}")
            print(f"    相关性分数: {result['score']:.4f}")
            print(f"    内容: {result['text'][:200]}...")
            print()
    else:
        print("\n未找到相关段落")
    
    print(f"\n查询耗时: {elapsed*1000:.2f}ms")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
