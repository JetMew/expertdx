import json
from abc import abstractmethod
from typing import Union
from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletionMessage


class BaseMessage(BaseModel):
    content: str
    additional_kwargs: dict = Field(default_factory=dict)

    @property
    @abstractmethod
    def role(self) -> str:
        """Type of the message, used for serialization."""
        pass

    def to_string(self, add_prefix: bool = True):
        if add_prefix:
            return f"[{self.role}] {json.dumps(self.content, indent=2, ensure_ascii=False)}"
        else:
            return str(self.content)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content
        }


class SystemMessage(BaseMessage):
    @property
    def role(self) -> str:
        return "system"


class UserMessage(BaseMessage):
    @property
    def role(self) -> str:
        return "user"


class AssistantMessage(BaseMessage):
    tool_calls: list = Field(default_factory=list)

    @property
    def role(self) -> str:
        return "assistant"

    def to_dict(self) -> dict:
        if self.tool_calls:
            return {
                "role": self.role,
                "content": self.content,
                "tool_calls": self.tool_calls
            }
        else:
            return super().to_dict()


class ToolMessage(BaseMessage):
    name: str = Field(default="")

    @property
    def role(self) -> str:
        return "function"

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "name": self.name,
            "content": self.content
        }


class ChatMessage(BaseMessage):
    sender: str

    @property
    def role(self) -> str:
        return "chat"

    def to_string(self, add_prefix: bool = True):
        if add_prefix:
            return f"[{self.sender}]: {json.dumps(self.content, indent=2, ensure_ascii=False)}"
        else:
            return str(self.content)


Message = Union[BaseMessage, ChatCompletionMessage]
