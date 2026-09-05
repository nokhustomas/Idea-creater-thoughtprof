/* script.js — 交互逻辑：工具栏、画布事件、动画、撤销 */
(function () {
  'use strict';
  const svg = document.getElementById('board');
  const status = document.getElementById('status');
  const gElements = document.getElementById('elements');
  const gPoints = document.getElementById('points');
  const gOverlay = document.getElementById('overlay');
  const captionText = document.getElementById('caption-text');
  const points = [];
  const elements = [];
  const stepStack = [];
  let currentTool = 'ruler';
  let nextId = 1;
  let compassCenter = null;
  let rulerFirstPoint = null;
  let animHandle = null, animSteps = [], animIndex = 0, animLastTs = 0;
  const ANIM_STEP_MS = 900;

  function genId(p) { return (p || 'e') + '-' + (nextId++); }
  function setStatus(t) { status.textContent = '当前工具：' + t; }
  function setCaption(t) { captionText.textContent = t; }

  function svgPt(evt) {
    const r = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    return new Point((evt.clientX - r.left) * vb.width / r.width,
                     (evt.clientY - r.top) * vb.height / r.height);
  }
  function nearest(p, th) {
    th = th || 14;
    let b = null, bd = th;
    for (const q of points) { const d = distance(p, q); if (d < bd) { b = q; bd = d; } }
    return b;
  }

  function drawPt(p, o) {
    o = o || {};
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x); c.setAttribute('cy', p.y);
    c.setAttribute('r', o.r || 5);
    c.setAttribute('fill', o.color || '#e11d48');
    c.setAttribute('stroke', '#333'); c.setAttribute('stroke-width', '1');
    c.classList.add('board-point'); c.dataset.pointId = p.id || '';
    gPoints.appendChild(c);
    let lbl = null;
    if (o.label) {
      const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      t.setAttribute('x', p.x + 8); t.setAttribute('y', p.y - 8);
      t.setAttribute('font-size', '14'); t.setAttribute('font-weight', '600');
      t.setAttribute('fill', '#1a237e'); t.textContent = o.label;
      gPoints.appendChild(t); lbl = t;
    }
    return { node: c, labelNode: lbl };
  }
  function drawLn(p1, p2, o) {
    o = o || {};
    const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    l.setAttribute('x1', p1.x); l.setAttribute('y1', p1.y);
    l.setAttribute('x2', p2.x); l.setAttribute('y2', p2.y);
    l.setAttribute('stroke', o.color || '#1976d2');
    l.setAttribute('stroke-width', o.width || 2);
    l.classList.add('board-line'); gElements.appendChild(l);
    return l;
  }
  function drawCir(c, o) {
    o = o || {};
    const e = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    e.setAttribute('cx', c.center.x); e.setAttribute('cy', c.center.y);
    e.setAttribute('r', c.radius); e.setAttribute('fill', 'none');
    e.setAttribute('stroke', o.color || '#2e7d32');
    e.setAttribute('stroke-width', o.width || 2);
    if (o.dashed) e.setAttribute('stroke-dasharray', '6,4');
    e.classList.add('board-circle'); gElements.appendChild(e);
    return e;
  }
  function drawPoly(pts, o) {
    o = o || {};
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    p.setAttribute('points', pts.map(q => q.x.toFixed(2) + ',' + q.y.toFixed(2)).join(' '));
    p.setAttribute('fill', o.fill || 'rgba(255,193,7,0.25)');
    p.setAttribute('stroke', o.color || '#ef6c00');
    p.setAttribute('stroke-width', '2');
    p.classList.add('board-polygon'); gElements.appendChild(p);
    return p;
  }
  function clearBoard() {
    while (gElements.firstChild) gElements.removeChild(gElements.firstChild);
    while (gPoints.firstChild) gPoints.removeChild(gPoints.firstChild);
    while (gOverlay.firstChild) gOverlay.removeChild(gOverlay.firstChild);
    points.length = 0; elements.length = 0; stepStack.length = 0;
    compassCenter = null; rulerFirstPoint = null;
    setCaption('点击"演示"按钮开始');
  }

  function pushStep(r) { stepStack.push(r); }
  function popStep() {
    const last = stepStack.pop(); if (!last) return;
    (last.nodes || []).forEach(n => { if (n && n.parentNode) n.parentNode.removeChild(n); });
    (last.addedPoints || []).forEach(p => { const i = points.lastIndexOf(p); if (i >= 0) points.splice(i, 1); });
    if (last.addedElement) {
      const i = elements.lastIndexOf(last.addedElement);
      if (i >= 0) elements.splice(i, 1);
    }
  }
  function addPoint(p, o) { p.id = p.id || genId('p'); points.push(p); const d = drawPt(p, o); return { point: p, node: d.node, labelNode: d.labelNode }; }
  function addElement(r) { elements.push(r); return r; }

  function setTool(name) {
    currentTool = name;
    document.querySelectorAll('.tool-btn[data-tool]').forEach(b => b.classList.toggle('active', b.dataset.tool === name));
    setStatus(name === 'ruler' ? '直尺' : name === 'compass' ? '圆规' : '选中');
    compassCenter = null; rulerFirstPoint = null;
  }
  document.querySelectorAll('.tool-btn[data-tool]').forEach(b => b.addEventListener('click', () => setTool(b.dataset.tool)));
  document.getElementById('undo').addEventListener('click', popStep);
  document.getElementById('reset').addEventListener('click', clearBoard);
  document.getElementById('next-step').addEventListener('click', () => { if (animHandle) animStepForward(); });
  document.getElementById('demo-pentagon').addEventListener('click', runPentagonDemo);
  document.getElementById('demo-heptagon').addEventListener('click', runHeptagonDemo);

  // 弹出菜单：当有多交点时用 prompt 让用户选序号
  function pickFromMany(candidates, label) {
    if (candidates.length <= 1) return candidates[0];
    const list = candidates.map((p, i) => `${i}: (${p.x.toFixed(1)}, ${p.y.toFixed(1)})`).join('\n');
    const ans = window.prompt(`${label}：共 ${candidates.length} 个候选项，输入序号\n${list}`, '0');
    const idx = parseInt(ans, 10);
    if (isNaN(idx) || idx < 0 || idx >= candidates.length) return candidates[0];
    return candidates[idx];
  }

  // 圆规：单击定圆心，再单击定半径
  function handleCompassClick(useP) {
    if (!compassCenter) {
      compassCenter = useP; compassCenter.id = genId('c');
      const added = addPoint(compassCenter, { color: '#1565c0', label: 'O' });
      pushStep({ nodes: [added.node, added.labelNode].filter(Boolean), addedPoints: [compassCenter] });
      setCaption('圆心已选，再<strong>单击</strong>另一点确定半径');
    } else {
      finalizeCompass(useP);
    }
  }
  function finalizeCompass(p) {
    if (!compassCenter) return;
    const r = distance(compassCenter, p);
    const c = new Circle(compassCenter, r);
    const node = drawCir(c, { color: '#2e7d32' });
    const rec = addElement({ kind: 'circle', ref: c, node });
    pushStep({ nodes: [node], addedElement: rec });
    // 自动算与其它圆 / 直线的交点
    computeAllIntersections();
    compassCenter = null;
    setCaption('圆已画好');
  }
  // 直尺：单击两点画线
  function handleRulerClick(useP, rawP) {
    if (!rulerFirstPoint) {
      rulerFirstPoint = useP; rulerFirstPoint.id = genId('l1');
      const added = addPoint(rulerFirstPoint, { color: '#6a1b9a', label: 'A' });
      pushStep({ nodes: [added.node, added.labelNode].filter(Boolean), addedPoints: [rulerFirstPoint] });
      setCaption('已选第一个点，再<strong>单击</strong>第二个点画线');
    } else {
      const p2 = useP; p2.id = genId('l2');
      const added2 = addPoint(p2, { color: '#6a1b9a', label: 'B' });
      const l = new Line(rulerFirstPoint, p2);
      const node = drawLn(rulerFirstPoint, p2, { color: '#1976d2' });
      const rec = addElement({ kind: 'line', ref: l, node });
      pushStep({ nodes: [node, added2.node, added2.labelNode].filter(Boolean), addedPoints: [p2], addedElement: rec });
      computeAllIntersections();
      rulerFirstPoint = null;
    }
  }
  function handleSelectClick(p) {
    setCaption(`选中了 (${p.x.toFixed(1)}, ${p.y.toFixed(1)})；按 Ctrl+Z 撤销`);
  }

  // 计算所有新元素与现有元素的交点
  function computeAllIntersections() {
    const circles = elements.filter(e => e.kind === 'circle').map(e => e.ref);
    const lines = elements.filter(e => e.kind === 'line').map(e => e.ref);
    for (const c of circles) {
      for (const l of lines) {
        const ips = intersectLineCircle(l, c);
        if (ips.length === 0) continue;
        const ip = ips.length > 1 ? pickFromMany(ips, '直线与圆交点') : ips[0];
        ip.id = genId('ip');
        const added = addPoint(ip, { color: '#00838f', label: 'P' });
        pushStep({ nodes: [added.node, added.labelNode].filter(Boolean), addedPoints: [ip] });
      }
    }
    for (let i = 0; i < circles.length; i++) {
      for (let j = i + 1; j < circles.length; j++) {
        const ips = intersectCircleCircle(circles[i], circles[j]);
        if (ips.length === 0) continue;
        const ip = ips.length > 1 ? pickFromMany(ips, '两圆交点') : ips[0];
        ip.id = genId('ip');
        const added = addPoint(ip, { color: '#00838f', label: 'Q' });
        pushStep({ nodes: [added.node, added.labelNode].filter(Boolean), addedPoints: [ip] });
      }
    }
  }

  // 动画：每步是一个函数
  function runAnimation(steps, onDone) {
    if (animHandle) cancelAnimationFrame(animHandle);
    clearBoard();
    animSteps = steps; animIndex = 0; animLastTs = 0;
    function frame(ts) {
      if (!animLastTs) animLastTs = ts;
      if (ts - animLastTs >= ANIM_STEP_MS) {
        if (animIndex >= animSteps.length) {
          cancelAnimationFrame(animHandle); animHandle = null;
          if (onDone) onDone();
          return;
        }
        animSteps[animIndex]();
        animIndex++;
        animLastTs = ts;
      }
      animHandle = requestAnimationFrame(frame);
    }
    animHandle = requestAnimationFrame(frame);
  }
  function animStepForward() {
    if (!animHandle || animIndex >= animSteps.length) return;
    animSteps[animIndex](); animIndex++; animLastTs = performance.now();
  }

  // 演示 1：正五边形
  function runPentagonDemo() {
    setTool('compass');
    const steps = [
      () => setCaption('正五边形：第 1 步，在画布上任选一点作圆心'),
      () => {
        const O = new Point(400, 300); O.id = genId('c');
        const added = addPoint(O, { color: '#1565c0', label: 'O' });
        pushStep({ nodes: [added.node, added.labelNode].filter(Boolean), addedPoints: [O] });
        compassCenter = O;
        setCaption('第 2 步：以 O 为圆心画一个单位圆');
      },
      () => {
        const A = new Point(550, 300);
        const c = new Circle(compassCenter, distance(compassCenter, A));
        const node = drawCir(c, { color: '#2e7d32' });
        addElement({ kind: 'circle', ref: c, node });
        pushStep({ nodes: [node], addedElement: elements[elements.length - 1] });
        const addedA = addPoint(A, { color: '#6a1b9a', label: 'A' });
        pushStep({ nodes: [addedA.node, addedA.labelNode].filter(Boolean), addedPoints: [A] });
        setCaption('第 3 步：在圆上任取 A，连接 OA 作中垂线找五等分点');
      },
      () => {
        const O = compassCenter; const B = new Point(250, 300);
        const c2 = new Circle(O, distance(O, B));
        const n2 = drawCir(c2, { color: '#2e7d32', dashed: true });
        addElement({ kind: 'circle', ref: c2, node: n2 });
        setCaption('第 4 步：以 A、OA 之中点 M 为圆心作辅助圆');
      },
      () => {
        // 画正五边形 5 个顶点
        const O = new Point(400, 300);
        const R = 150;
        const v = divideCirclePoints(new Circle(O, R), 5, -Math.PI / 2);
        const poly = drawPoly(v, { fill: 'rgba(255,193,7,0.35)', color: '#ef6c00' });
        v.forEach((p, i) => {
          const ap = addPoint(p, { color: '#ef6c00', label: 'V' + (i + 1) });
          pushStep({ nodes: [ap.node, ap.labelNode].filter(Boolean), addedPoints: [p] });
        });
        pushStep({ nodes: [poly] });
        setCaption('正五边形作出！因为 cos(36°) 的极小多项式次数 2 = 2¹');
      },
    ];
    runAnimation(steps, () => setCaption('正五边形演示完毕'));
  }

  // 演示 2：正七边形 —— 尝试后指出不可能
  function runHeptagonDemo() {
    setTool('compass');
    const steps = [
      () => setCaption('正七边形：先任取一个圆'),
      () => {
        const O = new Point(400, 300); O.id = genId('c');
        const added = addPoint(O, { color: '#1565c0', label: 'O' });
        pushStep({ nodes: [added.node, added.labelNode].filter(Boolean), addedPoints: [O] });
        compassCenter = O;
        setCaption('画一个圆');
      },
      () => {
        const c = new Circle(compassCenter, 150);
        const node = drawCir(c, { color: '#2e7d32' });
        addElement({ kind: 'circle', ref: c, node });
        pushStep({ nodes: [node], addedElement: elements[elements.length - 1] });
        setCaption('尝试作一个内接七边形');
      },
      () => {
        const O = new Point(400, 300); const R = 150;
        // 假装我们用尺规作一个内接七边形，但 cos(2π/7) 不是可构造数，所以这些顶点无法严格用尺规得到
        const fake = divideCirclePoints(new Circle(O, R), 7, -Math.PI / 2);
        const poly = drawPoly(fake, { fill: 'rgba(244,67,54,0.2)', color: '#c62828' });
        fake.forEach((p, i) => {
          const ap = addPoint(p, { color: '#c62828', label: '?' + (i + 1) });
          pushStep({ nodes: [ap.node, ap.labelNode].filter(Boolean), addedPoints: [p] });
        });
        pushStep({ nodes: [poly] });
        setCaption('红色多边形只是用三角函数"画"出来的近似 —— 真正尺规作不出');
      },
      () => {
        // 写上结论文本
        const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        t.setAttribute('x', 60); t.setAttribute('y', 560);
        t.setAttribute('font-size', '16'); t.setAttribute('fill', '#b71c1c');
        t.textContent = 'cos(2π/7) ≈ 0.62349，最小多项式 x³+x²-2x-1=0，次数 3 不是 2 的幂 → 不可构造';
        gOverlay.appendChild(t);
        setCaption('正七边形永远不可尺规作图（伽罗瓦理论证明）');
      },
    ];
    runAnimation(steps, () => setCaption('正七边形尝试演示完毕'));
  }

  // 键盘快捷键
  window.addEventListener('keydown', (e) => {
    // Ctrl+Z 撤销
    if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
      e.preventDefault(); popStep(); return;
    }
    if (animHandle && (e.key === ' ' || e.code === 'Space')) {
      e.preventDefault(); animStepForward(); return;
    }
    if (!animHandle) {
      if (e.key === 'r' || e.key === 'R') setTool('ruler');
      else if (e.key === 'c' || e.key === 'C') setTool('compass');
      else if (e.key === 's' || e.key === 'S') setTool('select');
    }
  });

  // 画布点击 / 双击
  svg.addEventListener('click', (evt) => {
    if (animHandle) return;
    const p = svgPt(evt);
    const near = nearest(p, 14) || p;
    if (currentTool === 'compass') handleCompassClick(near);
    else if (currentTool === 'ruler') handleRulerClick(near, p);
    else if (currentTool === 'select') handleSelectClick(near);
  });
  svg.addEventListener('dblclick', (evt) => {
    if (animHandle) return;
    if (currentTool === 'compass' && compassCenter) {
      const vb = svg.viewBox.baseVal;
      const far = new Point(vb.width / 2, vb.height / 2);
      finalizeCompass(far);
    }
  });

  // 画背景网格
  function drawGrid() {
    const g = document.getElementById('grid');
    const vb = svg.viewBox.baseVal;
    for (let x = 0; x <= vb.width; x += 50) {
      const ln = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      ln.setAttribute('x1', x); ln.setAttribute('y1', 0);
      ln.setAttribute('x2', x); ln.setAttribute('y2', vb.height);
      ln.setAttribute('stroke', '#eceff1'); ln.setAttribute('stroke-width', '1');
      g.appendChild(ln);
    }
    for (let y = 0; y <= vb.height; y += 50) {
      const ln = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      ln.setAttribute('x1', 0); ln.setAttribute('y1', y);
      ln.setAttribute('x2', vb.width); ln.setAttribute('y2', y);
      ln.setAttribute('stroke', '#eceff1'); ln.setAttribute('stroke-width', '1');
      g.appendChild(ln);
    }
  }
  drawGrid();

  // 暴露几个调试用函数
  window.appState = { points, elements, stepStack, setTool, clearBoard };
})();