"""패키지가 import 되고 버전이 노출되는지 확인하는 스모크 테스트."""

import redteam


def test_package_imports_and_exposes_version() -> None:
    assert isinstance(redteam.__version__, str)
    assert redteam.__version__ == "0.1.0"
