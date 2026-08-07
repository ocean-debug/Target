'use strict';

const $ = (id) => document.getElementById(id);
let currentProjectId = null;
let currentSnapshot = null;
let pollTimer = null;

async function api(path, options) {
  const response = await fetch(path, options);
  let payload = null;
  try { payload = await response.json(); } catch (_) { payload = null; }
  if (!response.ok) {
    throw new Error(payload && payload.error ? payload.error : `HTTP ${response.status}`);
  }
  return payload;
}

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function toast(message, kind = 'success') {
  const node = $('toast');
  node.textContent = message;
  node.className = `toast ${kind} show`;
  clearTimeout(node._timer);
  node._timer = setTimeout(() => node.classList.remove('show'), 3200);
}

function shortValue(value) {
  if (value === null || value === undefined) return '';
  let text = typeof value === 'string' ? value : JSON.stringify(value);
  return text.length > 120 ? text.slice(0, 117) + '…' : text;
}

function statusClass(status) {
  switch (status) {
    case 'completed': return 'go';
    case 'completed_with_gaps': return 'conditional';
    case 'needs_input': case 'waiting_review': return 'conditional';
    case 'failed': case 'blocked': case 'cancelled': return 'danger';
    case 'running': case 'planned': case 'pending': return 'blue';
    default: return '';
  }
}

function resultStatusClass(status) {
  switch (status) {
    case 'completed': return 'go';
    case 'completed_with_gaps': return 'conditional';
    case 'needs_input': return 'conditional';
    case 'failed': case 'blocked': case 'skipped': return 'danger';
    default: return '';
  }
}

function countAttempts(attempts) {
  const counts = new Map();
  for (const row of attempts || []) {
    counts.set(row.work_item_id, (counts.get(row.work_item_id) || 0) + 1);
  }
  return counts;
}

function lineageIds(snap, itemId) {
  const byId = new Map((snap.plan && snap.plan.items || []).map((item) => [item.item_id, item]));
  const seen = new Set();
  let current = byId.get(itemId);
  while (current && current.rerun_of_item_id && !seen.has(current.rerun_of_item_id)) {
    seen.add(current.rerun_of_item_id);
    current = byId.get(current.rerun_of_item_id);
  }
  return new Set([itemId, ...seen]);
}

// ---------- capability / project list ----------

async function refreshCapabilities() {
  try {
    const caps = await api('/api/capabilities');
    const backends = Object.entries(caps.analysis_backends || {})
      .filter(([, enabled]) => enabled).map(([name]) => name).join(', ') || '无';
    $('capability').textContent = `研究合同 ${caps.research_contract_version || '?'} · 后端 ${backends} · 技能库 ${(caps.skills && caps.skills.count) || 0}`;
  } catch (error) {
    $('capability').textContent = '系统能力不可用';
  }
}

