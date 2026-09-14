# 새 공격 기법(probe) 추가 (HOW)

설계 배경·정책은 [`docs/technique-fidelity.md`](../docs/technique-fidelity.md) 참조
(모든 기법은 `{attacker?, judge?, turns, transform}` 4-필드로 환원 → 단일 `Probe.run(behavior, ctx)`).

## 원칙 (요약)

- **논문 기억으로 재현하지 말 것.** 원저자가 공개한 **실제 프롬프트를 verbatim 으로 vendor** 하고,
  절차는 원본 코드를 보며 충실히 재구현한다. 출처·라이선스를 반드시 동반한다.
- import/pip-의존/submodule 금지(최소 의존성 유지).

## 절차

### 1. 프롬프트 vendoring (라이선스 확인 먼저)

- 원저자 레포의 **라이선스가 vendoring 을 허용**하는지 확인(MIT/Apache 등). 없으면(all-rights-reserved)
  vendor 하지 말고 사용자와 상의.
- 프롬프트/판정 기준을 `src/redteam/vendor/<technique>/` 에 **데이터 파일**(.txt/.yaml)로 byte-verbatim
  복사(공백·특수문자 보존). f-string 안의 프롬프트는 파서/`str.format`/jinja2 로 렌더하되, **렌더 결과가
  원본 함수 출력과 바이트 동일**함을 검증한다.
- 함께 둘 것: 원본 `LICENSE` 사본, `PROVENANCE.md`(repo URL·commit SHA·원본 파일 경로·파일별 sha256·
  DEVIATIONS). 최상위 [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) 에도 한 줄 추가.
- 로더/파서는 `vendor/prompts.py`·`vendor/parsing.py` 에 추가하고 `vendor/__init__.py` 에서 재노출한다.
  `vendor` 는 역할 패키지가 아니라 최하위이므로 `probes`·`detectors` 가 import 해도 레이어 위반이 아니다.

### 2. (필요 시) 기법 고유 judge/detector

- 원본이 자체 채점기(예: 1~10, refusal, 0~100 scale)를 쓰면 `src/redteam/detectors/<name>.py` 에 새
  `Detector` 로 추가하고 `detectors/__init__.py` 의 `DETECTORS` 에 등록. vendor 프롬프트/파서를 재사용한다.
- 참고 구현: `pair_judge.py`, `crescendo_refusal.py`, `crescendo_objective.py`.

### 3. probe 구현

- `tests/test_<technique>.py` 를 **먼저** 작성(결정론적 mock attacker/judge_client/target). basename 은
  repo 전역 유일.
- `src/redteam/probes/<technique>.py` 에 루프 재구현. 모듈 docstring 에 **원본 파일·커밋 인용 + DEVIATIONS**.
  - attacker/judge 는 `ctx.attacker`(Adapter)·`ctx.judge_client`(raw judge 엔드포인트)로 주입되며,
    이들 호출은 Fair-ASR 예산에 **차감되지 않는다**(예산은 `ctx.target`=BudgetedTarget 만).
  - `BudgetExceeded` 는 삼키지 말고 전파(runner 가 `Attempt.error`/`budget_exhausted` 로 흡수).
  - attacker/judge_client 부재 시 `AdapterError`.
  - 보고 성공은 primary(`ctx.judge`)로 판정하고, native judge 는 루프 구동에 쓴다(§docs 정책).
- `src/redteam/probes/__init__.py` 의 `PROBES` 에 zero-arg 팩토리로 등록. 기법별 파라미터는 run-config
  `techniques: [{<name>: {…}}]` 로 받아 `ctx.params` 로 전달된다(원본 기본값을 코드 기본값으로).

### 4. green 유지 + 게이트

- `python -m pytest -q` (체크포인트마다), `ruff check --fix . && ruff format .` (line-length 100).
- `.claude/skills/validate/scripts/gates.sh` (레이어 §6, basename/테스트짝 §7, deptry).
- 스캐폴딩/대량 파일은 Bash heredoc 으로 만들어 TDD 훅 데드락을 피하되 규율(테스트 먼저)은 유지.
