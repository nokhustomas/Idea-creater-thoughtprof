/**
 * 房贷提前还款决策器 - 计算逻辑模块
 * Mortgage Prepayment Decision Calculator
 *
 * 功能：
 *  - 等额本息 (EPI) 与 等额本金 (EP) 月供计算
 *  - 提前还款情境：可缩短年限或降低月供
 *  - 机会成本：理财收益按月复利计算
 *  - 通胀因子：调整每期现金流至今日购买力（实际值）
 *
 * 函数 calculate 主入口：
 *  principal         贷款余额（元）
 *  annualRate        年利率（小数，如 0.049 表示 4.9%）
 *  years             剩余年限
 *  prepaymentAmount  拟提前还款金额（元）
 *  investReturn      理财年化收益率（小数）
 *  inflationRate     通胀年化率（小数）
 *  method            'epi' 等额本息 / 'ep' 等额本金
 *  prepayMonth       提前还款月份（1=第1个月，默认1）
 *  reduceTerm        true=缩短年限(默认) / false=降低月供
 */

(function (global) {
  'use strict';

  function round2(x) {
    return Math.round(x * 100) / 100;
  }

  /**
   * 模拟一笔贷款，可选在某个月提前还款。
   */
  function simulateLoan(principal, annualRate, years, method, prepaymentAmount, prepayMonth, reduceTerm) {
    const r = annualRate / 12;
    const n = years * 12;
    const schedule = [];
    let balance = principal;
    let totalPayment = 0;
    let totalInterest = 0;

    let monthlyPayment = 0;
    let monthlyPrincipal = 0;

    if (method === 'epi') {
      if (r === 0) {
        monthlyPayment = principal / n;
      } else {
        monthlyPayment = principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
      }
    } else if (method === 'ep') {
      monthlyPrincipal = principal / n;
    } else {
      throw new Error('Unknown method: ' + method + ' (use "epi" or "ep")');
    }

    let month = 0;
    let remainingN = n;
    const maxIter = n + 12;

    while (balance > 0.005 && month < maxIter) {
      month++;
      const interest = balance * r;
      let principalPaid = 0;
      let payment = 0;
      let prepayThisMonth = 0;

      if (method === 'epi') {
        payment = monthlyPayment;
        principalPaid = payment - interest;
        if (principalPaid > balance) {
          principalPaid = balance;
          payment = principalPaid + interest;
        }
      } else {
        principalPaid = Math.min(monthlyPrincipal, balance);
        payment = principalPaid + interest;
      }

      if (month === prepayMonth && prepaymentAmount > 0 && balance > 0) {
        const maxPrepay = balance - principalPaid;
        prepayThisMonth = Math.max(0, Math.min(prepaymentAmount, maxPrepay));
      }

      balance -= (principalPaid + prepayThisMonth);
      if (balance < 0.005) balance = 0;

      totalPayment += payment + prepayThisMonth;
      totalInterest += interest;

      schedule.push({
        month: month,
        payment: round2(payment + prepayThisMonth),
        principalPaid: round2(principalPaid + prepayThisMonth),
        interest: round2(interest),
        balance: round2(balance),
        prepay: round2(prepayThisMonth)
      });

      if (prepayThisMonth > 0 && balance > 0) {
        remainingN = n - month;
        if (method === 'epi') {
          if (!reduceTerm) {
            if (r === 0) {
              monthlyPayment = balance / remainingN;
            } else {
              monthlyPayment = balance * r * Math.pow(1 + r, remainingN) /
                (Math.pow(1 + r, remainingN) - 1);
            }
          }
        } else {
          monthlyPrincipal = balance / remainingN;
        }
      }
    }

    return {
      schedule: schedule,
      totalPayment: round2(totalPayment),
      totalInterest: round2(totalInterest),
      actualMonths: month,
      method: method
    };
  }

  function simulateInvestment(principal, annualRate, months) {
    const i = annualRate / 12;
    const schedule = [];
    let balance = principal;
    for (let m = 1; m <= months; m++) {
      const interest = balance * i;
      balance += interest;
      schedule.push({ month: m, contribution: 0, interest: round2(interest), balance: round2(balance) });
    }
    return { schedule: schedule, finalValue: round2(balance), totalReturn: round2(balance - principal), principal: principal, annualRate: annualRate };
  }

  function realPV(cashFlows, annualInflation) {
    const inflM = annualInflation / 12;
    let sum = 0;
    for (let k = 0; k < cashFlows.length; k++) {
      sum += cashFlows[k].amount / Math.pow(1 + inflM, cashFlows[k].month);
    }
    return sum;
  }

  function calculate(principal, annualRate, years, prepaymentAmount,
                     investReturn, inflationRate, method, prepayMonth, reduceTerm) {
    if (typeof method === 'undefined') method = 'epi';
    if (typeof prepayMonth === 'undefined') prepayMonth = 1;
    if (typeof reduceTerm === 'undefined') reduceTerm = true;
    if (typeof prepaymentAmount === 'undefined') prepaymentAmount = 0;
    if (typeof investReturn === 'undefined') investReturn = 0;
    if (typeof inflationRate === 'undefined') inflationRate = 0;

    prepaymentAmount = Number(prepaymentAmount) || 0;
    investReturn = Number(investReturn) || 0;
    inflationRate = Number(inflationRate) || 0;
    prepayMonth = Number(prepayMonth) || 1;
    principal = Number(principal);
    annualRate = Number(annualRate);
    years = Number(years);

    const n = years * 12;
    const inflM = inflationRate / 12;

    const noPrepay = simulateLoan(principal, annualRate, years, method, 0, 0, reduceTerm);
    const hasPrepay = prepaymentAmount > 0 && prepaymentAmount < principal;
    const prepay = hasPrepay
      ? simulateLoan(principal, annualRate, years, method, prepaymentAmount, prepayMonth, reduceTerm)
      : null;
    const investment = simulateInvestment(prepaymentAmount, investReturn, n);

    const endingWealthNoPrepayNominal = -noPrepay.totalPayment + investment.finalValue;
    const endingWealthPrepayNominal = hasPrepay ? (-prepaymentAmount - prepay.totalPayment) : endingWealthNoPrepayNominal;
    const nominalNetBenefit = endingWealthPrepayNominal - endingWealthNoPrepayNominal;
    const nominalSavings = hasPrepay ? (noPrepay.totalPayment - prepay.totalPayment) : 0;
    const interestSavedNominal = hasPrepay ? (noPrepay.totalInterest - prepay.totalInterest) : 0;

    const noPrepayRealOutflowPV = realPV(noPrepay.schedule, inflationRate);
    const prepayRealOutflowPV = hasPrepay ? realPV(prepay.schedule, inflationRate) : 0;
    const investmentRealFV = investment.finalValue / Math.pow(1 + inflM, n);

    const realWealthNoPrepay = -noPrepayRealOutflowPV + investmentRealFV;
    const realWealthPrepay = hasPrepay ? (-prepaymentAmount - prepayRealOutflowPV) : realWealthNoPrepay;
    const realNetBenefit = realWealthPrepay - realWealthNoPrepay;

    let recommendation = 'NO_PREPAYMENT';
    if (hasPrepay) {
      recommendation = realNetBenefit > 0 ? 'PREPAY' : 'INVEST';
    }

    return {
      inputs: {
        principal: principal,
        annualRate: annualRate,
        years: years,
        prepaymentAmount: prepaymentAmount,
        investReturn: investReturn,
        inflationRate: inflationRate,
        method: method,
        prepayMonth: prepayMonth,
        reduceTerm: reduceTerm
      },
      noPrepay: {
        schedule: noPrepay.schedule,
        totalPayment: noPrepay.totalPayment,
        totalInterest: noPrepay.totalInterest,
        actualMonths: noPrepay.actualMonths,
        realPV: round2(noPrepayRealOutflowPV)
      },
      prepay: prepay ? {
        schedule: prepay.schedule,
        totalPayment: prepay.totalPayment,
        totalInterest: prepay.totalInterest,
        actualMonths: prepay.actualMonths,
        realPV: round2(prepayRealOutflowPV)
      } : null,
      investment: {
        principal: prepaymentAmount,
        annualRate: investReturn,
        nominalFV: investment.finalValue,
        realFV: round2(investmentRealFV)
      },
      nominal: {
        endingWealthNoPrepay: round2(endingWealthNoPrepayNominal),
        endingWealthPrepay: round2(endingWealthPrepayNominal),
        netBenefit: round2(nominalNetBenefit),
        savings: round2(nominalSavings),
        interestSaved: round2(interestSavedNominal)
      },
      real: {
        endingWealthNoPrepay: round2(realWealthNoPrepay),
        endingWealthPrepay: round2(realWealthPrepay),
        netBenefit: round2(realNetBenefit)
      },
      recommendation: recommendation
    };
  }

  function monthlyPaymentEPI(principal, annualRate, years) {
    const r = annualRate / 12;
    const n = years * 12;
    if (r === 0) return principal / n;
    return principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
  }

  const api = {
    calculate: calculate,
    simulateLoan: simulateLoan,
    simulateInvestment: simulateInvestment,
    monthlyPaymentEPI: monthlyPaymentEPI,
    round2: round2
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (typeof global !== 'undefined') {
    global.MortgageCalculator = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);