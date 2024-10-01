from abc import abstractmethod
from enum import Enum
from typing import Any
from pydantic import Field, BaseModel
from expertdx.utils.logging_utils import get_logger


class AgentEnum(str, Enum):
    helper = 'helper_agent'
    spark = 'spark_agent'
    yarn = 'yarn_agent'
    hive = 'hive_agent'
    hdfs = 'hdfs_agent'
    # in-house product
    us = 'us_agent'
    idex = 'idex_agent'
    supersql = 'supersql_agent'


class Tool(BaseModel):
    name: str
    description: str
    belong_to: AgentEnum
    parameters: dict = Field(default={"type": "object", "properties": {}, "required": []})
    logger: Any = Field(default_factory=None)
    data_dir: str = Field(default="data")

    def __init__(self, **data):
        super().__init__(**data)
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def __call__(self, *args, **kwargs) -> Any:
        pass

    def get_tool_information(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
