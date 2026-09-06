# -*- coding: utf-8 -*-
"""
体检异常指标真相解读器 — Flask 后端

路由：
  GET  /            渲染主页
  POST /calculate   接收 {age, gender, abnormal: [code,...]}，返回贝叶斯后验结果

合规边界：
  - 任何返回结果都附带 disclaimer = "以医生意见为准"
  - 不输出任何"建议服用""无需就医""可以不管"等诊疗话术
"""

from flask import Flask, render_template, request, jsonify

import data as disease_data
from bayes import calc_with_steps


app = Flask(__name__)

DISCLAIMER = '以医生意见为准'


@app.route('/')
def index():
    return render_template('index.html',
                           disease_meta=disease_data.DISEASE_META,
                           disclaimer=DISCLAIMER)


@app.route('/calculate', methods=['POST'])
def calculate():
    payload = request.get_json(silent=True) or {}
    age = payload.get('age')
    gender_raw = payload.get('gender')
    abnormal = payload.get('abnormal')

    # 校验
    if not age or age not in disease_data.AGE_GROUPS:
        return jsonify({'error': '年龄段无效', 'disclaimer': DISCLAIMER}), 400
    if gender_raw not in ('male', 'female'):
        return jsonify({'error': '性别参数无效', 'disclaimer': DISCLAIMER}), 400
    if not isinstance(abnormal, list) or not abnormal:
        return jsonify({'error': '请至少选择一项异常指标', 'disclaimer': DISCLAIMER}), 400

    gender_zh = '男' if gender_raw == 'male' else '女'

    results = []
    for code in abnormal:
        if code not in disease_data.DISEASE_DATA:
            results.append({
                'code': code,
                'name': code,
                'error': '未知异常项',
                'disclaimer': DISCLAIMER,
            })
            continue

        prior = disease_data.get_prevalence(code, age, gender_zh)
        sens = disease_data.DEFAULT_SENSITIVITY
        fpr = disease_data.DEFAULT_FALSE_POSITIVE_RATE
        calc = calc_with_steps(prior, sens, fpr)

        meta = disease_data.DISEASE_META.get(code, {})
        results.append({
            'code': code,
            'name': meta.get('name', code),
            'description': meta.get('description', ''),
            'unit': meta.get('unit', ''),
            'age_group': age,
            'gender': gender_zh,
            'prior': calc['prior'],
            'sensitivity': calc['sensitivity'],
            'false_positive_rate': calc['false_positive_rate'],
            'p_b': calc['p_b'],
            'posterior': calc['posterior'],
            'steps': calc['steps'],
            'review_path': disease_data.get_review_path(code),
            'source': disease_data.get_source(code, age),
            'disclaimer': DISCLAIMER,
        })

    return jsonify({
        'age': age,
        'gender': gender_zh,
        'results': results,
        'disclaimer': DISCLAIMER,
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)