from typing import List, Dict
from pydantic import BaseModel, Field
from expertdx.message import Message, BaseMessage, SystemMessage, AssistantMessage, UserMessage, ToolMessage


class Memory(BaseModel):
    messages: List[Message] = Field(default=[])

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def add_messages(self, messages: List[Message]) -> None:
        for message in messages:
            self.messages.append(message)

    def get_messages(self) -> List[Dict]:
        return [
            message.to_dict() if isinstance(message, BaseMessage) else message
            for message in self.messages
        ]

    def to_string(self, verbose: bool = True) -> str:
        if verbose:
            return "\n".join([
                f"==== Message {i + 1} ====\n"
                f"{message.to_string(add_prefix=True)}"
                for i, message in enumerate(self.messages)
            ])
        else:
            return "\n".join([
                f"{message.to_string(add_prefix=False)}"
                for message in self.messages
            ])

    def load_from_json(self, messages) -> None:
        self.reset()
        for message in messages:
            role = message["role"]
            content = message['content']
            if role == "system":
                self.messages.append(SystemMessage(content=content))
            elif role == "user":
                self.messages.append(UserMessage(content=content))
            elif role == "assistant":
                self.messages.append(AssistantMessage(content=content))
            elif role == "function":
                name = message["name"]
                self.messages.append(ToolMessage(content=content, name=name))
            else:
                raise ValueError("invalid message type.")

    def reset(self) -> None:
        self.messages = []
