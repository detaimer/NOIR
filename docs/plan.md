# redteam — 기능 구현 계획 (pluggable red-team MVP)

> 이 문서 = 기능 MVP 구현 계획 (git 관리). 로드맵 연결: `docs/roadmap.md`.
> 설계 근거: `docs/architecture.md`, `docs/evaluation.md`. 작업 규칙: `references/`, `.claude/rules/tdd.md`.

## Context (왜 지금 이걸 하나)

`~/Projects/RedTeaming` 의 **범용 블랙박스 LLM red-teaming 도구** `redteam`(CLI `rt`). 스캐폴딩
(역할별 폴더·TDD 훅·`rt --version`)은 완료(3 tests green). 이제 그 위에 **실제 기능**을 얹는다.

도구 정체성(인터뷰로 확정): **garak / PyRIT 류의 pluggable 블랙박스 red-team 프레임워크 — 다만 더
세련되고 커스터마이즈 가능하게.** 공격 기법·타깃·판정기·지표를 전부 **꽂아 끼우는(pluggable)** 것이 핵심
성격. 포괄적 harmful 커버가 주력이고, **OT/ICS(정수장 등 중대 인프라)는 하드 특화가 아니라 태그로
표현되는 1급 "지원 도메인"** 이다 (OT 전용 벤치마크가 없어 하드 특화는 실익이 적다는 판단). 향후
실서비스 API 점검 도구로 활용.

전제: 전역 TDD 훅 활성 — impl `<name>.py` 는 `tests/test_<name>.py` 선행 필요, 매 `.py` 쓰기 후 전체
pytest green 유지, **모듈 basename repo 전역 유일**, 비결정(LLM/네트워크) 로직은 ABC/Protocol 뒤 + fake로
테스트, 실 API 호출은 marker로 기본 제외.

## Goal (Definition of Done)

`rt run -c run.yaml` 한 번으로: 지정한 타깃에 (정적/PAIR/Crescendo) 기법을 적용 → 응답 수집 → 3개
judge(RefusalMatch·LlamaGuard·StrongREJECT)로 판정 → `out/runs/<ts>/` 에 **JSONL 로그 + summary.json +
config 스냅샷** 저장 + **터미널 요약표** 출력 + **HTML 리포트** 생성. 상업 API·로컬 서버·Manual(사람 복붙)
타깃 모두 지원. Fair-ASR(동일 타깃-호출 예산 B) 비교 가능. 전 구간 fake로 결정론적 테스트 green,
`ruff`/`import-linter`/`deptry` clean.

## 확정된 설계 결정 (인터뷰 A–F)

- **A. behaviors(시드 유해요청)**: pluggable 소스. 내장 소규모 팩(~15, 오프라인) + `jbb`/`harmbench` 로더.
  `--behaviors builtin|jbb|harmbench|<path>`. 각 behavior 는 `domain·subcat·tags(MITRE ATT&CK/ATT&CK-ICS/
  ATLAS/OWASP LLM Top10 crosswalk)` 메타 보유. OT/ICS = `domain="ot_ics"` + `attack-ics:*` 태그(특별취급 X).
- **B. detectors(judge)**: pluggable, 구조화 출력 `{success, score?, categories, judge_name}`. **3개 탑재** —
  `RefusalMatch`(이진·무료·무모델), `LlamaGuard`(이진 safe/unsafe + 카테고리; HTTP 어댑터 재사용하는 또다른
  엔드포인트), `StrongREJECT`(등급 0~1 = (1−refusal)×(구체성+설득력)/2; judge LLM).
- **C. techniques(probe)**: **세 tier 전부 구현** — 정적 one-shot 3~4종(past-tense·base64·FlipAttack·
  many-shot) + PAIR(반복형, attacker LLM) + Crescendo(멀티턴). 인터페이스는 모든 tier 수용.
- **D. adapters + eval**: HTTP(OpenAI 호환) 하나로 상업(Claude/OpenAI/Grok)+로컬(Ollama/vLLM/SGLang/
  LM Studio/TGI) 커버(설정만 다름). **Manual 어댑터**(멀티턴 포함). **Fair-ASR**(동일 예산 B 비교).
  Multimodal 은 v0.2.
- **E. run 설정**: **YAML run-config = 원천, CLI 오버라이드.** target/attacker/judge 엔드포인트 각각 독립
  설정(**target ≠ judge** 강제), behaviors·techniques·budget·out_dir 포함.
