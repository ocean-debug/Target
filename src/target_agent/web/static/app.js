const byId = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const list = value => Array.isArray(value) ? value : [];
const number = value => Number.isFinite(Number(value)) ? Number(value) : 0;
const state = {bundle: null, replayTimer: null, activeRunId: null};

async function api(path, options) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `请求失败（${response.status}）`);
  return payload;
}

function toast(message, kind = 'info') {
  const node = byId('toast');
  node.textContent = message;
  node.className = `toast show ${kind}`;
  window.clearTimeout(node._timer);
  node._timer = window.setTimeout(() => { node.className = 'toast'; }, 3200);
}

function decisionClass(value) {
  return ({GO:'go', CONDITIONAL_GO:'conditional', INSUFFICIENT_EVIDENCE:'insufficient', NO_GO:'danger'}[value] || 'neutral');
}

function statusLabel(value) {
  return ({completed:'COMPLETED', completed_with_gaps:'COMPLETED WITH GAPS', needs_input:'NEEDS INPUT', refused:'REFUSED', failed:'FAILED'}[value] || String(value || 'RUNNING').toUpperCase());
}

function safeLink(uri) {
  return /^https:\/\//i.test(String(uri || '')) ? uri : '';
}

async function initialize() {
  const [capability, catalog] = await Promise.all([
    api('/api/capabilities'), api('/api/demo/cases')
  ]);
  const model = capability.settings?.step_configured ? `${capability.settings.step_model} 已配置` : '确定性通用工作流可用';
  const readyTools = list(capability.tools).length;
  byId('capability').textContent = `合同 ${capability.contract_version} · ${readyTools} 个工具 · ${model}`;
  renderCases(catalog.cases);
}

function renderCases(cases) {
  byId('demo-cases').innerHTML = list(cases).map(item => {
    const disabled = item.available ? '' : 'disabled';
    const marker = item.kind === 'main' ? '主Demo' : item.kind === 'boundary' ? '可靠性边界' : '泛化案例';
    return `<article class="case-card ${item.available ? '' : 'unavailable'} ${item.recommended ? 'recommended' : ''}">
      <div class="case-top"><span class="case-kind">${esc(marker)}</span><span class="availability">${item.available ? '已验证' : '当前无缓存'}</span></div>
      <h3>${esc(item.title)}</h3><b>${esc(item.subtitle)}</b><p>${esc(item.description)}</p>
      <button class="case-action" data-run-id="${esc(item.run_id || '')}" ${disabled}>${item.available ? '加载并回放' : '不可用'}</button>
    </article>`;
  }).join('');
  document.querySelectorAll('.case-action:not([disabled])').forEach(button => {
    button.addEventListener('click', () => loadRun(button.dataset.runId, true));
  });
}

async function loadRun(runId, autoplay = false) {
  stopReplay();
  byId('workspace').classList.remove('hidden');
  byId('run-status').textContent = 'LOADING';
  byId('run-title').textContent = '正在读取结构化运行结果…';
  byId('workspace').scrollIntoView({behavior:'smooth', block:'start'});
  try {
    const bundle = await api(`/api/runs/${encodeURIComponent(runId)}/bundle`);
    state.bundle = bundle;
    state.activeRunId = runId;
    renderBundle(bundle);
    if (autoplay) startReplay();
  } catch (error) {
    toast(error.message, 'error');
    byId('run-status').textContent = 'ERROR';
  }
}

function renderBundle(data) {
  const terminal = data.run?.terminal_status;
  byId('run-status').textContent = statusLabel(terminal);
  byId('run-status').className = `status-badge ${decisionClass(terminal === 'completed' ? 'GO' : terminal === 'completed_with_gaps' ? 'CONDITIONAL_GO' : 'NO_GO')}`;
  byId('run-title').textContent = data.question || '疾病靶点发现运行';
  byId('run-meta').textContent = `${data.run.run_id} · ${data.contract_version}`;
  byId('report-link').href = `/api/runs/${encodeURIComponent(data.run.run_id)}/report`;
  byId('research-question').textContent = data.question || '';
  renderContext(data.context);
  renderPlan(data.plan);
  renderTools(data.tools);
  renderDatasets(data.dataset_selection_trace);
  renderEvidenceMetrics(data.evidence);
  renderRanking(data.ranking);
  renderCards(data.target_cards, data.highlighted_targets);
  renderFindings(data.reviewer_findings);
  renderEvidence(data.evidence);
  resetTrace(data.trace);
}

