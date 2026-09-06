# -*- coding: utf-8 -*-
"""
体检异常指标患病率数据字典

数据结构：
  DISEASE_DATA: { 异常项代码: { 年龄段: { '男': rate, '女': rate, 'source': '...' } } }

注意：
  - 所有患病率数据均为公开流行病学数据估算值，截至训练数据，需读者结合最新指南核实。
  - 性别差异调整系数 0.6（用于甲状腺结节男女比）属于估算值，缺乏精确文献支撑，请谨慎使用。
"""

from typing import Dict, Any


# 年龄段统一编码
AGE_GROUPS = ['20-29', '30-39', '40-49', '50-59', '60+']

# 异常项元信息（用于前端展示）
DISEASE_META = {
    'thyroid_nodule': {
        'name': '甲状腺结节',
        'unit': '超声检出率',
        'description': '甲状腺超声检查发现的结节性病变',
    },
    'colorectal_polyp': {
        'name': '结直肠息肉',
        'unit': '肠镜检出率',
        'description': '结肠镜检查发现的息肉样病变',
    },
    'alt_abnormal': {
        'name': '转氨酶异常(ALT>40U/L)',
        'unit': '血清学异常率',
        'description': '丙氨酸氨基转移酶超过 40 U/L',
    },
    'fatty_liver': {
        'name': '脂肪肝',
        'unit': '影像学检出率',
        'description': 'B超/CT 等影像学发现的肝脏脂肪浸润',
    },
}


def _mk_node(rates_female: Dict[str, float], source: str, male_ratio: float = 0.6) -> Dict[str, Dict[str, Any]]:
    """根据女性各年龄段患病率与男女比系数，生成 age -> {男, 女, source} 嵌套字典。"""
    out: Dict[str, Dict[str, Any]] = {}
    for ag, fr in rates_female.items():
        out[ag] = {
            '男': round(fr * male_ratio, 4),
            '女': fr,
            'source': source,
        }
    return out


def _mk_node_no_gender_diff(rates: Dict[str, float], source: str) -> Dict[str, Dict[str, Any]]:
    """男女患病率相同的情况（如部分结直肠息肉数据按年龄段不分性别）"""
    out: Dict[str, Dict[str, Any]] = {}
    for ag, r in rates.items():
        out[ag] = {
            '男': r,
            '女': r,
            'source': source,
        }
    return out


# 1. 甲状腺结节（女性按年龄段；男性约为女性的 0.6 倍）
THYROID_NODULE_FEMALE = {
    '20-29': 0.042,
    '30-39': 0.098,
    '40-49': 0.156,
    '50-59': 0.223,
    '60+':   0.287,
}
THYROID_NODULE_SOURCE = '来源：中国甲状腺疾病诊治指南（2020版）甲状腺结节流行病学数据（截至训练数据，需核）'

# 2. 结直肠息肉（不分性别，按年龄段）
COLORECTAL_POLYP = {
    '20-29': 0.05,
    '30-39': 0.05,
    '40-49': 0.12,
    '50-59': 0.25,
    '60+':   0.35,
}
COLORECTAL_POLYP_SOURCE = '来源：中国消化内镜学会结直肠息肉筛查共识（2019）（截至训练数据，需核）'

# 3. 转氨酶异常 ALT>40U/L（不分性别，按年龄段）
ALT_ABNORMAL = {
    '20-29': 0.08,
    '30-39': 0.08,
    '40-49': 0.15,
    '50-59': 0.15,
    '60+':   0.22,
}
ALT_ABNORMAL_SOURCE = '来源：中国卫生健康统计年鉴（2020）肝病相关章节（截至训练数据，需核）'

# 4. 脂肪肝：20-49 岁男 30%/女 15%；50 岁及以上男 35%/女 25%
FATTY_LIVER = {}
for ag in ['20-29', '30-39', '40-49']:
    FATTY_LIVER[ag] = {
        '男': 0.30,
        '女': 0.15,
        'source': '来源：中国非酒精性脂肪性肝病诊疗指南（2018版）（截至训练数据，需核）',
    }
