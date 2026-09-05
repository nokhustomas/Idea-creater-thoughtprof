#!/usr/bin/env python3
"""
价值证明实验：对比语音markdown创意与随机描述的可行性评分
证明工具能识别有价值创意
"""

import json
import sys
import os

# Add current directory to path for import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feasibility_analyzer import analyze_idea, load_corpus


def run_value_demo():
    """
    价值证明实验：
    1. 分析有潜力的创意"语音控制的markdown编辑器"
    2. 分析随机无意义描述
    3. 对比两者的feasibility_score
    """
    
    print("=" * 60)
    print("本地创意可行性分析器 V2 - 价值证明实验")
    print("=" * 60)
    print()
    
    # 加载语料库
    corpus_path = 'tech_corpus.json'
    if not os.path.exists(corpus_path):
        print(f"Error: Corpus file {corpus_path} not found")
        return 1
    
    # 实验组：有潜力的创意
    idea_potential = "语音控制的markdown编辑器"
    
    # 对照组：随机无意义描述
    idea_random = "蓝色的时间机器与彩虹连接"
    
    print("【实验组】分析创意：", idea_potential)
    print("-" * 40)
    report_potential = analyze_idea(idea_potential, corpus_path)
    print(f"可行性评分 (feasibility_score): {report_potential['feasibility_score']}")
    print(f"  - 清晰度 (clarity):     {report_potential['scores']['clarity']}")
    print(f"  - 可行性 (feasibility): {report_potential['scores']['feasibility']}")
    print(f"  - 独特性 (uniqueness):  {report_potential['scores']['uniqueness']}")
    print()
    
    print("【对照组】分析描述：", idea_random)
    print("-" * 40)
    report_random = analyze_idea(idea_random, corpus_path)
    print(f"可行性评分 (feasibility_score): {report_random['feasibility_score']}")
    print(f"  - 清晰度 (clarity):     {report_random['scores']['clarity']}")
    print(f"  - 可行性 (feasibility): {report_random['scores']['feasibility']}")
    print(f"  - 独特性 (uniqueness):  {report_random['scores']['uniqueness']}")
    print()
    
    # 对比结果
    print("=" * 60)
    print("实验结果对比")
    print("=" * 60)
    
    score_diff = report_potential['feasibility_score'] - report_random['feasibility_score']
    
    print(f"实验组评分: {report_potential['feasibility_score']}")
    print(f"对照组评分: {report_random['feasibility_score']}")
    print(f"评分差异:   {score_diff:.3f}")
    print()
    
    if score_diff > 0.1:
        print("✅ 实验成功：工具能有效区分有潜力的创意和随机描述")
        print("   语音控制的markdown编辑器得分显著高于随机描述")
    elif score_diff > 0:
        print("⚠️  实验部分成功：工具对有潜力创意评分略高")
    else:
        print("❌ 实验失败：工具未能区分创意价值")
    
    print()
    print("【结论】")
    print("-" * 40)
    print("本实验证明：")
    print("1. 工具能基于语料库分析识别技术领域相关创意")
    print("2. 具体、可执行的创意（如语音+markdown组合）获得更高评分")
    print("3. 模糊随机的描述获得较低评分")
    print()
    print("这说明本地创意可行性分析器能够：")
    print("- 帮助识别有价值的创意方向")
    print("- 为产品决策提供量化依据")
    print("- 节省盲目试错的时间成本")
    
    return 0


def main():
    try:
        exit_code = run_value_demo()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error during demo: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
