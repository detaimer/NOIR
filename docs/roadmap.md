# 로드맵 (WHY)

## v0.1 — 스캐폴딩 (현재)
역할별 폴더 구조 + 얇은 CLAUDE.md + references/docs + TDD 인프라 + `rt` 진입점. 테스트 green.

## v0.2 — 기능 MVP (계획 확정)
pluggable 범용 프레임워크(garak/PyRIT류). 상세·task 는 **[docs/plan.md](plan.md)**. 요지:
- 기법 3 tier: 정적 one-shot(past-tense·base64·FlipAttack·many-shot) + PAIR + Crescendo
- detector 3개: RefusalMatch · LlamaGuard · StrongREJECT (구조화 출력; ASR은 기본 헤드라인일 뿐 유일 축 아님)
- 어댑터: HTTP(상업+로컬) + Manual · YAML run-config · Fair-ASR · JSONL+터미널+HTML 리포트
- probe/adapter/detector 인터페이스(ABC) + import-linter 계약
- OT/ICS는 `domain`+taxonomy 태그 도메인(하드 특화 X)

## 이후 (v0.3+)
LiteLLM · Multimodal(FigStep) · TAP/PAP/GOAT/X-Teaming · Wilson CI 신뢰구간 · 데이터셋 auto-download ·
병렬/async 실행 · judge 앙상블 · OT 전용 대량 데이터셋 저작.