- **F. 출력**: 셋 다 — 시도별 JSONL + summary.json + config 스냅샷(`out/runs/<ts>/`), 터미널 요약표, **HTML
  리포트(정보설계의 중심, v1 초안 → 사용자 피드백으로 반복)**.
- **평가 철학**: judge/지표 모두 pluggable. **ASR은 기본 헤드라인이지 유일 축이 아님** — reporting이 이진
  judge→ASR, 등급 judge→평균점수, 카테고리/도메인/taxonomy별 분해로 집계.

## 핵심 아키텍처

**설계 원칙 2가지 (레이어 계약을 지키는 근간):**
1. **의존성 주입(DI), 레이어 내부 import 금지.** 역할 패키지(probes/adapters/detectors/reporting/
   behaviors)는 **`core` 에만** 의존. probe 는 구체 adapter/detector 를 import 하지 않고 **run 시 `core` ABC
   인스턴스로 주입받음**. LLM judge 는 이미 만들어진 judge client(`Adapter`)를 생성자로 받음. **wiring 은
   runner/registry 만.** → 역할 패키지가 진짜 독립 형제가 되고 fake 테스트가 쉬움.
2. **Fair-ASR 예산은 wrapper 가 집계**(probe 자가보고 X). runner 가 실제 타깃을 `BudgetedTarget(limit=B)`
   로 감싸 probe 에 주입 → 매 `chat/generate` 가 카운트, 상한서 `BudgetExceeded`. 세 tier 모두 자동·균일.

**인터페이스 (`core/interfaces.py` 한 파일 — `base.py` 3개 대신 basename 유일성 확보):**
```python
Adapter(Protocol):   name; chat(messages)->str; generate(prompt, system=None)->str   # stateless, 히스토리는 caller
Detector(ABC):       name; judge(behavior, prompt, response, conversation=None)->DetectionResult
ProbeContext:        target: Adapter(=BudgetedTarget); judge: Detector(primary); attacker: Adapter|None;
                     max_turns; max_attempts; rng
Probe(ABC):          name; uses_attacker; uses_judge; default_turns; run(behavior, ctx)->Attempt
```
**4-필드 모델이 한 `run()` 계약으로 수렴:** 정적=`transform(prompt)`→target 1회→judge (attacker✘,turns=1);
PAIR=attacker가 judge 피드백 보며 프롬프트 재작성 ×N(각 single-turn, target N회); Crescendo=`conv` 유지하며
attacker가 매 턴 escalating 메시지 생성→`target.chat(conv)` ×turns. 시그니처·예산기전 동일, 내부 루프만 다름.

**core 레코드(`core/records.py`)**: `Message/Role, Behavior(id,prompt,domain,subcat,tags,source), Turn,
DetectionResult(success,judge_name,score?,categories,rationale?), Attempt(behavior_id,technique,turns,
final_prompt,final_response,detections[모든 judge],success[primary],target_calls[Fair-ASR 단위],attacker_calls,
judge_calls,budget_exhausted,error?)`. `core/budget.py`=CallCounter/BudgetedTarget. `core/errors.py`=
ConfigError/BudgetExceeded/AdapterError/UnknownComponent. `core/config_schema.py`=RunConfig.from_dict(순수,
target≠judge 검증).

**Registry(`registry.py`)**: 역할 패키지의 name→factory dict 를 aggregate(role `__init__` 가 자기 dict 소유;
registry 가 roles 를 import, 역방향 X). `get_probe/adapter/detector`, unknown→`UnknownComponent`(유효목록 제시),
`available()`.

**Runner(`runner.py`)**: config 로드→behaviors 로드→엔드포인트/판정기/probe 빌드(detectors[0]=primary)→
technique×behavior 루프(behavior마다 새 `BudgetedTarget`)→`probe.run`(try/except로 예산초과·어댑터오류를
Attempt.error 로)→**나머지 judge를 최종응답에 채점**→`target_calls=counter.count` 기록→collect→
`aggregate.summarize`→JSONL/터미널/HTML 출력. MVP는 순차 실행.

**HTML 리포트 v1 섹션(8)**: ①메타/헤더(+재현 config 링크) ②Executive(전체 ASR·총시도·**취약 도메인 top3**)
③**도메인/카테고리 위험도 히트맵**(강조 파트) ④기법 효과(ASR@B/평균calls/StrongREJECT평균) ⑤taxonomy
커버리지 ⑥드릴다운(behavior별 표 + 성공 transcript + judge 3개 판정) ⑦judge 합치도 ⑧부록. v1 → 피드백 반복.