async function loadProjects() {
  try {
    const data = await api('/api/projects');
    const rows = data.projects || [];
    const host = $('project-list');
    if (!rows.length) {
      host.innerHTML = '<p class="muted empty">还没有项目，先在右侧新建一个。</p>';
      return;
    }
    host.innerHTML = rows.map((row) => `
      <button class="project-card" data-id="${esc(row.project_id)}">
        <b>${esc(row.title)}</b>
        <small>${esc(row.project_id)} · ${esc(row.status)}</small>
      </button>`).join('');
    host.querySelectorAll('button[data-id]').forEach((button) => {
      button.addEventListener('click', () => selectProject(button.dataset.id));
    });
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function selectProject(projectId) {
  currentProjectId = projectId;
  $('workspace').classList.remove('hidden');
  $('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
  await pollProject();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollProject, 1500);
}

// ---------- create project ----------

function buildProjectSpec() {
  const value = (id) => $(id).value.trim();
  const disease = value('disease');
  const subtype = value('subtype');
  const tissue = value('tissue');
  const cell = value('cell');
  const stage = value('stage');
  const organism = value('organism');
  const assay = value('assay');
  const phenotype = value('phenotype');
  const accessions = value('accessions').split(',').map((row) => row.trim()).filter(Boolean);
  const context = {
    disease, subtype, tissue, cell_type: cell, stage, phenotype, organism, assay,
    preferred_dataset_accessions: accessions,
    literature_query: `${disease} mechanism and drug targets`,
    target_task_spec: {
      contract_version: '2.2.0',
      task_type: 'disease_to_target',
      question: `Which mechanisms and drug targets are supported by public evidence for ${disease}?`,
      context: {
        disease,
        disease_subtype: subtype || null,
        organism,
        tissue: tissue || null,
        cell_type: cell || null,
        disease_stage: stage || null,
        desired_phenotype: phenotype || null,
        assay: assay || null,
      },
      constraints: {
        public_data_only: true,
        dataset_selection: { preferred_dataset_accessions: accessions },
      },
    },
  };
  return {
    contract_version: '3.0.0',
    project_id: `project-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`,
    title: `${disease} target discovery`,
    domain: 'disease_target_discovery',
    goal: {
      question: `Which mechanisms and drug targets are supported by public evidence for ${disease}?`,
      success_criteria: ['Every released conclusion is traceable to a durable artifact.'],
      deliverables: ['A reviewed research report with explicit evidence gaps.'],
      constraints: ['Only public data and allowlisted tools may be used.'],
    },
    context,
    autonomy_mode: value('autonomy'),
    max_work_items: 12,
    max_replans: 2,
    max_forks: 4,
  };
}

async function createProject() {
  if (!$('disease').value.trim()) {
    toast('请填写疾病名称', 'error');
    return;
  }
  try {
    const created = await api('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildProjectSpec()),
    });
    toast('项目已创建并启动');
    await loadProjects();
    await selectProject(created.project_id);
  } catch (error) {
    toast(error.message, 'error');
  }
}

// ---------- snapshot rendering ----------

async function pollProject() {
  if (!currentProjectId) return;
  try {
    const snap = await api(`/api/projects/${currentProjectId}`);
    currentSnapshot = snap;
    renderSnapshot(snap);
    renderForkForm(snap);
  } catch (error) {
    toast(error.message, 'error');
  }
}

function renderSnapshot(snap) {
  const state = snap.state || {};
  const status = state.status || 'draft';
  const badge = $('run-status');
  badge.textContent = status.toUpperCase();
  badge.className = `status-badge ${statusClass(status)}`;
  $('run-title').textContent = snap.spec.title;
  let meta = `${snap.spec.project_id} · ${snap.spec.autonomy_mode} · 覆盖层 ${snap.plan_revisions.length}`;
  if (state.terminal_reason) meta += ` · ${state.terminal_reason}`;
  if (state.checkpoint_kind) meta += ` · 等待: ${state.checkpoint_kind}`;
  $('run-meta').textContent = meta;
  const exportLink = $('export-package');
  if (exportLink) {
    exportLink.href = '/api/projects/' + snap.spec.project_id + '/export';
    exportLink.classList.remove('hidden');
  }
  renderNextActions(snap);
  renderContext(snap);
  renderPlan(snap);
  renderResults(snap);
  renderBranches(snap);
  renderArtifacts(snap);
  renderEvents(snap);
  renderGraph(snap);
  renderFiles(snap);
}

function renderNextActions(snap) {
  const host = $('next-actions');
  host.innerHTML = '';
  const actions = snap.next_actions || [];
  if (!actions.length) {
    host.innerHTML = '<span class="muted">无待办审批</span>';
    return;
  }
  for (const action of actions) {
    if (action.action === 'decide_repair' || action.action === 'decide_fork') {
      const approve = document.createElement('button');
      approve.className = 'primary';
      approve.textContent = action.action === 'decide_repair' ? '批准修复' : '批准回退';
      approve.title = action.reason || '';
      approve.addEventListener('click', () => runAction(snap, action, true));
      host.appendChild(approve);
      const reject = document.createElement('button');
      reject.className = 'ghost';
      reject.textContent = action.action === 'decide_repair' ? '拒绝修复' : '拒绝回退';
      reject.addEventListener('click', () => runAction(snap, action, false));
      host.appendChild(reject);
      continue;
    }
    const button = document.createElement('button');
    button.className = 'primary';
    button.textContent = action.action === 'accept_checkpoint' ? '批准检查点' : '继续执行';
    button.title = action.reason || '';
    button.addEventListener('click', () => runAction(snap, action, true));
    host.appendChild(button);
  }
}

async function runAction(snap, action, approve) {
  const projectId = snap.spec.project_id;
  const actor = 'reviewer';
  try {
    if (action.action === 'accept_checkpoint') {
      await api(`/api/projects/${projectId}/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_id: action.target_id,
          actor,
          rationale: action.reason || 'Approved from the web workbench.',
        }),
      });
      toast('检查点已批准，正在继续执行');
    } else if (action.action === 'decide_repair') {
      await api(`/api/projects/${projectId}/repairs/${action.repair_request_id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approve,
          actor,
          rationale: approve ? 'Approve the bounded repair.' : 'Reject the bounded repair.',
          trigger_snapshot_digest: action.trigger_snapshot_digest,
        }),
      });
      toast(approve ? '修复已批准，正在继续' : '修复已拒绝');
    } else if (action.action === 'decide_fork') {
      await api(`/api/projects/${projectId}/forks/${action.branch_id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approve,
          actor,
          rationale: approve ? 'Approve the rollback branch.' : 'Reject the rollback branch.',
        }),
      });
      toast(approve ? '回退已批准，正在继续' : '回退已拒绝');
    } else if (action.action === 'run_project') {
      await api(`/api/projects/${projectId}/resume`, { method: 'POST' });
      toast('已排队继续执行');
    }
  } catch (error) {
    toast(error.message, 'error');
  }
  setTimeout(pollProject, 300);
}

function renderContext(snap) {
  const context = snap.spec.context || {};
  const keys = ['disease', 'subtype', 'tissue', 'cell_type', 'stage', 'organism', 'assay', 'phenotype'];
  const cells = keys
    .filter((key) => context[key])
    .map((key) => `<div><span>${esc(key)}</span><b>${esc(context[key])}</b></div>`)
    .join('');
  $('research-question').textContent = snap.spec.goal.question;
  $('context').innerHTML = cells || '<p class="muted">无上下文</p>';
  $('planner-backend').textContent = `${snap.plan ? snap.plan.planner_backend : '未规划'} · 预算 工作项 ${snap.spec.max_work_items} / 修复 ${snap.spec.max_replans} / 回退 ${snap.spec.max_forks}`;
}

function renderPlan(snap) {
  const activeIds = new Set(snap.active_work_item_ids || []);
  const resultById = new Map((snap.work_item_results || []).map((row) => [row.item_id, row]));
  const attemptsByItem = countAttempts(snap.work_attempts || []);
  const items = (snap.plan && snap.plan.items) || [];
  $('plan').innerHTML = items.map((item, index) => {
    const active = activeIds.has(item.item_id);
    const result = resultById.get(item.item_id);
    const attempts = attemptsByItem.get(item.item_id) || 0;
    const status = result ? result.status : (active ? 'pending' : 'superseded');
    const bind = item.rerun_of_item_id
      ? ` · 重跑 ${esc(item.rerun_of_item_id)}${item.fork_branch_id ? ' · fork' : ''}`
      : '';
    return `<article class="plan-step">
      <span>${String(index + 1).padStart(2, '0')}</span>
      <div>
        <b>${esc(item.title)}</b>
        <small>${esc(item.item_id)} · ${esc(item.module)}${bind}</small>
        <i>依赖: ${esc((item.dependencies || []).join(', ') || '无')}</i>
      </div>
      <span class="status-badge ${resultStatusClass(status)}">${esc(status)} · ${attempts} 次尝试</span>
    </article>`;
  }).join('');
}

function renderResults(snap) {
  const activeIds = new Set(snap.active_work_item_ids || []);
  const rows = (snap.work_item_results || []).filter((row) => activeIds.has(row.item_id));
  $('results').innerHTML = rows.length ? rows.map((row) => {
    const outputs = Object.entries(row.outputs || {})
      .map(([key, value]) => `${esc(key)}=${esc(shortValue(value))}`).join(' · ');
    const limitations = (row.limitations || []).map(esc).join('; ');
    return `<article class="result-row">
      <div class="result-head"><b>${esc(row.item_id)}</b><span class="status-badge ${resultStatusClass(row.status)}">${esc(row.status)}</span></div>
      <p>${esc(row.summary)}</p>
      ${outputs ? `<small class="mono">${outputs}</small>` : ''}
      ${row.error ? `<small class="danger-text">错误: ${esc(row.error)}</small>` : ''}
      ${limitations ? `<small class="muted">${limitations}</small>` : ''}
      ${row.fork_branch_id ? `<small class="muted">分支 ${esc(row.fork_branch_id)} · 覆盖 ${esc(row.supersedes_result_digest ? row.supersedes_result_digest.slice(0, 12) : '')}…</small>` : ''}
    </article>`;
  }).join('') : '<p class="muted empty">暂无结果</p>';
}

function renderBranches(snap) {
  const host = $('branches');
  const branches = snap.plan_branches || [];
  const directives = new Map((snap.fork_directives || []).map((row) => [row.fork_directive_id, row]));
  if (!branches.length) {
    host.innerHTML = '<p class="muted empty">尚无回退分支</p>';
    return;
  }
  host.innerHTML = `<div class="branch-table">${branches.map((branch) => {
    const directive = directives.get(branch.fork_directive_id);
    const pending = branch.status === 'proposed';
    const attempts = branch.rollback_to_attempt_id ? ` · 恢复 ${esc(branch.rollback_to_attempt_id)}` : '';
    return `<div class="branch-row">
      <div><b>${esc(branch.branch_id)}</b><small>${esc(branch.mode)} · 目标 ${esc(branch.fork_point_item_id)}${attempts} · ${esc(branch.status)}</small></div>
      <small class="muted">${esc(directive ? directive.rationale : '')}</small>
      <div class="branch-actions">${pending
        ? `<button data-branch="${esc(branch.branch_id)}" data-approve="true" class="primary">批准</button>
           <button data-branch="${esc(branch.branch_id)}" data-approve="false" class="ghost">拒绝</button>`
        : ''}</div>
    </div>`;
  }).join('')}</div>`;
  host.querySelectorAll('button[data-branch]').forEach((button) => {
    button.addEventListener('click', () => {
      decideFork(snap.spec.project_id, button.dataset.branch, button.dataset.approve === 'true');
    });
  });
}

async function decideFork(projectId, branchId, approve) {
  try {
    await api(`/api/projects/${projectId}/forks/${branchId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        approve,
        actor: 'reviewer',
        rationale: approve ? 'Approve the rollback branch.' : 'Reject the rollback branch.',
      }),
    });
    toast(approve ? '回退已批准，正在继续' : '回退已拒绝');
  } catch (error) {
    toast(error.message, 'error');
  }
  setTimeout(pollProject, 300);
}

