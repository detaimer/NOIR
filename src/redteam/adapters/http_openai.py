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
        """실제 클라이언트 호출; 모든 예외를 AdapterError 로 래핑한다."""
        try:
            resp = self.client.chat.completions.create(model=self.model, messages=messages)
            return resp.choices[0].message.content
        except Exception as exc:
            raise AdapterError(f"{self.name} chat.completions failed: {exc}") from exc
