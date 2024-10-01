import json
from pydantic import Field, BaseModel
from typing import Union, Any
from expertdx.llms import LLMResult
from expertdx.message import SystemMessage
from expertdx.toolkit import Toolkit
from .base import Agent


class AgentAction(BaseModel):
    """Agent's action to take."""
    tool: str
    tool_input: dict
    tool_call_id: str
    log: Any

    def to_string(self):
        return f"[{self.tool}] {json.dumps(self.tool_input, indent=2, ensure_ascii=False)}"


class AgentFinish(BaseModel):
    """Agent's return value."""
    return_values: Any
    log: Any


class ToolAgent(Agent):
    toolkit: Toolkit = Field(default_factory=Toolkit)

    def __init__(self, **data):
        super().__init__(**data)
        self.memory.add_message(SystemMessage(
            role="system",
            content=self.role_description
        ))

    def reset(self, **kwargs) -> None:
        self.memory.reset()
        self.chat_memory.reset()
        self.receiver = {"all"}

    def tool_call(self, *args, **kwargs) -> str:
        pass

    def _parse(self, response: LLMResult) -> Union[AgentAction, AgentFinish]:
        if response.finish_reason == "tool_calls":
            tool_calls = response.message.tool_calls
            response.message.tool_calls = [tool_calls[0], ]

            tool_call_id = response.message.tool_calls[0].id
            function_call = response.message.tool_calls[0].function

            print(function_call.name)
            print(function_call.arguments)

            return AgentAction(
                tool=function_call.name,
                tool_input=json.loads(function_call.arguments),
                tool_call_id=tool_call_id,
                log=response
            )
        elif response.finish_reason == "stop":
            return AgentFinish(
                return_values=response.message.content,
                log=response,
            )
        else:
            self.logger.warning(response.finish_reason)