function renderContext(context = {}) {
  const labels = {disease:'疾病', disease_subtype:'亚型', disease_stage:'阶段', organism:'物种', tissue:'组织', cell_type:'细胞类型', assay:'检测类型', desired_phenotype:'目标表型'};
  const entries = Object.entries(labels).filter(([key]) => context[key]);
  byId('context').innerHTML = entries.map(([key, label]) => `<div><span>${esc(label)}</span><b>${esc(context[key])}</b></div>`).join('') || '<p class="empty">当前运行未提供上下文。</p>';
}

function renderPlan(plan = {}) {
  const backend = plan.planner_backend || 'unknown';
  byId('planner-backend').textContent = plan.fallback_used ? `${backend} · fallback` : backend;
  byId('plan').innerHTML = list(plan.steps).map((step, index) => `<article class="plan-step">
    <span>${String(index + 1).padStart(2, '0')}</span><div><b>${esc(step.name || step.step_id)}</b><small>${esc(step.tool || 'Agent logic')}</small></div>
    <i>${list(step.dependencies).length ? `依赖 ${esc(step.dependencies.join(', '))}` : '起始步骤'}</i>
  </article>`).join('');
}

function renderTools(tools) {
  const covered = list(tools).filter(item => item.coverage_status === 'covered').length;
  byId('tool-summary').textContent = `${covered} / ${list(tools).length} covered`;
  byId('tools').innerHTML = list(tools).map(item => `<article class="tool-row">
    <span class="tool-dot ${item.status === 'success' ? 'ok' : item.status === 'out_of_scope' ? 'warn' : 'bad'}"></span>
    <div><b>${esc(item.tool_name)}</b><small>${esc(item.coverage_status)} · context ${number(item.context_match_score).toFixed(2)}</small></div>
    <em>${item.cached ? 'CACHE' : `${number(item.elapsed_ms)} ms`}</em>
  </article>`).join('') || '<p class="empty">暂无工具结果。</p>';
}

function renderDatasets(rows) {
  const values = list(rows);
  if (!values.length) { byId('datasets').innerHTML = '<p class="empty">当前运行没有GEO筛选记录。</p>'; return; }
  byId('datasets').innerHTML = values.slice(0, 8).map(item => {
    const accession = item.accession || item.candidate?.accession || 'dataset';
    const decision = item.decision || item.candidate?.eligibility || 'reviewed';
    const reason = item.reason || list(item.reasons || item.rejection_reasons || item.candidate?.rejection_reasons)[0] || '通过元数据资格审查';
    return `<article class="dataset-row"><span class="dataset-state ${decision === 'selected' || decision === 'eligible' ? 'selected' : ''}">${esc(decision)}</span><b>${esc(accession)}</b><small>${esc(reason)}</small></article>`;
  }).join('');
}

function renderEvidenceMetrics(evidence = {}) {
  const classes = evidence.claim_classes || {};
  const metrics = [['TOTAL', evidence.total, 'blue'], ['FACT', classes.FACT || 0, 'cyan'], ['OBSERVED', classes.OBSERVED || 0, 'green'], ['PREDICTED', classes.PREDICTED || 0, 'purple'], ['INFERRED', classes.INFERRED || 0, 'amber']];
  byId('evidence-metrics').innerHTML = metrics.map(([label, value, color]) => `<div class="metric ${color}"><strong>${esc(value)}</strong><span>${label}</span></div>`).join('');
}

