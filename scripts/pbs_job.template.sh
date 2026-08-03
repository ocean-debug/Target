#!/usr/bin/env bash
# Parameterized PBS body. Scheduler resources and environment activation are
# supplied by an external deployment profile; this file intentionally has no
# host, queue, node, core, GPU, path, or environment defaults.
set -euo pipefail

: "${TARGET_AGENT_PROJECT_DIR:?set TARGET_AGENT_PROJECT_DIR}"
: "${TARGET_AGENT_ACTIVATE:?set TARGET_AGENT_ACTIVATE}"
: "${TARGET_AGENT_COMMAND:?set TARGET_AGENT_COMMAND}"

cd "$TARGET_AGENT_PROJECT_DIR"
bash -lc "$TARGET_AGENT_ACTIVATE && $TARGET_AGENT_COMMAND"
