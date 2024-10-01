from typing import List, Any
from pydantic import BaseModel, Field
from expertdx.agents import ToolAgent
from expertdx.utils.logging_utils import get_logger


class Environment(BaseModel):
    agents: List[ToolAgent]
    max_turns: int = Field(default=1)
    cnt_turns: int = Field(default=0)
    logger: Any = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.logger = get_logger(self.__class__.__name__)

    def reset(self) -> None:
        self.cnt_turns = 0

    def is_done(self) -> bool:
        return self.cnt_turns >= self.max_turns
