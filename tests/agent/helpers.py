from __future__ import annotations

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, PrivateAttr


class ToolFakeChatModel(BaseChatModel):
    """Minimal chat model stub that supports Deep Agents tool binding."""

    responses: list[str] = Field(default_factory=list)
    _call_count: int = PrivateAttr(default=0)

    def bind_tools(self, tools: object, **kwargs: object) -> ToolFakeChatModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        if not self.responses:
            text = "ok"
        else:
            idx = min(self._call_count, len(self.responses) - 1)
            text = self.responses[idx]
        self._call_count += 1
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    @property
    def _llm_type(self) -> str:
        return "tool-fake"
