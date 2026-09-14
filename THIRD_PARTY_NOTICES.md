# Third-Party Notices

This project vendors prompt/judge assets from the following third-party projects,
byte-verbatim, under their original licenses. Only prompt/data assets are vendored;
the attack loops are re-implemented against this project's own adapter contract
(see [`docs/technique-fidelity.md`](docs/technique-fidelity.md)). This project does not
import, depend on, or bundle the upstream Python packages.

Each vendored subtree keeps the upstream LICENSE and a PROVENANCE.md (source repo,
pinned commit, upstream file paths, per-file sha256, deviations).

## PAIR — `src/redteam/vendor/pair/`

- Project: **JailbreakingLLMs** (PAIR) — https://github.com/patrickrchao/JailbreakingLLMs
- Pinned commit: `6379ef705a0fc745530f7d895963510c021b496a`
- License: **MIT** — Copyright (c) 2023 PAIR Team (see `src/redteam/vendor/pair/LICENSE`)
- Paper: Chao, Robey, Dobriban, Hassani, Pappas, Wong. *Jailbreaking Black Box Large
  Language Models in Twenty Queries.* arXiv:2310.08419.
- Vendored: attacker system prompts (roleplaying / logical_appeal / authority_endorsement),
  the 1–10 judge system prompt, and the init / process-response message templates.

## Crescendo — `src/redteam/vendor/crescendo/`

- Project: **PyRIT** — https://github.com/Azure/PyRIT (the repo the Crescendo paper links;
  since archived, active development at https://github.com/microsoft/PyRIT)
- Pinned commit: `004d079c94c907539f3f99ae9c07558cb4ace18a`
- License: **MIT** — Copyright (c) Microsoft Corporation. (see `src/redteam/vendor/crescendo/LICENSE`)
- Paper: Russinovich, Salem, Eldan. *Great, Now Write an Article About That: The Crescendo
  Multi-Turn LLM Jailbreak Attack.* arXiv:2404.01833 (USENIX Security 2025).
- Vendored: the Crescendo attacker system prompt (variant 1), the refusal scorer prompts
  (default / strict), and the 0–100 task-achieved scale + red-teamer scale system prompt.