for ag in ['50-59', '60+']:
    FATTY_LIVER[ag] = {
        '男': 0.35,
        '女': 0.25,
        'source': '来源：中国非酒精性脂肪性肝病诊疗指南（2018版）（截至训练数据，需核）',
    }


# 主数据字典
DISEASE_DATA: Dict[str, Dict[str, Dict[str, Any]]] = {
    'thyroid_nodule':  _mk_node(THYROID_NODULE_FEMALE, THYROID_NODULE_SOURCE, male_ratio=0.6),
    'colorectal_polyp': _mk_node_no_gender_diff(COLORECTAL_POLYP, COLORECTAL_POLYP_SOURCE),
    'alt_abnormal':    _mk_node_no_gender_diff(ALT_ABNORMAL, ALT_ABNORMAL_SOURCE),
    'fatty_liver':     FATTY_LIVER,
}


# 默认检测敏感度与假阳性率（行业经验值，需按具体项目核实）
DEFAULT_SENSITIVITY = 0.9
DEFAULT_FALSE_POSITIVE_RATE = 0.05

# 复查路径建议（医学共识科普文案，不构成诊疗建议）
REVIEW_PATH = {
    'thyroid_nodule': '医学共识科普：甲状腺结节 TI-RADS 分类评估；一般 6-12 月复查超声；以医生意见为准。',
    'colorectal_polyp': '医学共识科普：依据息肉病理决定复查间隔；通常 1-3 年内复查肠镜；以医生意见为准。',
    'alt_abnormal': '医学共识科普：排除药物/饮酒/脂肪肝等可逆因素后复查肝功能；以医生意见为准。',
    'fatty_liver': '医学共识科普：生活方式干预为主，半年-1 年复查肝功能及肝脏超声；以医生意见为准。',
}


def list_diseases() -> list:
    """返回所有异常项代码列表。"""
    return list(DISEASE_DATA.keys())


def get_prevalence(disease_code: str, age_group: str, gender: str) -> float:
    """
    查询某异常项在某年龄段某性别下的患病率（先验概率）。
    返回 float，若未命中返回 0.0。
    """
    if disease_code not in DISEASE_DATA:
        return 0.0
    ag_map = DISEASE_DATA[disease_code].get(age_group)
    if not ag_map:
        # 跨段就近回退：例如转氨酶异常的 20-39 合并段
        # 优先尝试邻接段
        ordered = ['20-29', '30-39', '40-49', '50-59', '60+']
        if age_group in ordered:
            idx = ordered.index(age_group)
            for j in (idx - 1, idx + 1):
                if 0 <= j < len(ordered):
                    nb = DISEASE_DATA[disease_code].get(ordered[j])
                    if nb and gender in nb:
                        return float(nb[gender])
        return 0.0
    val = ag_map.get(gender)
    return float(val) if val is not None else 0.0


def get_source(disease_code: str, age_group: str = '') -> str:
    """获取数据来源字符串。"""
    if disease_code not in DISEASE_DATA:
        return '来源：未知'
    if age_group and age_group in DISEASE_DATA[disease_code]:
        return DISEASE_DATA[disease_code][age_group].get('source', '来源：未知')
    # 取任意一条的 source
    first_ag = next(iter(DISEASE_DATA[disease_code]), '')
    if first_ag:
        return DISEASE_DATA[disease_code][first_ag].get('source', '来源：未知')
    return '来源：未知'


def get_review_path(disease_code: str) -> str:
    """获取医学共识复查路径文案（科普）。"""
    return REVIEW_PATH.get(disease_code, '医学共识科普：请遵医嘱复查；以医生意见为准。')


if __name__ == '__main__':
    # 自检
    assert get_prevalence('thyroid_nodule', '30-39', '女') == 0.098
    print('data.py 自检通过')
    print('甲状腺结节 30-39 女:', get_prevalence('thyroid_nodule', '30-39', '女'))
    print('脂肪肝 50-59 男:', get_prevalence('fatty_liver', '50-59', '男'))
    print('结直肠息肉 60+ 男:', get_prevalence('colorectal_polyp', '60+', '男'))