function renderArtifacts(snap) {
  const rows = snap.artifacts || [];
  $('artifacts').innerHTML = rows.length ? rows.map((row) => `
    <div class="artifact-row">
      <div><b>${esc(row.logical_name)}</b><small>${esc(row.media_type)} · ${row.size_bytes} B · sha256 ${esc(row.sha256.slice(0, 12))}…</small></div>
      <a class="ghost link-button" href="/api/projects/${esc(snap.spec.project_id)}/artifacts/${esc(row.artifact_id)}">下载</a>
    </div>`).join('') : '<p class="muted empty">暂无产物</p>';
}

async function renderEvents(snap) {
  try {
    const page = await api(`/api/projects/${snap.spec.project_id}/events?after_sequence=0`);
    const rows = page.events || [];
    $('event-count').textContent = `${rows.length} 条`;
    const tail = rows.slice(-80).reverse();
    $('events').innerHTML = tail.map((row) => `
      <div class="event-row">
        <span>${row.sequence}</span>
        <div>
          <b>${esc(row.event_type)} · ${esc(row.state)}</b>
          ${row.work_item_id ? `<small>${esc(row.work_item_id)}</small>` : ''}
          <small>${esc(JSON.stringify(row.detail || {}))}</small>
        </div>
      </div>`).join('');
  } catch (error) {
    $('events').innerHTML = `<p class="muted">${esc(error.message)}</p>`;
  }
}