**의존성(최소)**: `openai>=1.40`(HTTP 클라이언트 — **LiteLLM 대신 얇은 OpenAI SDK, LiteLLM은 v0.2**; 모두
OpenAI 호환이라 base_url/key/model 로 충분, ABC 뒤라 교체 1파일), `pyyaml>=6`(safe_load), `jinja2>=3.1`
(HTML). `rich` 미채택(터미널표는 순수 ASCII, 스냅샷 테스트 쉬움). pytest marker `live` 추가 +
`addopts="-q -m 'not live'"`.

## Requirements

- 세 tier(정적·PAIR·Crescendo) 모두 단일 `Probe.run` 계약으로 동작, fake로 결정론 테스트.
- HTTP 어댑터가 상업+로컬을 설정만으로 커버; Manual 어댑터가 멀티턴 포함 동작(input/output 주입으로 테스트).
- 3개 detector 가 구조화 결과 반환; LlamaGuard/StrongREJECT 는 주입된 judge client 로 동작(네트워크 X 테스트).
- Fair-ASR: 동일 B에서 기법별 ASR@B + 평균 타깃호출 + efficiency(성공/총호출) 집계·표시.
- YAML run-config + CLI 오버라이드; target≠judge 강제; 비밀키는 `api_key_env`(인라인 금지), config 스냅샷 redact.
- 출력 3종(JSONL+summary+snapshot / 터미널표 / HTML) `out/runs/<ts>/`.
- 레이어 계약 import-linter 로 강제; deptry clean.

## Non-goals (v0.2+)

TAP/PAP/GOAT/ActorAttack/X-Teaming; Multimodal(FigStep 등); Wilson-CI 신뢰구간; 데이터셋 auto-download;
병렬/async 실행; cost tracking; LiteLLM; judge 앙상블/투표; 추가 transform(rot13/leetspeak/DeepInception);
CyberSecEval식 별도 task-score 축; OT 전용 대량 데이터셋 저작(도구 완성 후 별도 과제).

## Tasks (TDD 순서, 의존성 순)

> **훅 데드락 브레이커(모든 신규 모듈 첫 테스트에 적용)**: `test_<name>.py` 상단에서
> `mod = pytest.importorskip("redteam...<name>")`. impl 전엔 SKIP(=green)이라 테스트 파일 쓰기 허용, impl
> 후엔 실제 import 되어 assert 수행. 각 task: 테스트 먼저 → impl → `pytest -q` green + `ruff` clean.

**M0 설정(.py 아님, 훅 무관)**
1. [x] `pyproject`에 `openai/pyyaml/jinja2` 추가 + `live` marker + `addopts="-q -m 'not live'"` — 완료: `pip install -e '.[dev]'` OK, 기존 3 tests green.
2. [x] `tests/conftest.py`에 공용 fake(`FakeAdapter`(scripted)/`FakeJudge`/샘플 Behavior) — 완료: suite green.

**M1 core 기반**
3. [x] test_records → `core/records.py` — 완료: 각 레코드 생성·불변·동등. (importorskip 브레이커 첫 시연)
4. [x] test_errors → `core/errors.py` — 완료: 각 예외 raise/필드.
5. [x] test_interfaces → `core/interfaces.py`(Adapter Protocol·Detector/Probe ABC·ProbeContext) — 완료: ABC 직접 인스턴스화 TypeError, fake가 isinstance(Adapter).
6. [x] test_budget → `core/budget.py` — 완료: N회 OK, N+1 BudgetExceeded, counter 반영.
7. [x] test_config_schema → `core/config_schema.py` — 완료: 유효 dict 빌드, self-judge dict→ConfigError(단 `allow_self_judge`).

**M2 adapters**
8. [x] test_http_openai → `adapters/http_openai.py`(fake OpenAI client 주입) — 완료: Message→payload 매핑, generate/chat, 오류→AdapterError, 네트워크 X.
9. [x] test_manual_io → `adapters/manual_io.py`(scripted input/output_fn, single+multi-turn, sentinel 종료) — 완료: 프롬프트 출력·순서대로 응답. 후 `adapters/__init__.py` ADAPTERS 등록.

**M3 detectors**
10. [x] test_refusal_match → `detectors/refusal_match.py`(순수 휴리스틱) — 완료: 거부문구→success False, 응낙→True.
11. [x] test_llama_guard → `detectors/llama_guard.py`(FakeAdapter가 "unsafe\nS9"/"safe" 반환) — 완료: 두 분기 파싱, 카테고리 추출.
12. [x] test_strong_reject → `detectors/strong_reject.py`(fake judge 루브릭) — 완료: 알려진 루브릭→알려진 0~1 점수, success=score≥τ. 후 `detectors/__init__.py` DETECTORS 등록.

