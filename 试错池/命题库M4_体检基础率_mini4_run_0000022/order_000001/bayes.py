# -*- coding: utf-8 -*-
"""
贝叶斯后验概率计算模块

适用场景：在某项体检初筛异常（阳性）之后，已知该检测的灵敏度 sensitivity
与假阳性率 false_positive_rate，结合该指标在同年龄同性别人群中的患病率
（先验概率 prior），求该人真实患病的概率（后验）。

核心公式（任务约定，含义：阳性证据出现后真患病的概率）：
  posterior = sensitivity * prior / (sensitivity * prior + false_positive_rate)

边界：
  - prior=0 或 1 时直接返回 0 / 1，避免除零
  - 所有输入若超出 [0,1] 视为非法输入，抛出 ValueError
"""

from typing import Dict, Any


def calc(prior: float, sensitivity: float, false_positive_rate: float) -> float:
    """
    计算贝叶斯后验概率（短名）。
    公式：posterior = sensitivity * prior / (sensitivity * prior + false_positive_rate)
    :param prior: 先验概率（患病率），取值 [0, 1]
    :param sensitivity: 检测灵敏度 P(B|A)，取值 [0, 1]
    :param false_positive_rate: 假阳性率 P(B|¬A)，取值 [0, 1]
    :return: 后验概率 P(A|B)，保留 3 位小数
    """
    for name, val in (('prior', prior), ('sensitivity', sensitivity), ('false_positive_rate', false_positive_rate)):
        if val < 0 or val > 1:
            raise ValueError(f'{name} 必须位于 [0,1]，当前为 {val}')

    # 边界：先验为 0 时，阳性必为假阳性 → 后验 0
    if prior == 0:
        return 0.0
    # 边界：先验为 1 时，阳性必为真阳性 → 后验 1
    if prior == 1:
        return 1.0
    # 边界：灵敏度为 0 → 后验 0
    if sensitivity == 0:
        return 0.0
    # 边界：假阳性率为 0 → 后验 1
    if false_positive_rate == 0:
        return 1.0

    num = sensitivity * prior
    den = num + false_positive_rate
    if den == 0:
        return 0.0
    posterior = num / den
    return round(posterior, 3)


# 别名，兼容老代码
calc_posterior = calc


def calc_with_steps(prior: float, sensitivity: float, false_positive_rate: float) -> Dict[str, Any]:
    """
    计算后验并返回展开复算过程的步骤字典，便于前端展示。
    """
    for name, val in (('prior', prior), ('sensitivity', sensitivity), ('false_positive_rate', false_positive_rate)):
        if val < 0 or val > 1:
            raise ValueError(f'{name} 必须位于 [0,1]，当前为 {val}')

    p_a = prior
    p_not_a = 1 - prior
    p_b_given_a = sensitivity
    p_b_given_not_a = false_positive_rate

    if prior == 0:
        posterior = 0.0
        p_b = p_b_given_not_a
    elif prior == 1:
        posterior = 1.0
        p_b = p_b_given_a
    elif sensitivity == 0:
        posterior = 0.0
        p_b = p_b_given_not_a
    elif false_positive_rate == 0:
        posterior = 1.0
        p_b = p_b_given_a * p_a
    else:
        num = p_b_given_a * p_a
        den = num + p_b_given_not_a
        p_b = den
        posterior = num / den

    p_a_given_b = round(posterior, 3)

    steps = [
        f'先验概率 P(A) = {round(p_a, 4)}',
        f'检测灵敏度 P(B|A) = {round(p_b_given_a, 4)}',
        f'假阳性率 P(B|¬A) = {round(p_b_given_not_a, 4)}',
        f'分子 = P(B|A)·P(A) = {round(p_b_given_a, 4)}×{round(p_a, 4)} = {round(p_b_given_a * p_a, 4)}',
        f'分母 = P(B|A)·P(A) + P(B|¬A) = {round(p_b_given_a * p_a, 4)} + {round(p_b_given_not_a, 4)} = {round(p_b, 4)}',
        f'贝叶斯公式 P(A|B) = 分子 / 分母 = {round(p_b_given_a * p_a, 4)} / {round(p_b, 4)} = {p_a_given_b}',
    ]

    return {
        'prior': round(p_a, 4),
        'sensitivity': round(p_b_given_a, 4),
        'false_positive_rate': round(p_b_given_not_a, 4),
        'p_b': round(p_b, 4),
        'posterior': p_a_given_b,
        'steps': steps,
    }


if __name__ == '__main__':
    # 自检：calc(0.1, 0.9, 0.05) 必须等于 0.643
    r = calc(0.1, 0.9, 0.05)
    print('posterior:', r)
    assert abs(r - 0.643) < 1e-9, f'期望 0.643，实际 {r}'

    r2 = calc(0.0, 0.9, 0.05)
    assert r2 == 0.0
    r3 = calc(1.0, 0.9, 0.05)
    assert r3 == 1.0
    print('bayes.py 自检通过')