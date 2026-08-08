# Five-minute workbench demo

The web workbench has two explicit modes:

- **Acceptance-checked stored replay** reads an existing stored run and never calls Step or a public database. Acceptance covers Trace and artifact integrity, not biological truth.
- **Live run** submits a new `TaskSpec 2.2.0`, streams SSE Trace events and may use configured external services.

Never describe replay as a live run. The header, run identifier and Planner backend remain visible so the audience can distinguish them.

## Start and verify

Infrastructure values belong in the external deployment profile. Supply the port, run directory and cache directory explicitly:

```bash
target-agent doctor
target-agent serve \
  --host 0.0.0.0 \
  --port "$TARGET_AGENT_PORT" \
  --runs-dir "$TARGET_AGENT_RUN_DIR" \
  --cache-dir "$TARGET_AGENT_CACHE_DIR"
```

When the service runs on a compute node, create a local tunnel using the deployment profile rather than recording the host in Git:

```bash
ssh -N -L 8888:<compute-node>:<service-port> <ssh-profile>
```

Open `http://localhost:8888` and verify:

```bash
curl -fsS http://localhost:8888/healthz
curl -fsS http://localhost:8888/api/demo/cases
```

The health response must report the service, Evidence Store, cache and executor as available. The demo catalog should mark the required stored cases as `available`.

## Presentation path

### 0:00–0:35 — Product position

Explain that the product is a research Agent, not a gene-list generator. Point to the six-stage pipeline and the statement that the frontend renders only stored backend evidence.

### 0:35–1:15 — Stable LUAD replay

Click **肺腺癌靶点发现 → 加载并回放**. State clearly that this is an acceptance-checked stored Trace replay. Show:

- the typed 12-step Plan;
- the actual Planner backend used by that stored run;
- 33 Trace events and nine covered tools;
- dynamic GEO screening, with GSE310170 selected and rejected datasets retaining their reasons.

### 1:15–2:20 — Evidence and ranking

Scroll to evidence fusion and the top-10 ranking. Explain:

- `FACT`, `OBSERVED`, `PREDICTED` and `INFERRED` remain separate;
- a priority score is not a clinical success probability;
- BIRC3 and CEMIP2 have omics-only support and remain `INSUFFICIENT_EVIDENCE`;
- EGFR is `CONDITIONAL_GO`, not unconditional `GO`.

### 2:20–3:30 — TargetCard and falsifiable experiment

Show the EGFR, TP63 and NRG1 cards. For EGFR, point out the retained safety liabilities, known drugs, matched-context perturbation gap and highest-information experiment. Explain what positive, negative and contradictory results would imply.

### 3:30–4:20 — Reliable degradation

Click **UC可靠降级 → 加载并回放**. Show `COMPLETED WITH GAPS`, `not_covered` and `context_mismatch`. Explain that the Agent continues available aggregate associations, literature and drug evidence while refusing to fabricate strict genetics or formal omics evidence without controlled inputs.

### 4:20–5:00 — Generalization and optional live action

Point to the Alzheimer disease stored case as cross-disease evidence. Expand **启动新的真实运行** only if network time permits. A live run is optional; the acceptance-checked replay demonstrates the auditable product path but is not a biological validation result.

## Recovery during a presentation

- If a live run is slow, return to an acceptance-checked stored case; do not wait on public databases.
- If Step is unavailable, the generic deterministic workflow remains available and the Planner backend is shown.
- If a backend capability is missing, use the capability pill and Reviewer findings to explain the gap.
- If the service cannot be reached, use the separately generated offline HTML/video package. Do not present it as a live backend session.
