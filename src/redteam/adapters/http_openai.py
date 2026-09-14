"""HttpOpenAIAdapter — OpenAI 호환 HTTP 타깃(상업 API + 로컬 서버) 어댑터."""

from __future__ import annotations

from redteam.core import AdapterError, Message


class HttpOpenAIAdapter:
    """OpenAI 호환 chat.completions 엔드포인트를 감싸는 Adapter (설정만으로 상업/로컬 겸용)."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        client: object | None = None,
        name: str | None = None,
    ) -> None:
        """client 미주입 시 openai.OpenAI 를 지연 생성; name 기본값은 ``http:<model>``."""
        self.model = model
        if client is None:
            import openai

            client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self.client = client
        self.name = name or f"http:{model}"

    def generate(self, prompt: str, system: str | None = None) -> str:
        """system(옵션)+user 프롬프트로 1회 호출하고 응답 텍스트를 반환한다."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._create(messages)

    def chat(self, messages: list[Message]) -> str:
        """Message 리스트를 OpenAI payload 로 매핑해 호출하고 응답 텍스트를 반환한다."""
        payload = [{"role": m.role.value, "content": m.content} for m in messages]
        return self._create(payload)

    def _create(self, messages: list[dict[str, str]]) -> str:
        """실제 클라이언트 호출; 모든 예외를 AdapterError 로 래핑한다.

        content 가 비면(reasoning 모델이 사고과정 채널에만 답을 남기는 경우) reasoning 으로
        폴백한다. content 가 non-blank 면 그대로 쓰므로 실제 거부("I can't…")는 폴백하지 않는다.
        content·reasoning 이 모두 비면 "" 를 반환한다(None 반환 방지).
        """
        try:
            resp = self.client.chat.completions.create(model=self.model, messages=messages)
            message = resp.choices[0].message
            return _first_nonblank(message.content, getattr(message, "reasoning", None))
        except Exception as exc:
            raise AdapterError(f"{self.name} chat.completions failed: {exc}") from exc


def _first_nonblank(*values: str | None) -> str:
    """앞에서부터 공백-only 가 아닌 첫 문자열을 반환; 모두 비면 ""."""
    for v in values:
        if v is not None and v.strip():
            return v
    return ""
