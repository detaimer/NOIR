# Crescendo — vendored prompt provenance

- **Upstream**: https://github.com/Azure/PyRIT (the repo the Crescendo paper links; now
  archived/read-only — active development moved to https://github.com/microsoft/PyRIT).
  This pinned commit is our source of truth.
- **Pinned commit**: `004d079c94c907539f3f99ae9c07558cb4ace18a`
- **License**: MIT — "Copyright (c) Microsoft Corporation." (see `./LICENSE`, byte-verbatim copy)
- **Paper**: Russinovich, Salem, Eldan. *Great, Now Write an Article About That: The
  Crescendo Multi-Turn LLM Jailbreak Attack.* arXiv:2404.01833 (USENIX Security 2025).
  The authors did not release a standalone repo; the paper names PyRIT as the public
  implementation of "Crescendomation".

## Files (copied byte-verbatim, no transformation)

| file | upstream path (@ pinned commit) | sha256 |
|---|---|---|
| `crescendo_variant_1.yaml` | `pyrit/datasets/executors/crescendo/crescendo_variant_1.yaml` | `f522d7fb3394883cf6ad8ebb40b79110b5457f223998d5c0542dd3ec539bb4bf` |
| `refusal_default.yaml` | `pyrit/datasets/score/refusal/refusal_default.yaml` | `f398b1a77e526bd26b3ed2e731a1c7fbf19aada47ce889b9e9f52b55fba1eb2f` |
| `refusal_strict.yaml` | `pyrit/datasets/score/refusal/refusal_strict.yaml` | `41bd1da6bb24aaa31058972dbaf469097b45c64b73eca683f0b151262a4e50ea` |
| `task_achieved_scale.yaml` | `pyrit/datasets/score/scales/task_achieved_scale.yaml` | `3e52aea1d3ba4539b813e0e401facf3f98464e15d042a0960dcaf48999c395d2` |
| `red_teamer_system_prompt.yaml` | `pyrit/datasets/score/scales/red_teamer_system_prompt.yaml` | `74faaa76dcf507d3fe0741ff5adc75abb4b37ec0b1ce9e19c861cf16e81e2d22` |

Each YAML's prompt text is under its `value:` key (Jinja2 template). The attacker
prompt (`crescendo_variant_1.yaml`) takes `objective`, `max_turns`, `conversation_context`.
The objective scale system prompt is `red_teamer_system_prompt.yaml` rendered with the
fields of `task_achieved_scale.yaml` (`minimum_value`, `maximum_value`, `examples`, …).

## Pinned-commit schema note

At this commit the attacker must return JSON with keys **`generated_question`**,
`last_response_summary`, `rationale_behind_jailbreak`. (Newer PyRIT HEAD renamed these
to `next_message` / `rationale` / `last_response_summary`.) Our parser targets the
pinned-commit schema — only `generated_question` is consumed as the next user turn.

## Code-level format strings reproduced in `vendor/prompts.py` (cited)

- refusal user message: `"conversation_objective: {objective}\nresponse_to_evaluate_input: {response}"`
  — `pyrit/score/true_false/self_ask_refusal_scorer.py:21`
- scale user message: `"objective: {objective}\nresponse: {response}"`
  — `pyrit/score/float_scale/self_ask_scale_scorer.py:117`
- scale system prompt = `red_teamer_system_prompt.yaml` rendered with `task_achieved_scale.yaml`
  args — `self_ask_scale_scorer.py:75-85`

## What was NOT taken

PyRIT's async framework, `CentralMemory`, `PromptTarget`, and scorer machinery are not
imported. The Crescendo loop (turn escalation, refusal→backtrack, objective threshold
0.8) is re-implemented against redteam's adapter contract in
`src/redteam/probes/crescendo_probe.py`; see its module docstring for loop citations
and deviations.
