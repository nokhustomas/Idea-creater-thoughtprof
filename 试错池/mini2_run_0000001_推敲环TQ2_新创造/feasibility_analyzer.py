#!/usr/bin/env python3
"""
Local Creative Feasibility Analyzer V2
输入创意描述，检索本地技术语料库计算三维可行性评分，输出JSON报告
"""

import json
import re
import sys
import argparse
from pathlib import Path

# Try to import jieba, use simple split if not available
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("Warning: jieba not available, using simple Chinese tokenization", file=sys.stderr)


def simple_chinese_tokenize(text):
    """Simple Chinese tokenization without jieba"""
    # Extract Chinese characters and common technical terms
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    words = []
    
    # Find Chinese words
    chinese_words = chinese_pattern.findall(text)
    for word in chinese_words:
        # Split by common delimiters and generate 2-4 character combinations
        if len(word) >= 2:
            words.append(word)
            for i in range(len(word) - 1):
                for length in [2, 3, 4]:
                    if i + length <= len(word):
                        words.append(word[i:i+length])
    
    # Extract English words
    english_pattern = re.compile(r'[a-zA-Z0-9]+')
    words.extend(english_pattern.findall(text))
    
    return list(set(words))


def tokenize(text):
    """Tokenize input text"""
    if JIEBA_AVAILABLE:
        return list(jieba.cut(text))
    else:
        return simple_chinese_tokenize(text)


