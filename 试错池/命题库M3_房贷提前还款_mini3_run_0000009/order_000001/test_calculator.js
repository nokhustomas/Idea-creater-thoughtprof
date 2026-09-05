/**
 * 房贷提前还款决策器 - 单元测试
 * 运行：node test_calculator.js
 */
'use strict';

const c = require('./calculator.js');

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) {
    console.log('  ✓ ' + msg);
    pass++;
  } else {
    console.error('  ✗ FAIL: ' + msg);
    fail++;
  }
}
function approx(a, b, eps, msg) {
  assert(Math.abs(a - b) < (eps || 0.5), msg + ' (got ' + a.toFixed(4) + ', expected ~' + b.toFixed(4) + ')');
}

console.log('==== Test 1: 基本等额本息计算 ====');
// 100万贷款，4.9%年利率，30年
// 月供 ≈ 5307.27
const r1 = c.calculate(1000000, 0.049, 30, 0, 0, 0, 'epi', 1, true);
console.log('  月供:', r1.noPrepay.schedule[0].payment);
approx(r1.noPrepay.schedule[0].payment, 5307.27, 0.5, '等额本息月供 ≈ 5307.27');
assert(r1.noPrepay.schedule.length === 360, '等额本息30年共360期');
assert(Math.abs(r1.noPrepay.schedule[359].balance) < 0.5, '末期余额≈0');

console.log('\n==== Test 2: 等额本金计算 ====');
const r2 = c.calculate(1000000, 0.049, 30, 0, 0, 0, 'ep', 1, true);
approx(r2.noPrepay.schedule[0].payment, 6861.11, 0.5, '等额本金首月月供 ≈ 6861.11');
assert(r2.noPrepay.schedule[0].principalPaid > 2700 && r2.noPrepay.schedule[0].principalPaid < 2800, '等额本金首月本金≈2777.78');
assert(r2.noPrepay.schedule[0].interest > 4000 && r2.noPrepay.schedule[0].interest < 4200, '等额本金首月利息≈4083.33');
assert(r2.noPrepay.schedule.length === 360, '等额本金30年共360期');

console.log('\n==== Test 3: 提前还款-缩短年限 ====');
const r3 = c.calculate(1000000, 0.049, 30, 200000, 0, 0, 'epi', 12, true);
console.log('  实际月数(提前后):', r3.prepay.actualMonths);
assert(r3.prepay.actualMonths < 360, '提前还款后月数<360');
assert(r3.prepay.totalPayment < r1.noPrepay.totalPayment, '提前还款总支出<不提前');
assert(r3.prepay.totalInterest < r1.noPrepay.totalInterest, '提前还款利息<不提前');
assert(r3.nominal.interestSaved > 0, '名义利息节省>0');

console.log('\n==== Test 4: 提前还款-降低月供 ====');
const r4 = c.calculate(1000000, 0.049, 30, 200000, 0, 0, 'epi', 12, false);
assert(r4.prepay.actualMonths === 360, '降低月供仍为360期');
assert(r4.prepay.schedule[12].payment < r4.prepay.schedule[0].payment, '第13期月供<首期');

console.log('\n==== Test 5: 机会成本(理财月复利) ====');
// 20万 30年 3%年化 → 终值 = 200000 * (1 + 0.03/12)^360 ≈ 491774.79
const r5 = c.calculate(1000000, 0.049, 30, 200000, 0.03, 0, 'epi', 12, true);
approx(r5.investment.nominalFV, 491774.79, 1, '理财月复利30年终值≈491775');
assert(r5.investment.principal === 200000, '理财本金正确');
assert(r5.investment.nominalFV > 200000, '理财终值>本金');

console.log('\n==== Test 6: 通胀因子(实际值) ====');
const r6 = c.calculate(1000000, 0.049, 30, 200000, 0.03, 0.02, 'epi', 12, true);
assert(r6.noPrepay.realPV > 0, '不提前还款现值(实际)>0');
assert(r6.prepay.realPV > 0, '提前还款现值(实际)>0');
assert(r6.investment.realFV < r6.investment.nominalFV, '通胀使理财终值实际值<名义值');
assert(typeof r6.recommendation === 'string', 'recommendation字段');
assert(r6.noPrepay.realPV < r6.noPrepay.totalPayment, '通胀折现后<名义总额(>0折现率)');

