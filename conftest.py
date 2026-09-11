"""루트 conftest — src/ 레이아웃을 sys.path 에 올려 `import redteam` 가능하게 한다.

전역 TDD 훅이 repo 루트를 PYTHONPATH 에 두므로(＝ src/ 는 자동 포함 안 됨),
편집 가능 설치(`pip install -e .`) 전에도 테스트가 패키지를 찾도록 보강한다.
"""

import pathlib
import sys

_SRC = pathlib.Path(__file__).parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