function renderRanking(rows) {
  byId('ranking').innerHTML = list(rows).slice(0, 10).map(row => {
    const scores = row.scores || {};
    return `<tr><td>${esc(row.rank)}</td><td><b>${esc(row.gene)}</b></td><td><span class="decision ${decisionClass(row.decision)}">${esc(row.decision)}</span></td><td><strong>${number(scores.total).toFixed(2)}</strong></td><td>${number(scores.human_genetics).toFixed(2)}</td><td>${number(scores.disease_omics).toFixed(2)}</td><td>${number(scores.perturbation).toFixed(2)}</td><td>${number(scores.mechanism).toFixed(2)}</td><td>${number(scores.druggability).toFixed(2)}</td></tr>`;
  }).join('') || '<tr><td colspan="9" class="empty">没有可展示的排名。</td></tr>';
}

function renderCards(cards, highlighted) {
  const preferred = new Set(list(highlighted));
  const selected = list(cards).filter(card => preferred.has(card.gene_symbol));
  const display = (selected.length ? selected : list(cards)).slice(0, 3);
  byId('target-cards').innerHTML = display.map(card => {
    const plan = card.experiment_plan || {};
    const drugs = list(card.matched_drugs).slice(0, 4);
    const blockers = list(card.safety_blockers);
    const gaps = list(card.evidence_gaps);
    return `<article class="target-card">
      <div class="target-head"><div><span>#${esc(card.rank)}</span><h3>${esc(card.gene_symbol)}</h3></div><div><strong>${number(card.scores?.total).toFixed(2)}</strong><span class="decision ${decisionClass(card.decision)}">${esc(card.decision)}</span></div></div>
      <div class="card-block"><h4>证据缺口 / 阻断项</h4>${[...blockers, ...gaps].slice(0, 4).map(item => `<p class="risk">${esc(item)}</p>`).join('') || '<p class="muted">当前无结构化阻断项</p>'}</div>
      <div class="card-block"><h4>已知药物</h4><div class="drug-list">${drugs.map(drug => `<span>${esc(drug.prefName || drug.name || drug.drugId)}${drug.phase != null ? ` · Phase ${esc(drug.phase)}` : ''}</span>`).join('') || '<span>暂无结构化药物匹配</span>'}</div></div>
      <div class="card-block experiment"><h4>最高信息价值实验</h4><p>${esc(plan.highest_information_next_experiment || plan.hypothesis || '需要补充匹配上下文实验。')}</p><small>${esc(list(plan.stop_conditions)[0] || '根据预设终点和停止条件决策。')}</small></div>
    </article>`;
  }).join('');
}

function renderFindings(findings) {
  const values = list(findings);
  const major = values.filter(item => item.severity === 'major' || item.severity === 'blocking').length;
  byId('finding-summary').textContent = `${major} major / blocking`;
  byId('review').innerHTML = values.map(item => `<article class="finding ${esc(item.severity)}"><div><span>${esc(item.severity)}</span><b>${esc(item.category)}</b></div><p>${esc(item.message)}</p></article>`).join('') || '<div class="success-box">Reviewer未发现阻断性问题。</div>';
}

function renderEvidence(evidence = {}) {
  const items = list(evidence.items).slice(0, 12);
  byId('evidence-count').textContent = `${evidence.total || 0} EvidenceItems`;
  byId('evidence').innerHTML = items.map(item => {
    const uri = safeLink(item.source?.uri);
    const source = esc(item.source?.source_id || 'source');
    return `<article class="evidence-row"><div><span class="claim ${String(item.claim_class || '').toLowerCase()}">${esc(item.claim_class)}</span><b>${esc(item.gene_symbol || 'Context')}</b><em>${esc(item.stance)}</em></div><p>${esc(item.statement)}</p><small>${uri ? `<a href="${esc(uri)}" target="_blank" rel="noreferrer">${source}</a>` : source} · context ${number(item.context_match_score).toFixed(2)}</small></article>`;
  }).join('') || '<p class="empty">当前没有可展示证据。</p>';
}

function traceText(item) {
  const detail = item.detail || {};
  const tool = detail.tool_name || detail.tool || detail.step_id || '';
  const status = detail.status || detail.terminal_status || '';
  return [item.state, item.event_type, tool, status].filter(Boolean).join(' · ');
}

function resetTrace(trace) {
  stopReplay();
  byId('events').innerHTML = '<p class="empty">点击“回放Trace”展示Agent执行过程。</p>';
  byId('trace-progress').textContent = `0 / ${list(trace).length}`;
  byId('replay').textContent = '▶ 回放Trace';
}