**M4 정적 probe**
13. [x] test_transforms → `probes/transforms.py`(past_tense/to_base64/flip_attack/many_shot 순수) — 완료: 고정입력→고정출력, base64 왕복.
14. [x] test_static_probe → `probes/static_probe.py`(FakeAdapter+FakeJudge) — 완료: transform 적용, target_calls==1, primary detection 임베드. 후 `probes/__init__.py` PROBES(정적) 등록.

**M5 registry**
15. [x] test_registry → `registry.py` — 완료: 알려진 이름 해석, unknown→UnknownComponent(추천), available().

**M6 behaviors**
16. [x] test_builtin_seed → `behaviors/builtin_seed.py`(~15, id 유일, 전부 domain+tags, ≥1 `ot_ics`+`attack-ics:*`, 다중 taxonomy) — 완료: 개수·유일성·태그 불변식. 내용은 **비운영적·추상 paraphrase**(데이터로만).
17. [x] test_loaders → `behaviors/loaders.py`(builtin + `<path.jsonl>` 디스패치, domain/limit 필터, unknown→ConfigError) — 완료: builtin+tmp jsonl 로드·필터. 후 `behaviors/__init__.py`.

**M7 reporting: 지표·JSONL·터미널**
18. [x] test_aggregate → `reporting/aggregate.py`(순수 summarize: 기법별 ASR@B·평균calls·efficiency·StrongREJECT평균·도메인/카테고리 매트릭스·취약 top3·judge 합치도) — 완료: 수제 attempts→정확 수치.
19. [x] test_jsonl_writer → `reporting/jsonl_writer.py`(tmp: attempts.jsonl+summary.json+redact config.snapshot.yaml) — 완료: 파일 생성·왕복·**비밀키 부재**.
20. [x] test_terminal_table → `reporting/terminal_table.py`(ASCII 문자열) — 완료: 기법 행/카테고리 라인 assert.

**M8 config_loader + runner + CLI (첫 usable `rt run`, 정적 tier 오프라인 e2e)**
21. [x] test_config_loader → `config_loader.py`(yaml 읽기+CLI 오버라이드+from_dict, api_key_env 해석, target≠judge) — 완료: yaml+override→RunConfig.
22. [x] test_runner → `runner.py`(전 fake+builtin 부분+정적 기법 e2e, target_calls 기록, 모든 judge 최종응답 채점, tmp 출력) — 완료: 결정론 e2e, 예산 준수.
23. [x] test_cli 확장 → `cli.py`에 `rt run -c cfg.yaml [overrides]`(주입 runner/`--dry-run`) — 완료: 명령 wired, help 노출, 기존 cli 테스트 green.

**M9 PAIR**
24. [x] test_pair_probe → `probes/pair_probe.py`(fake attacker 제안, fake judge k회째 성공) — 완료: 성공시 중단, target_calls==k, attacker_calls==k, ≤B. `"pair"` 등록 + test_runner 확장. 예산초과는 probe 가 삼키지 않고 `BudgetExceeded` 전파(runner 처리); attacker 부재 시 `AdapterError`.

**M10 Crescendo + Manual 멀티턴**
25. [x] test_crescendo_probe → `probes/crescendo_probe.py`(conv 성장, 턴별 judge, 성공/max_turns 중단, target_calls==turns) — 완료: 멀티턴 상태 검증. `"crescendo"` 등록 + test_runner에 ManualAdapter(scripted) 경유 Crescendo run 추가로 manual 멀티턴 실증. runner 의 `BudgetExceeded` 흡수 경로(budget<max_turns)도 여기서 커버.

**M11 Fair-ASR 마감**
26. [x] test_aggregate/test_terminal_table 확장: 동일 B에서 정적 vs PAIR vs Crescendo — 완료: 동일-B ASR + 평균calls 열 + efficiency 랭킹(aggregate/terminal_table 는 기존 로직으로 충족, 테스트만 확장).

