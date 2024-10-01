from typing import List
from pydantic import Field
from expertdx.message import ChatMessage
from .memory import Memory


class ChatMemory(Memory):
    messages: List[ChatMessage] = Field(default=[])

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)

    def add_messages(self, messages: List[ChatMessage]) -> None:
        for message in messages:
            self.messages.append(message)

    def to_dict(self) -> List[ChatMessage]:
        return self.messages

    def reset(self) -> None:
        self.messages = []