// ---------- fork form ----------

function renderForkForm(snap) {
  const activeIds = new Set(snap.active_work_item_ids || []);
  const resultById = new Map((snap.work_item_results || []).map((row) => [row.item_id, row]));
  const targets = [...resultById.keys()].filter((itemId) => {
    const row = resultById.get(itemId);
    return activeIds.has(itemId) && row.status in { completed: 1, completed_with_gaps: 1 };
  });
  $('fork-target').innerHTML = targets.length
    ? targets.map((itemId) => `<option value="${esc(itemId)}">${esc(itemId)}</option>`).join('')
    : '<option value="">暂无可回退工作项</option>';
  renderForkAttempts(snap);
}

function renderForkAttempts(snap) {
  const target = $('fork-target').value;
  const host = $('fork-attempt');
  if ($('fork-mode').value !== 'restore' || !target) {
    host.innerHTML = '<option value="">—</option>';
    return;
  }
  const allowed = lineageIds(snap, target);
  const rows = (snap.work_attempts || []).filter((row) =>
    (row.status === 'completed' || row.status === 'completed_with_gaps') && allowed.has(row.work_item_id)
  );
  host.innerHTML = rows.length
    ? rows.map((row) => `<option value="${esc(row.attempt_id)}">${esc(row.work_item_id)} #${row.attempt_number} · ${esc(row.attempt_id)}</option>`).join('')
    : '<option value="">无历史 attempt</option>';
}

