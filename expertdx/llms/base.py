from abc import abstractmethod, ABC
from typing import Union, Optional, Any
from pydantic import BaseModel, Field
from expertdx.message import Message
from expertdx.utils.logging_utils import get_logger


class LLMResult(BaseModel):
    message: Message
    finish_reason: Optional[str]
    send_tokens: Optional[int]
    recv_tokens: Optional[int]
    total_tokens: Optional[int]


class BaseLLM(BaseModel):
    model: str = Field(default="gpt4-turbo")
    logger: Any = Field(default_factory=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def generate_response(self, **kwargs) -> LLMResult:
        pass


class BaseChatModel(BaseLLM, ABC):
    pass


class BaseCompletionModel(BaseLLM, ABC):
    pass
