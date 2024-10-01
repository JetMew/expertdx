from typing import List, Optional
from pydantic import BaseModel, Field
from expertdx.tools import Tool


class Toolkit(BaseModel):
    tools: List[Tool] = Field(default=[])

    def get_tools(self) -> List[Tool]:
        return self.tools

    def get_tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]

    def get_tool_descriptions(self, exclude_tools: Optional[List] = None) -> List:
        if exclude_tools is None:
            exclude_tools = []

        return [
            tool.get_tool_information()
            for tool in self.tools if tool.name not in exclude_tools
        ]

    def get_tool_by_name(self, name) -> Tool:
        return next((tool for tool in self.tools if tool.name == name), None)
