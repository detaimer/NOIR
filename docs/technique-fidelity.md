# 기법 충실도(fidelity) 정책 — 원저자 프롬프트 vendoring + 충실 재구현 (WHY)

## 배경

공격 기법(probe)은 **논문 기억으로 재현하면 안 된다.** 초기 PAIR/Crescendo 구현이 그렇게 되어
(공격 프롬프트가 가짜, PAIR 1~10 피드백·Crescendo 백트래킹 누락, 출처 없음) 재작업했다.
이 문서는 그때 확정한 통합 정책과 근거를 남긴다. 실무 절차(HOW)는
[`references/adding-a-technique.md`](../references/adding-a-technique.md).

## 정책 (2026-09-14 확정)

> **문구는 원본 그대로 복사(vendor) + 절차는 원본 코드를 보고 충실히 재구현 + 출처·라이선스 기록.**

층별 원칙:

1. **프롬프트/판정 기준** — 라이선스가 허용하면 **항상 verbatim vendor**(공백·특수문자까지 보존).
   `src/redteam/vendor/<technique>/` 에 데이터 파일(.txt/.yaml)로 둔다. 예외 없음.
2. **절차(loop)** — 원본이 프레임워크/인프라에 묶였거나 라이선스가 없으면 → **프롬프트만 vendor +
   루프를 rt 의 `Probe.run`/adapter 계약에 맞춰 충실히 재구현**(원본 파일·커밋을 주석으로 인용,
   불가피한 차이는 DEVIATIONS 로 명시). 원본이 복잡·자기완결·라이선스 OK 면 HarmBench 식
   **복사+각색**도 가능.
3. **import/pip-의존/submodule 은 하지 않는다.** rt 의 pluggable·최소의존성(openai/pyyaml/jinja2)·
   adapter DI 정체성을 지킨다.
4. **항상 provenance + 라이선스 동반.** repo URL·commit SHA·원본 파일 경로·파일별 sha256·
   DEVIATIONS·원본 LICENSE 사본을 `vendor/<technique>/PROVENANCE.md` + `LICENSE` 로 둔다.

## 왜 "저자 코드를 통째로 쓰지" 않는가 (조사 근거)

- **주요 프레임워크 넷 다 원저자 레포를 import/submodule/pip-의존/subprocess 로 쓰지 않는다.**
  - PyRIT·deepteam: 네이티브 재구현 + 프롬프트만 vendor(PyRIT 는 YAML `source:`/`authors:` 표기,
    deepteam 은 표기 거의 없음 — 반면교사).
  - HarmBench·garak: 원본 소스를 기법별로 **복사+각색**해 자기 트리에 두고 얇게 감쌈
    (garak 은 파일마다 SPDX 로 원 라이선스 보존).
- **원저자 레포는 대개 "그대로 실행 불가".** 예: X-Teaming 은 라이선스 파일 없음(vendor 자체 불가),
  CWD 묶인 연구 스크립트, judge 가 OpenAI 에 하드와이어드. 11개 method 레포 중 pip 설치 가능한 건
  하나(GCG)뿐이고 그마저 white-box 라 블랙박스 HTTP 프레임워크엔 무용.
  → **재사용 가능한 자산은 코드 패키지가 아니라 프롬프트 + 알고리즘.**

## PAIR·Crescendo 적용 결과

| | PAIR | Crescendo |
|---|---|---|
| 원본 | patrickrchao/JailbreakingLLMs @ `6379ef7` (MIT) | Azure/PyRIT @ `004d079` (MIT, MS) |
| vendored 프롬프트 | 3전략 attacker + 1~10 judge + init/process 메시지 | crescendo_variant_1 + refusal(default/strict) + 0~100 scale(+red_teamer) |
| native judge | `pair_judge`(1~10) | `crescendo_refusal` + `crescendo_objective`(0~100, th=0.8) |
| 루프 | n_streams×n_iterations, keep_last_n, JSON `{improvement,prompt}`, ==10 조기중단 | max_turns, refusal→backtrack(max_backtracks), objective≥0.8 |
| 재구현 위치 | `probes/pair_probe.py` | `probes/crescendo_probe.py` |

**보고 ASR vs 루프 구동**: 기본 보고 성공(ASR)은 실행의 primary detector(`detectors[0]`)로 판정해
기법 간 Fair-ASR 비교를 일관되게 유지하고, 원본 native judge 는 **루프 구동**(PAIR 점수 피드백·
Crescendo 백트래킹/성공)에 쓴다. 원본 논문식 ASR 이 필요하면 config 에서 primary 를
`pair_judge`/`crescendo_objective` 로 지정하면 코드 변경 없이 전환된다.

**참고**: rt 프로젝트 자체의 루트 LICENSE 는 아직 정해지지 않았다(배포 라이선스는 사용자 결정 사항).
vendored 서드파티 코드의 라이선스는 `vendor/*/LICENSE` + [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)
로 보존한다.