async function proposeFork() {
  const target = $('fork-target').value;
  const mode = $('fork-mode').value;
  const rationale = $('fork-rationale').value.trim();
  if (!target || !rationale) {
    toast('请选择目标工作项并填写理由', 'error');
    return;
  }
  let inputOverrides = null;
  const raw = $('fork-overrides').value.trim();
  if (raw) {
    try { inputOverrides = JSON.parse(raw); }
    catch (_) { toast('输入覆盖必须是合法 JSON', 'error'); return; }
  }
  const body = {
    target_work_item_id: target,
    mode,
    rationale,
    actor: 'scientist',
  };
  if (mode === 'restore') body.rollback_to_attempt_id = $('fork-attempt').value || null;
  if (inputOverrides) body.input_overrides = inputOverrides;
  try {
    await api(`/api/projects/${currentProjectId}/forks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    toast('回退分支已发起');
    $('fork-rationale').value = '';
    $('fork-overrides').value = '';
  } catch (error) {
    toast(error.message, 'error');
  }
  setTimeout(pollProject, 300);
}

// ---------- init ----------

async function init() {
  refreshCapabilities();
  await loadProjects();
  $('refresh-projects').addEventListener('click', loadProjects);
  $('create').addEventListener('click', createProject);
  $('propose-fork').addEventListener('click', proposeFork);
  $('fork-mode').addEventListener('change', () => {
    if (currentSnapshot) renderForkAttempts(currentSnapshot);
  });
}

document.addEventListener('DOMContentLoaded', init);

// ---------- evidence graph / file preview ----------

async function renderGraph(snap) {
  const host = $('evidence-graph');
  const projectId = snap.spec.project_id;
  try {
    const graph = await api(`/api/projects/${projectId}/graph`);
    const nodes = graph.nodes || [];
    const edges = graph.edges || [];
    if (!nodes.length) {
      host.innerHTML = '<p class="muted">尚无计划节点（项目未规划）</p>';
      return;
    }
    host.innerHTML = renderSvgGraph(nodes, edges);
  } catch (error) {
    host.innerHTML = `<p class="muted">${esc(error.message)}</p>`;
  }
}

function renderSvgGraph(nodes, edges) {
  const work = nodes.filter((n) => n.kind === 'work_item');
  const artifactNodes = nodes.filter((n) => n.kind === 'artifact');
  const branchNodes = nodes.filter((n) => n.kind === 'branch');
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const deps = edges.filter((e) => e.kind === 'depends_on');
  const level = new Map();
  const compute = (id) => {
    if (level.has(id)) return level.get(id);
    const node = byId.get(id);
    let lv = 0;
    if (node && node.kind === 'work_item') {
      for (const e of deps) if (e.target === id) lv = Math.max(lv, compute(e.source) + 1);
    }
    level.set(id, lv);
    return lv;
  };
  work.forEach((n) => compute(n.id));
  const maxWorkLevel = Math.max(0, ...work.map((n) => level.get(n.id)));
  for (const n of artifactNodes) {
    const producer = edges.find((e) => e.target === n.id && e.kind === 'produces');
    level.set(n.id, producer ? (level.get(producer.source) || 0) + 1 : maxWorkLevel + 1);
  }
  const colW = 210, rowH = 64, nodeW = 180, nodeH = 42, padX = 24, padY = 20;
  const maxLevel = Math.max(0, ...nodes.map((n) => level.get(n.id) || 0));
  const cols = [];
  nodes.forEach((n) => {
    const lv = level.get(n.id) || maxLevel;
    (cols[lv] = cols[lv] || []).push(n);
  });
  const maxRows = Math.max(1, ...cols.map((c) => c.length));
  const width = (maxLevel + 1) * colW + padX * 2;
  const height = maxRows * rowH + padY * 2 + 34;
  const pos = new Map();
  cols.forEach((col, lv) => {
    col.forEach((n, idx) => {
      const cy = ((maxRows - col.length) / 2) * rowH + idx * rowH + padY;
      pos.set(n.id, { x: padX + lv * colW, y: cy });
    });
  });
  const statusColor = (s) => ({
    completed: '#42d392', completed_with_gaps: '#ffbf69', running: '#5da9ff',
    pending: '#98abc3', failed: '#ff6b7a', blocked: '#ff6b7a',
  }[s] || '#98abc3');
  const edgeSvg = edges.map((e) => {
    const a = pos.get(e.source), b = pos.get(e.target);
    if (!a || !b) return '';
    const x1 = a.x + nodeW, y1 = a.y + nodeH / 2;
    const x2 = b.x, y2 = b.y + nodeH / 2;
    const color = e.kind === 'produces' ? '#8ec5ff' : '#5f7ea0';
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="1.4" marker-end="url(#arrow)"/>`;
  }).join('');
  const nodeSvg = nodes.map((n) => {
    const p = pos.get(n.id);
    if (!p) return '';
    const isWork = n.kind === 'work_item';
    const fill = isWork ? statusColor(n.status) : '#2b6f9e';
    const stroke = n.active ? '#eef6ff' : 'none';
    const title = isWork ? (n.module + ' · ' + n.status) : (n.media_type + ' · ' + n.sha256_short);
    const label = n.label.length > 26 ? n.label.slice(0, 25) + '…' : n.label;
    return `<g transform="translate(${p.x},${p.y})">
      <rect width="${nodeW}" height="${nodeH}" rx="8" fill="${fill}" stroke="${stroke}" stroke-width="1.5" opacity="0.92"/>
      <text x="${nodeW / 2}" y="18" text-anchor="middle" fill="#06121f" font-size="11" font-weight="700">${esc(label)}</text>
      <text x="${nodeW / 2}" y="33" text-anchor="middle" fill="#0b1b2e" font-size="9">${esc(title)}</text>
    </g>`;
  }).join('');
  const legend = `<div class="graph-legend">工作项：<span class="dot" style="background:#42d392"></span>完成
    <span class="dot" style="background:#ffbf69"></span>完成有缺口 <span class="dot" style="background:#5da9ff"></span>运行
    <span class="dot" style="background:#98abc3"></span>待处理 <span class="dot" style="background:#ff6b7a"></span>失败/阻断
    · 产物：<span class="dot" style="background:#2b6f9e"></span>artifact · 白框=活跃</div>`;
  const branchNote = branchNodes.length
    ? `<p class="muted">回退分支：${branchNodes.map((b) => esc(b.label) + ' (' + esc(b.mode) + '/' + esc(b.status) + ')').join('，')}</p>`
    : '';
  return `${legend}${branchNote}<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%">
    <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#5f7ea0"/></marker></defs>
    ${edgeSvg}${nodeSvg}</svg>`;
}

