#!/usr/bin/env bash
# validate skill 의 자동 게이트 — 계획과 무관하게 매번 같은 방법으로 도는 품질 검사를 모아 실행한다.
# 사용법: gates.sh [검증할 디렉터리 (기본: .)]
# 사실만 출력하고 판정은 skill 본문 기준으로 모델이 내린다. 코드를 바꾸지 않고 캐시도 남기지 않는다.
set -uo pipefail

dir="${1:-.}"
cd "$dir" || { echo "디렉터리 없음: $dir" >&2; exit 2; }
# 커밋 사본에서 돌 때도 사본의 src 를 import 하도록, 편집 가능 설치가 가리키는 원본 src 보다 앞에 둔다.
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1

roles="probes adapters detectors reporting behaviors"
upper="registry runner cli config_loader"

section() { printf '\n=== %s ===\n' "$1"; }

echo "검증 디렉터리: $PWD"

section "1. pytest (addopts 대로 live 제외, skip 사유 포함)"
out=$(python -m pytest -q -rs -p no:cacheprovider 2>&1); code=$?
printf '%s\n' "$out" | tail -25
echo "exit=$code"

section "2. 조용한 skip — importorskip 등으로 건너뛴 테스트 (구현이 있는데 skip 이면 거짓 green)"
skips=$(printf '%s\n' "$out" | grep -E '^SKIPPED' || true)
if [ -n "$skips" ]; then printf '%s\n' "$skips"; else echo "(skip 없음)"; fi

section "3. live 마커 — live 전용 파일 밖에서 live 로 빠진 테스트 (기본 실행에서 숨겨짐)"
live=$(grep -rnE 'mark\.live' tests --include='*.py' 2>/dev/null | grep -v 'tests/test_http_live.py' || true)
if [ -n "$live" ]; then printf '%s\n' "$live"; else echo "(없음)"; fi

section "4. ruff check / format --check"
ruff check --no-cache . 2>&1 | tail -20; echo "check exit=${PIPESTATUS[0]}"
ruff format --check --no-cache . 2>&1 | tail -20; echo "format exit=${PIPESTATUS[0]}"

section "5. import-linter (계약이 설정된 뒤에만 — plan M14)"
if grep -q '^\[tool\.importlinter' pyproject.toml 2>/dev/null; then
  lint-imports --no-cache 2>&1 | tail -30; echo "exit=${PIPESTATUS[0]}"
else
  echo "(계약 미설정 — 6번 grep 검사로 대신함)"
fi

section "6. 레이어 import — 역할 패키지는 core 에만 의존, core 는 어떤 역할도 모름"
viol=0
for role in $roles; do
  d="src/redteam/$role"
  [ -d "$d" ] || continue
  others=$(printf '%s\n' $roles $upper | grep -vx "$role" | paste -sd'|')
  hits=$(grep -rnE \
    -e "^[[:space:]]*(from|import)[[:space:]]+redteam\.($others)([.[:space:]]|$)" \
    -e "^[[:space:]]*from[[:space:]]+redteam[[:space:]]+import[[:space:]].*\b($others)\b" \
    -e "^[[:space:]]*from[[:space:]]+\.\.($others)\b" \
    "$d" --include='*.py' || true)
  if [ -n "$hits" ]; then printf '%s\n' "$hits"; viol=1; fi
done
if [ -d src/redteam/core ]; then
  all=$(printf '%s\n' $roles $upper | paste -sd'|')
  hits=$(grep -rnE \
    -e "^[[:space:]]*(from|import)[[:space:]]+redteam\.($all)([.[:space:]]|$)" \
    -e "^[[:space:]]*from[[:space:]]+redteam[[:space:]]+import[[:space:]].*\b($all)\b" \
    -e "^[[:space:]]*from[[:space:]]+\.\.($all)\b" \
    src/redteam/core --include='*.py' || true)
  if [ -n "$hits" ]; then printf '%s\n' "$hits"; viol=1; fi
fi
[ "$viol" -eq 0 ] && echo "(위반 없음)"

section "7. 모듈 basename 유일성 + 테스트 짝 (tests/test_<name>.py)"
dups=$(find src -name '*.py' ! -name '__init__.py' -printf '%f\n' 2>/dev/null | sort | uniq -d)
if [ -n "$dups" ]; then echo "중복 basename: $dups"; else echo "(중복 없음)"; fi
missing=""
while IFS= read -r f; do
  b=$(basename "$f" .py)
  [ -f "tests/test_$b.py" ] || missing="$missing $f"
done < <(find src -name '*.py' ! -name '__init__.py' 2>/dev/null | sort)
if [ -n "$missing" ]; then echo "테스트 짝 없음:$missing"; else echo "(모든 모듈에 테스트 짝 있음)"; fi

section "8. 인라인 비밀키 / Non-goal 의존성"
keys=$(grep -rnE \
  -e 'sk-[A-Za-z0-9_-]{16,}' -e 'xai-[A-Za-z0-9]{16,}' \
  -e "api_key[\"']?[[:space:]]*[:=][[:space:]]*[\"'][^\"'\$]{8,}" \
  src tests examples 2>/dev/null | grep -v 'api_key_env' || true)
if [ -n "$keys" ]; then printf '%s\n' "$keys"; echo "(테스트용 가짜 값인지 확인할 것)"; else echo "(인라인 키 없음)"; fi
dep=$( { grep -nE '^[[:space:]]*"(litellm|rich)\b' pyproject.toml
         grep -rnE '^[[:space:]]*(import|from)[[:space:]]+(litellm|rich)\b' src --include='*.py'; } 2>/dev/null || true)
if [ -n "$dep" ]; then printf '%s\n' "$dep"; else echo "(Non-goal 의존성 없음)"; fi

section "9. deptry (선언한 의존성 ↔ 실제 import)"
deptry --no-ansi src 2>&1 | tail -20; echo "exit=${PIPESTATUS[0]}"