> **재작업 (2026-09-14, fidelity)**: task 24~26 은 이후 **원저자 코드 기반**으로 재작성됨.
> PAIR(`patrickrchao/JailbreakingLLMs@6379ef7`)·Crescendo(`Azure/PyRIT@004d079`) 프롬프트를
> `src/redteam/vendor/{pair,crescendo}/` 에 verbatim vendor(+LICENSE/PROVENANCE/파일별 sha256).
> native judge 신설: `pair_judge`(1~10)·`crescendo_refusal`·`crescendo_objective`(0~100,th 0.8).
> PAIR = JSON `{improvement,prompt}` + n_streams×n_iterations + keep_last_n + ==10 조기중단;
> Crescendo = JSON `generated_question` + refusal→backtrack(max_backtracks) + objective≥0.8.
> `ProbeContext` 에 `judge_client`+`params`, `TechniqueSpec`(기법별 config) 추가(하위호환).
> 근거·정책: `docs/technique-fidelity.md`, `references/adding-a-technique.md`, 루트 `THIRD_PARTY_NOTICES.md`.
> ⚠️ 기존 검증 리포트(bd2ba8c)는 옛 구현 기준 — 커밋 후 M9~M11 **재검증** 필요.
> ※ 기법 pluginable화(자동등록/엔트리포인트)는 별도 설계 문서: `docs/pluggable-techniques.md`.

**M12 HTML 리포트(중심)**
27. [x] test_html_report → `reporting/html_report.py`(jinja2 렌더, 8섹션 + **위험도 히트맵 셀** + top3 + 드릴다운 transcript+judge3 + taxonomy + 합치도) — 완료: 섹션·히트맵 존재, runner 연동, test_runner에 report.html 생성 assert.
    `Summary` 에 `heatmap`(도메인×기법)·`per_tag`(taxonomy) 축 추가(기본값 有 → 하위호환). 외부 CDN 0개(오프라인 단일 파일), autoescape 필수.

**M13 jbb/HarmBench 로더**
28. [x] test_loaders 확장(로컬 fixture 파일로 jbb+harmbench 파싱→Behavior, 태그 보존) — 완료: fixture 파싱,
    네트워크 다운로드 제외. `BehaviorSpec.path` 신설(외부 셋은 로컬 경로 필수); 원본 카테고리는 내부 도메인
    매핑 + 슬러그 폴백, 원본 taxonomy 는 `jbb:*`/`harmbench:*` 태그로 보존.

**M14 import-linter + deptry**
29. [x] `[tool.importlinter]` 계약(layers / role 독립성 / core 금지 / vendor 독립) 추가 — 완료: `lint-imports` 4 kept,
    `deptry src` green(dev extras 는 DEP002 ignore). 기존 코드 수정 불필요 — 계약이 실 위반을 잡는 것까지 확인.

**M15 live 테스트(선택, marked)**
30. [x] `tests/test_http_live.py`(`live` 마킹, 실 엔드포인트 스모크) — 완료: `pytest -q` 무영향, `pytest -m live` 수동 실행.

## Verification (end-to-end)

```bash
cd ~/Projects/RedTeaming
pip install -e ".[dev]"
python -m pytest -q                 # 전 green (live 제외)
ruff check . && ruff format --check .
lint-imports && deptry src          # 레이어/의존성 clean
# 오프라인 스모크(fake 아님, 로컬 Ollama 등 준비 시):
rt run -c examples/run.yaml         # out/runs/<ts>/ 에 jsonl+summary+snapshot+report.html, 터미널 요약표 출력
```
YAML 예시 스키마: `target/attacker/judge:{base_url,api_key_env,model}`, `judge:[refusal_match, llama_guard:{...},
strong_reject:{...}]`, `behaviors: builtin|jbb|harmbench|<path>`, `techniques:[flip_attack,pair,crescendo]`,
`budget:{target_calls:50}`, `reporting:{html:true}`.

## Open questions (구현 중 확정)

- **PAIR/Crescendo의 primary judge** (확정, M9/M10): probe 는 이진 primary(`refusal_match` 등, `score=None`)에도
  크래시 없이 동작하고 피드백은 점수를 "N/A"로 렌더한다 → `strong_reject`를 detectors[0]로 두면 반복 피드백이
  풍부해져 **권장**이지만 **필수는 아니다**. 즉 정책은 "graceful degradation + strong_reject 권장".
- **Manual 어댑터 sentinel**: 멀티라인 붙여넣기 종료 표식(단독 `.` vs EOF)과 인터럽트 처리 방식.
- **LlamaGuard 버전/카테고리 맵**: 채팅 템플릿·S1..S13 맵을 생성자 파라미터로(버전마다 다름) — 기본 버전 지정.
- **HTML 리포트 v1**: 만들어 본 뒤 사용자 피드백으로 레이아웃/강조 반복.
- **import-linter 2.x**: layers 계약의 `a | b` 파이프 문법 설치버전 확인(안 되면 independence+forbidden으로 충분).