async function renderFiles(snap) {
  const host = $('file-tree');
  const projectId = snap.spec.project_id;
  try {
    const page = await api(`/api/projects/${projectId}/files`);
    const rows = page.files || [];
    if (!rows.length) { host.innerHTML = '<p class="muted">项目目录为空</p>'; return; }
    host.innerHTML = rows.map((row) => {
      const icon = (row.media_type.startsWith('text/') || row.media_type === 'application/json') ? '📄' : '📦';
      return `<button class="file-row" data-path="${esc(row.path)}">${icon} <span>${esc(row.path)}</span><small>${row.size_bytes} B</small></button>`;
    }).join('');
    host.querySelectorAll('button.file-row').forEach((button) => {
      button.addEventListener('click', () => previewFile(projectId, button.dataset.path));
    });
  } catch (error) {
    host.innerHTML = `<p class="muted">${esc(error.message)}</p>`;
  }
}

async function previewFile(projectId, path) {
  const host = $('file-preview');
  try {
    const page = await api(`/api/projects/${projectId}/files/preview?path=${encodeURIComponent(path)}`);
    if (page.reason === 'binary_file') {
      host.innerHTML = `<p class="muted">二进制文件，不支持在线预览：${esc(path)}</p>`;
      return;
    }
    const head = page.truncated ? '<span class="muted">已截断</span>' : '';
    host.innerHTML = `<div class="subhead"><h3>${esc(path)}</h3>${head}</div><pre class="file-preview-content">${esc(page.content)}</pre>`;
  } catch (error) {
    host.innerHTML = `<p class="muted">${esc(error.message)}</p>`;
  }
}

