# Remote acceptance

All project execution happens through a Git-external deployment profile. The operator must provide every field below; repository scripts do not define defaults:

- SSH profile or target;
- remote work directory;
- environment activation command;
- scheduler and queue;
- compute node;
- CPU, memory and GPU allocation;
- service port when the web workbench is launched.

Required sequence:

1. Validate the external profile and active environment.
2. Synchronize a clean Git archive into the configured remote work directory.
3. Install the project in the named environment.
4. Run `target-agent doctor`.
5. Run schema, policy and pytest checks on the scheduled compute node.
6. Run the real Step smoke test only after a rotated key is injected through an untracked secret source.
7. Run cold and cached AD, lung adenocarcinoma and UC cases.

The acceptance record may report Python/package versions, anonymous job IDs and scientific artifacts, but must not commit infrastructure identifiers or absolute paths.
