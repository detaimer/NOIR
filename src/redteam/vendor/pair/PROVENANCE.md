# PAIR — vendored prompt provenance

- **Upstream**: https://github.com/patrickrchao/JailbreakingLLMs
- **Pinned commit**: `6379ef705a0fc745530f7d895963510c021b496a` (default branch `main`)
- **License**: MIT — "Copyright (c) 2023 PAIR Team" (see `./LICENSE`, byte-verbatim copy)
- **Paper**: Chao, Robey, Dobriban, Hassani, Pappas, Wong. *Jailbreaking Black Box Large
  Language Models in Twenty Queries.* arXiv:2310.08419.
- **Version note**: this is the maintained HEAD 3-strategy set
  (`get_attacker_system_prompts`), not the 2023 single-prompt v1. The `logical_appeal`
  and `authority_endorsement` few-shot examples are credited by upstream to
  Zeng et al. (arXiv:2401.06373).

## Files

| file | upstream origin (@ pinned commit) | sha256 |
|---|---|---|
| `roleplaying.txt` | `system_prompts.py` → `roleplaying_prompt` | `aaf1642cd24a07afd13df970252ccf1eee387240cee202bd0af586bafa030b99` |
| `logical_appeal.txt` | `system_prompts.py` → `logical_appeal_prompt` | `96c861418874c2064eb636758c08718a531f301801a5310002f72c8086a37539` |
| `authority_endorsement.txt` | `system_prompts.py` → `authority_endorsement_prompt` | `33034661741af82b7283f4a6ca8b2334a2c51602716cf54db56c4f21bbc6fbd9` |
| `judge_system.txt` | `system_prompts.py` → `get_judge_system_prompt` | `9be96058a93c83658c571dad93ae29d7c96b3f06c92a4ecbf1542cac0670b8aa` |
| `init_msg.txt` | `common.py` → `get_init_msg` | `6cc3b298c6702eb049724d03eb64d5e8184b10a9e3c319e858ac91bad864bb06` |
| `process_target_response.txt` | `common.py` → `process_target_response` | `d1d8b2449163433b1ff54016d9a6fb23b22c8b267e3866d31fa2c84d14ac4294` |

## Transformation (the only change from upstream bytes)

Upstream stores these prompts as Python **f-string function bodies**. Each file here
is the same string reconstructed as a `str.format` template: literal braces doubled
(`{{ }}`), interpolation points kept as named fields. The Python parser decodes escape
sequences, so `\n` in `process_target_response` is a real newline here. Load-bearing
trailing spaces and the em-dash (`—`) in `judge_system.txt` are preserved.

Placeholders per file:
- `roleplaying.txt`, `logical_appeal.txt`, `authority_endorsement.txt`: `{goal}`, `{target_str}`
- `judge_system.txt`: `{goal}`
- `init_msg.txt`: `{goal}`, `{target}`
- `process_target_response.txt`: `{goal}`, `{score}`, `{target_response}`

**Fidelity guarantee**: extraction asserted `template.format(...) == <upstream_fn>(...)`
byte-for-byte, and `tests/test_prompts.py` pins each file's sha256 above.

## What was NOT taken

The upstream loop (`main.py`, `conversers.py`), FastChat/LiteLLM/JailbreakBench
plumbing, and the model-seeding trick are re-implemented against redteam's adapter
contract in `src/redteam/probes/pair_probe.py`; see its module docstring for the
loop citations and deviations. `extract_json` / rating parsing are re-expressed in
`src/redteam/vendor/parsing.py` with a fidelity test.
