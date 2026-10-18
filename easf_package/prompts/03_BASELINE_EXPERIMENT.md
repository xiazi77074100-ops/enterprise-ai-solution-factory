# COPY TO AN ISOLATED CODEX OR CC SESSION — BASELINE EXPERIMENT

You are conducting a controlled comparison of expert AI Coding alone vs AI Coding plus EASF. Follow `docs/03_ACCEPTANCE_AND_EXPERIMENT.md` and `docs/07_DATA_AND_EVAL.md`.

First produce a pre-registration document (scope, frozen requirements, scoring, order, time log template, cost ledger, holdout hashes) for human approval. DO NOT run the experiment until approved. Baseline may use standard open-source libraries and an ordinary component repository, but MUST NOT use Factory-specific reusable capabilities, Catalog, Composer or Evaluation code. Both arms use Claude Code/Codex and comparable environment/model budget. Record developer prompting/review/integration/test/debug time and AI cost. Protect holdout labels from both arms. Document any unavoidable learning bias, differences in operator skill, or order effects. Use at least one changed-requirement test to assess reuse rather than duplicated implementation.

Output after real runs: raw logs, per-scenario metrics, severity failures, absolute time/cost, comparison, break-even sensitivity, threats to validity and go/no-go. No fabricated savings. If Factory underperforms, explicitly recommend component-library/playbook pivot where justified.
