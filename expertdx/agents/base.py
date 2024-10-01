from abc import abstractmethod
from typing import Any, Dict, Set, Union, Optional
from pydantic import BaseModel, Field
from expertdx.llms import BaseLLM
from expertdx.memory import ChatMemory, Memory
from expertdx.toolkit import Toolkit
from expertdx.utils.logging_utils import get_logger


class Agent(BaseModel):
    name: str = ""
    role_description: str = ""
    toolkit: Toolkit = Field(default_factory=Toolkit)

    llm: BaseLLM
    memory: Memory = Field(default_factory=Memory)
    chat_memory: ChatMemory = Field(default_factory=ChatMemory)
    receiver: Set[str] = Field(default={"all"})
    max_tool_calls: Optional[int] = Field(default=1000)
    max_iterations: Optional[int] = Field(default=None)
    max_execution_time: Optional[float] = Field(default=None)
    verbose: bool = Field(default=True)

    iteration: int = Field(default=0)
    logger: Any = Field(default_factory=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def reset(self, **kwargs) -> None:
        """Reset the agent"""
        pass

    def get_receiver(self) -> Set[str]:
        return self.receiver

    def add_receiver(self, receiver: Union[Set[str], str]) -> None:
        if isinstance(receiver, str):
            self.receiver.add(receiver)
        elif isinstance(receiver, set):
            self.receiver = self.receiver.union(receiver)
        else:
            raise ValueError(
                "input argument `receiver` must be a string or a set of string"
            )

    def remove_receiver(self, receiver: Union[Set[str], str]) -> None:
        if isinstance(receiver, str):
            try:
                self.receiver.remove(receiver)
            except KeyError as e:
                self.logger.warning(f"Receiver {receiver} not found.")
        elif isinstance(receiver, set):
            self.receiver = self.receiver.difference(receiver)
        else:
            raise ValueError(
                "input argument `receiver` must be a string or a set of string"
            )