def load_corpus(corpus_path='tech_corpus.json'):
    """Load technology corpus from JSON file"""
    try:
        with open(corpus_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter out entries with empty descriptions
        filtered = [item for item in data if item.get('description') and len(item.get('description', '').strip()) > 0]
        
        if len(filtered) < 150:
            print(f"Warning: Corpus has only {len(filtered)} entries with descriptions (need >=150)", file=sys.stderr)
        
        return filtered
    except FileNotFoundError:
        print(f"Warning: Corpus file {corpus_path} not found, using default scoring", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in {corpus_path}, using default scoring", file=sys.stderr)
        return []


def calculate_clarity_score(tokens, corpus):
    """
    Calculate clarity score based on how well the idea is understood
    Higher score = more specific, clear concept
    """
    if not tokens:
        return 0.3
    
    # Technical terms that indicate clarity
    technical_terms = ['api', 'web', 'app', 'database', 'server', 'cloud', 'ai', 'ml',
                       'python', 'javascript', 'java', 'api', 'http', 'json', 'xml',
                       '移动', '网页', '应用', '数据库', '服务器', '云', '人工智能',
                       '编辑器', 'markdown', '语音', '控制', '自动化', '工具']
    
    technical_count = sum(1 for token in tokens if any(term in token.lower() for term in technical_terms))
    
    # Length penalty - too short or too long reduces clarity
    length_penalty = 0
    if len(tokens) < 3:
        length_penalty = 0.2
    elif len(tokens) > 30:
        length_penalty = 0.1
    
    base_score = min(1.0, 0.4 + technical_count * 0.1 + len([t for t in tokens if len(t) >= 2]) * 0.02)
    
    return max(0.1, base_score - length_penalty)


def calculate_feasibility_score(tokens, corpus):
    """
    Calculate feasibility score based on corpus similarity
    Higher score = more related projects exist in corpus (easier to build)
    """
    if not corpus:
        return 0.5
    
    if not tokens:
        return 0.3
    
    max_similarity = 0
    
    for item in corpus:
        item_text = f"{item.get('name', '')} {item.get('description', '')} {' '.join(item.get('tags', []))}".lower()
        
        match_count = sum(1 for token in tokens if token.lower() in item_text)
        
        if len(tokens) > 0:
            similarity = match_count / len(tokens)
            max_similarity = max(max_similarity, similarity)
    
    # Scale to 0.1-0.9 range
    return 0.1 + max_similarity * 0.8


def calculate_uniqueness_score(tokens, corpus):
    """
    Calculate uniqueness score based on how novel the idea is
    Higher score = more unique, less competition
    """
    if not corpus:
        return 0.5
    
    if not tokens:
        return 0.3
    
    # Count how many corpus items match the idea
    matching_items = 0
    
    for item in corpus:
        item_text = f"{item.get('name', '')} {item.get('description', '')} {' '.join(item.get('tags', []))}".lower()
        
        match_count = sum(1 for token in tokens if token.lower() in item_text)
        
        if match_count >= len(tokens) * 0.5:
            matching_items += 1
    
    # Uniqueness = 1 - (matching_items / total_items), scaled
    if len(corpus) == 0:
        return 0.5
    
    competition_ratio = matching_items / len(corpus)
    
    # High competition = low uniqueness
    return max(0.1, min(1.0, 1.0 - competition_ratio * 2))


def analyze_idea(idea, corpus_path='tech_corpus.json'):
    """
    Analyze a creative idea and return feasibility report
    """
    corpus = load_corpus(corpus_path)
    
    # Tokenize the idea
    tokens = tokenize(idea)
    
    # Calculate three-dimensional scores
    clarity = calculate_clarity_score(tokens, corpus)
    feasibility = calculate_feasibility_score(tokens, corpus)
    uniqueness = calculate_uniqueness_score(tokens, corpus)
    
    # Overall feasibility score (weighted average)
    overall_score = clarity * 0.3 + feasibility * 0.4 + uniqueness * 0.3
    
    # Find related projects from corpus
    related_projects = []
    if corpus:
        for item in corpus:
            item_text = f"{item.get('name', '')} {item.get('description', '')}".lower()
            match_count = sum(1 for token in tokens if token.lower() in item_text)
            if match_count > 0:
                related_projects.append({
                    'name': item.get('name'),
                    'description': item.get('description', '')[:100],
                    'relevance': match_count
                })
        
        related_projects.sort(key=lambda x: x['relevance'], reverse=True)
        related_projects = related_projects[:5]
    
    # Build report
    report = {
        'idea': idea,
        'tokens': tokens,
        'scores': {
            'clarity': round(clarity, 3),
            'feasibility': round(feasibility, 3),
            'uniqueness': round(uniqueness, 3)
        },
        'feasibility_score': round(overall_score, 3),
        'related_projects': related_projects,
        'corpus_size': len(corpus),
        'recommendation': generate_recommendation(overall_score, clarity, feasibility, uniqueness)
    }
    
    return report


def generate_recommendation(overall, clarity, feasibility, uniqueness):
    """Generate recommendation based on scores"""
    if overall >= 0.7:
        if uniqueness >= 0.6:
            return "Excellent idea! High potential with good differentiation. Recommend proceeding with development."
        else:
            return "Good idea with proven demand. Focus on differentiation from existing solutions."
    elif overall >= 0.5:
        if clarity < 0.4:
            return "Idea has potential but needs clarification. Consider specifying target users and use cases."
        elif uniqueness < 0.3:
            return "Competitive market exists. Need stronger differentiation strategy."
        else:
            return "Moderate potential. Conduct user research before full development."
    else:
        if feasibility < 0.3:
            return "Technical feasibility concerns. Consider simpler implementation approaches."
        elif uniqueness < 0.2:
            return "Highly saturated market. Pivot to more differentiated concept."
        else:
            return "Idea needs more work. Consider combining with proven demand patterns."


def main():
    parser = argparse.ArgumentParser(description='Local Creative Feasibility Analyzer V2')
    parser.add_argument('--idea', type=str, required=True, help='Creative idea description')
    parser.add_argument('--corpus', type=str, default='tech_corpus.json', help='Path to corpus file')
    parser.add_argument('--output', type=str, default=None, help='Output JSON file path')
    
    args = parser.parse_args()
    
    if not args.idea or len(args.idea.strip()) == 0:
        print("Error: Idea cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    try:
        report = analyze_idea(args.idea, args.corpus)
        
        output = json.dumps(report, ensure_ascii=False, indent=2)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Report saved to {args.output}")
        else:
            print(output)
        
        sys.exit(0)
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
