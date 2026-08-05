# Target product/runtime strategy

## Decision

Target should become the disease-target research domain service used by an Agent runtime, not a
second general scientific desktop. A useful product must keep a research question alive across
sessions, execute real scientific tools, preserve every decision and artifact, stop at explicit
human checkpoints and return a machine-readable evidence package. It does not need to rebuild a
file editor, terminal, persistent Python/R kernel, remote-compute manager or model-provider layer.

This boundary is informed by four independently implemented products:

- [SciForge](https://github.com/AGI4Sci/SciForge) separates a human/evidence control surface from
  Codex and Claude Code runtimes, and packages scientific domains behind stable contribution
  contracts.
- [OpenScience](https://github.com/synthetic-sciences/openscience) provides the general research
  harness, workspace, skills, tools, sessions and provider routing.
- [OpenAI4S](https://github.com/PKU-YuanGroup/OpenAI4S) separates a JSON control plane from a
  persistent Python/R science plane and treats completion as a structured runtime fact.
- [Wisp Science](https://github.com/xuzhougeng/wisp-science) models projects, execution contexts,
  runs, data assets and versioned artifacts independently of one chat or one machine.

No source code is copied from these projects. Their different licenses also make a clean protocol
boundary preferable to vendoring implementation code.

## Responsibility split

| Host runtime/workbench | Target domain service |
| --- | --- |
| Conversation, model routing and context compaction | Disease-target question and TaskSpec contracts |
| General filesystem, editor, terminal and code execution | Allowlisted genetics/omics/perturbation/drug/safety tools |
| Python/R kernels and remote compute contexts | Scientific eligibility, context and causality gates |
| User interface, notifications and long-running task UX | Project Plan, Evidence Store, Reviewer and Decision ledger |
| Generic MCP/skill/plugin discovery | Ranked targets, TargetCards and falsifiable experiments |
| Workspace sharing and collaboration | Digest-bound release package and explicit evidence gaps |

## Product lifecycle

```text
Question and biological context
  -> immutable Target project intake
  -> typed plan and human scope checkpoint
  -> real evidence acquisition and controlled analysis
  -> immutable artifacts and ordered event ledger
  -> evidence synthesis and Reviewer findings
  -> bounded repair or explicit request for input
  -> ranked targets, TargetCards and falsifiable experiments
  -> digest-bound expert release checkpoint
  -> report plus machine-readable evidence package
```

Conversation history is never the system of record. A host may disconnect after any step and use
the project id plus event cursor to continue later.

## Phase-one MCP product surface

The optional official-SDK stdio server exposes:

- `target_capabilities`
- `target_create_disease_project`
- `target_run_project`
- `target_get_project`
- `target_list_projects`
- `target_get_events`
- `target_get_domain_activities`
- `target_accept_checkpoint`
- `target_read_text_artifact`

The adapter calls `ResearchProjectService`; it does not invoke a second planner or maintain a
second store. Project and artifact resources are also addressable as `target://` resources.
Missing biological context is preserved rather than inferred, text artifacts are verified before
read-back and bounded before entering a model context.

## Remaining product work

The MCP adapter makes Target embeddable, but it does not by itself complete the full product moat.
The next runtime increments are:

1. Add append-only, digest-bound project plan revisions for explicitly authorized evidence
   supplementation. The current child Reviewer retry is real and observable, but it must not be
   misrepresented as project-level replan semantics.
2. Add evaluator-owned hidden target-ranking cases and independent expert adjudication.
3. Build real cross-disease alignment cases from reviewed project decisions instead of template
   expansion.
4. Add execution-context references for pre-staged omics/genetics assets without copying large
   data into the Agent store.
5. Add authenticated Streamable HTTP MCP only after a concrete multi-user deployment requires it.
