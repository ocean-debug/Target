const byId = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

fetch('/api/capabilities').then(response => response.json()).then(data => {
  const step = data.settings?.step_configured ? `${data.settings.step_model} 已配置` : 'Step 未配置，将使用确定性通用工作流';
  byId('capability').textContent = `合同 ${data.contract_version} · ${data.tools.length} 个工具 · ${step}`;
}).catch(() => { byId('capability').textContent = '能力信息暂不可用'; });

byId('run').addEventListener('click', async () => {
  const preferred = byId('accessions').value.split(',').map(value => value.trim()).filter(Boolean);
  const excluded = byId('excluded-accessions').value.split(',').map(value => value.trim()).filter(Boolean);
  const omicsModes = [];
  if (byId('mode-geo').checked) omicsModes.push('geo_bulk');
  if (byId('mode-census').checked) omicsModes.push('cellxgene');
  const payload = {
    contract_version: '2.1.0',
    task_type: 'disease_to_target',
    question: `Discover traceable targets for ${byId('disease').value}`,
    context: {
      contract_version: '2.1.0', disease: byId('disease').value,
      disease_subtype: byId('subtype').value || null, disease_stage: byId('stage').value || null,
      organism: byId('organism').value, tissue: byId('tissue').value || null,
      cell_type: byId('cell').value || null, assay: byId('assay').value || null,
      desired_phenotype: byId('phenotype').value || null
    },
    constraints: {
      contract_version: '2.1.0',
      dataset_selection: {
        contract_version: '2.1.0', preferred_dataset_accessions: preferred,
        excluded_dataset_accessions: excluded, omics_modes: omicsModes
      }
    },
    candidate_genes: [], omics_inputs: [], requested_outputs: ['ranked_targets', 'target_cards', 'report']
  };
  const response = await fetch('/api/runs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) { byId('events').textContent = JSON.stringify(data); return; }
  byId('run-id').textContent = data.run_id;
  listen(data.run_id);
});

function listen(runId) {
  byId('events').innerHTML = '';
  const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`);
  source.onmessage = event => {
    const value = JSON.parse(event.data);
    const div = document.createElement('div');
    div.className = 'event';
    div.textContent = `${value.state} · ${value.event_type} · ${JSON.stringify(value.detail)}`;
    byId('events').appendChild(div);
  };
  source.addEventListener('terminal', async () => { source.close(); await render(runId); });
}

async function render(runId) {
  const reportResponse = await fetch(`/api/runs/${encodeURIComponent(runId)}/artifacts/report.json`);
  if (!reportResponse.ok) { byId('ranking').textContent = '报告生成失败或尚未就绪'; return; }
  const report = await reportResponse.json();
  const rank = report.ranked_targets || [];
  byId('ranking').innerHTML = `<table><thead><tr><th>#</th><th>Target</th><th>Score</th><th>Decision</th><th>Gap</th></tr></thead><tbody>${rank.map(row => `<tr><td>${esc(row.rank)}</td><td><b>${esc(row.gene)}</b></td><td>${esc(row.scores.total)}</td><td><span class="badge">${esc(row.decision)}</span></td><td>${esc((row.evidence_gaps || [])[0] || '无')}</td></tr>`).join('')}</tbody></table>`;
  byId('review').innerHTML = (report.reviewer_findings || []).map(finding => `<div class="finding"><b>${esc(finding.severity)} · ${esc(finding.category)}</b><br>${esc(finding.message)}</div>`).join('') || '无 Reviewer finding';
  const graphResponse = await fetch(`/api/runs/${encodeURIComponent(runId)}/artifacts/mechanistic_evidence_graph.json`);
  if (graphResponse.ok) {
    const graph = await graphResponse.json();
    byId('evidence').textContent = `${graph.nodes.length} nodes · ${graph.edges.length} source-linked edges`;
  } else {
    byId('evidence').textContent = '当前运行没有生成机制图；请查看Reviewer证据缺口。';
  }
}