console.log('\n==== Test 7: 极端场景 - 高收益理财优先 ====');
const r7 = c.calculate(500000, 0.049, 20, 100000, 0.05, 0.02, 'epi', 12, true);
console.log('  建议:', r7.recommendation, '净收益(名义):', r7.nominal.netBenefit);

console.log('\n==== Test 8: 极端场景 - 低收益理财优先提前还款 ====');
const r8 = c.calculate(500000, 0.049, 20, 100000, 0.01, 0.02, 'epi', 12, true);
console.log('  建议:', r8.recommendation, '净收益(名义):', r8.nominal.netBenefit);

console.log('\n==== Test 9: 边界 - 不提前还款 ====');
const r9 = c.calculate(1000000, 0.049, 30, 0, 0.03, 0.02, 'epi', 1, true);
assert(r9.prepay === null, '无提前还款金额时不返回prepay字段');
assert(r9.nominal.netBenefit === 0, '无提前还款净收益=0');

console.log('\n==== Test 10: 边界 - 0利率 ====');
const r10 = c.calculate(100000, 0, 10, 0, 0, 0, 'epi', 1, true);
approx(r10.noPrepay.schedule[0].payment, 100000 / 120, 0.01, '0利率月供=本金/期数');
assert(r10.noPrepay.totalInterest === 0, '0利率总利息=0');

console.log('\n==== Test 11: 银行政策JSON完整性 ====');
const fs = require('fs');
const policy = JSON.parse(fs.readFileSync('banks_policy.json', 'utf8'));
assert(Array.isArray(policy.banks), 'banks是数组');
assert(policy.banks.length >= 7, '至少有7家银行');
policy.banks.forEach((b, i) => {
  assert(typeof b.name === 'string' && b.name.length > 0, '第' + (i+1) + '家银行有名称');
  assert(typeof b.source === 'string' && b.source.length > 0, '第' + (i+1) + '家银行有source字段');
  assert(typeof b.prepayment_penalty !== 'undefined', '第' + (i+1) + '家银行有prepayment_penalty字段');
});

console.log('\n==== Test 12: 计算结果格式完整性 ====');
const r12 = c.calculate(500000, 0.039, 25, 100000, 0.025, 0.02, 'epi', 6, true);
assert(typeof r12.inputs === 'object', 'inputs字段');
assert(typeof r12.noPrepay === 'object', 'noPrepay字段');
assert(typeof r12.investment === 'object', 'investment字段');
assert(typeof r12.nominal === 'object', 'nominal字段');
assert(Array.isArray(r12.noPrepay.schedule), 'schedule是数组');
assert(typeof r12.recommendation === 'string', 'recommendation字段');

console.log('\n==== Test 13: 等额本息/本金总利息对照 ====');
// 利率相同时，等额本金总利息 < 等额本息
const r13a = c.calculate(1000000, 0.049, 30, 0, 0, 0, 'epi', 1, true);
const r13b = c.calculate(1000000, 0.049, 30, 0, 0, 0, 'ep', 1, true);
assert(r13b.noPrepay.totalInterest < r13a.noPrepay.totalInterest, '等额本金总利息<等额本息');

console.log('\n==== Test 14: 月复利计算正确性(单期) ====');
// 1万 12个月 12%年化 → 月利率1% → 终值 = 10000 * 1.01^12 ≈ 11268.25
const r14 = c.calculate(0, 0, 1, 10000, 0.12, 0, 'epi', 1, true);
approx(r14.investment.nominalFV, 11268.25, 0.5, '1万 12%年化 1年终值≈11268.25');

console.log('\n=============================');
console.log('PASS: ' + pass + ', FAIL: ' + fail);
console.log('=============================');
process.exit(fail > 0 ? 1 : 0);
