import json
from openai import AzureOpenAI
from typing import Optional, Union, Any
from pydantic import Field
from expertdx.message import AssistantMessage
from . import llm_registry
from .base import BaseChatModel, LLMResult


@llm_registry.register("azure_openai_chat")
class AzureOpenAIChat(BaseChatModel):
    model: str = Field(default="gpt4-turbo")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.7)
    top_p: float = Field(default=0.8)

    version: str = Field(default="2024-02-15-preview")
    endpoint: str = Field(default=...)
    apikey: str = Field(default=...)        # APIKEY here

    client: Any = None

    def __init__(self, **data):
        super().__init__(**data)
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_version=self.version,
            api_key=self.apikey
        )

    def generate_response(
            self,
            messages,
            tools: Optional[list] = None,
            tool_choice: Union[str, dict] = "none",
            model: Optional[str] = None,
            max_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            response_format: Optional[dict] = None,
            stream: bool = False,
    ) -> LLMResult:

        params = {
            "model": model or self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "top_p": top_p or self.top_p,
            "response_format": response_format or {"type": "text"}
        }

        if tool_choice != "none":
            assert stream is False, "tool call "
            params["tools"] = tools
            params["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(
            messages=messages,
            stream=stream,
            **params
        )

        if not stream:
            self.logger.debug(
                f"Input Messages ({response.usage.prompt_tokens} tokens):\n"
                f"{json.dumps({'messages': [m.get('content') for m in messages]}, indent=2, ensure_ascii=False)}"
            )
            self.logger.debug(
                f"Output Message ({response.usage.completion_tokens} tokens):\n"
                f"{json.dumps(response.choices[0].message.content, indent=2, ensure_ascii=False)}"
            )
            self.logger.info(
                f"total_tokens: {response.usage.total_tokens}, "
                f"send_tokens: {response.usage.prompt_tokens}, "
                f"recv_tokens: {response.usage.completion_tokens}."
            )
            return LLMResult(
                message=response.choices[0].message,                # content, role, function_call, tool_calls
                finish_reason=response.choices[0].finish_reason,
                send_tokens=response.usage.prompt_tokens,
                recv_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        else:
            message = AssistantMessage(content="")
            finish_reason = None

            for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                if delta.content is not None:
                    message.content += delta.content
                    print(delta.content, end="")      # print the delay and text

                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                if delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    index = tool_call.index
                    if index == len(message.tool_calls):
                        # add tool_call dict
                        tool_call = {
                            "id": tool_call.get("id", None),
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        message.tool_calls.append(tool_call)
            print()

            self.logger.debug(
                f"Input Messages:\n"
                f"{json.dumps({'messages': [m.get('content') for m in messages]}, indent=2, ensure_ascii=False)}"
            )
            self.logger.debug(
                f"Output Message:\n"
                f"{json.dumps(message.content, indent=2, ensure_ascii=False)}"
            )

            return LLMResult(
                message=message,
                finish_reason=finish_reason,
                send_tokens=-1,
                recv_tokens=-1,
                total_tokens=-1
            )
