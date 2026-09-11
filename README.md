# NOIR — NSR Opaque-box Investigation & Red-teaming

범용 블랙박스 LLM red-teaming MVP — 타깃 모델의 취약성을 파악하고 ASR 로 평가한다. (패키지 `redteam` · CLI `rt`)

- 프로젝트 지도: [`CLAUDE.md`](CLAUDE.md)
- 설계 / 근거: [`docs/`](docs/)
- 개발 규칙: [`references/`](references/)

## 개발 셋업

    pip install -e ".[dev]"
    rt --version
    python -m pytest -q

현재는 **스캐폴딩 단계**. 공격 기법·타깃 어댑터·ASR judge 는 이후 단계에서 구현한다.