function appendTrace(item, index, total) {
  if (index === 0) byId('events').innerHTML = '';
  const row = document.createElement('article');
  row.className = 'event-row';
  row.innerHTML = `<span>${String(index + 1).padStart(2, '0')}</span><div><b>${esc(traceText(item))}</b><small>${esc(item.created_at || '')}</small></div>`;
  byId('events').appendChild(row);
  byId('events').scrollTop = byId('events').scrollHeight;
  byId('trace-progress').textContent = `${index + 1} / ${total}`;
}

function startReplay() {
  if (!state.bundle) return;
  stopReplay();
  const trace = list(state.bundle.trace);
  let index = 0;
  byId('replay').textContent = '❚❚ 暂停回放';
  const tick = () => {
    if (index >= trace.length) { stopReplay(false); byId('replay').textContent = '↻ 重新回放'; return; }
    appendTrace(trace[index], index, trace.length);
    index += 1;
  };
  tick();
  state.replayTimer = window.setInterval(tick, 180);
}

function stopReplay(resetLabel = true) {
  if (state.replayTimer) window.clearInterval(state.replayTimer);
  state.replayTimer = null;
  if (resetLabel && byId('replay')) byId('replay').textContent = '▶ 回放Trace';
}

byId('replay').addEventListener('click', () => state.replayTimer ? stopReplay() : startReplay());

byId('run').addEventListener('click', async () => {
  const button = byId('run');
  const preferred = byId('accessions').value.split(',').map(value => value.trim()).filter(Boolean);
  const omicsModes = [];
  if (byId('mode-geo').checked) omicsModes.push('geo_bulk');
  if (byId('mode-census').checked) omicsModes.push('cellxgene');
  const payload = {
    contract_version: '2.2.0', task_type: 'disease_to_target',
    question: `Discover traceable targets for ${byId('disease').value}`,
    context: {contract_version:'2.2.0', disease:byId('disease').value, disease_subtype:byId('subtype').value || null, disease_stage:byId('stage').value || null, organism:byId('organism').value, tissue:byId('tissue').value || null, cell_type:byId('cell').value || null, assay:byId('assay').value || null, desired_phenotype:byId('phenotype').value || null},
    constraints: {contract_version:'2.2.0', dataset_selection:{contract_version:'2.2.0', preferred_dataset_accessions:preferred, excluded_dataset_accessions:[], omics_modes:omicsModes}},
    candidate_genes: [], omics_inputs: [], requested_outputs: ['ranked_targets','target_cards','report']
  };
  button.disabled = true; button.textContent = '正在提交…';
  try {
    const result = await api('/api/runs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    state.activeRunId = result.run_id;
    byId('workspace').classList.remove('hidden');
    byId('run-status').textContent = 'RUNNING';
    byId('run-title').textContent = payload.question;
    byId('run-meta').textContent = result.run_id;
    listenLive(result.run_id);
    byId('workspace').scrollIntoView({behavior:'smooth', block:'start'});
  } catch (error) { toast(error.message, 'error'); }
  finally { button.disabled = false; button.textContent = '启动Agent'; }
});

function listenLive(runId) {
  stopReplay();
  byId('events').innerHTML = '';
  let index = 0;
  const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`);
  source.onmessage = event => {
    const value = JSON.parse(event.data);
    appendTrace(value, index, Math.max(index + 1, 1));
    index += 1;
  };
  source.addEventListener('terminal', async event => {
    source.close();
    const status = JSON.parse(event.data);
    toast(`运行结束：${status.terminal_status}`, status.terminal_status === 'failed' ? 'error' : 'success');
    await loadRun(runId, false);
  });
  source.onerror = () => { source.close(); toast('Trace连接中断，请从运行记录重新加载。', 'error'); };
}

initialize().catch(error => {
  byId('capability').textContent = '系统能力读取失败';
  byId('demo-cases').innerHTML = `<article class="case-card unavailable"><h3>工作台初始化失败</h3><p>${esc(error.message)}</p></article>`;
});
