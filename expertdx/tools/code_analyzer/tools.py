import os
import json
import requests
from abc import ABC
from pydantic import Field
from .. import tool_registry
from ..base import Tool, AgentEnum


class CodeAnalyzer(Tool, ABC):
    offline: bool = Field(default=True)
    tool_request_url: str = Field(default='')
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json'
    }

    def __call__(self, data: dict):
        # cached tool observation for offline evaluation
        if self.offline:
            filepath = os.path.join(self.data_dir, f"{data['task_id']}/{self.name}.txt")
            self.logger.info(f"offline simulation of tool requests. loading from {filepath}")
            with open(filepath) as f:
                return f.read()
        else:
            r = requests.post(url=self.tool_request_url, headers=self.headers, data=json.dumps(data))
            res = r.json()
            return res


@tool_registry.register("sql_copilot")
class SQLCopilot(CodeAnalyzer):
    name = "sql_copilot"
    description = (
        "This is a sophisticated SQL analysis tool designed to optimize the performance of SQL queries. "
        "It examines your SQL queries to identify potential performance bottlenecks, inefficient operations, and areas that could benefit from indexing or other optimization techniques. "
        "SQL Copilot also provides actionable recommendations to improve the efficiency of your queries."
    )
    belong_to = AgentEnum.supersql
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("program_analyzer")
class ProgramAnalyzer(CodeAnalyzer):
    name = "program_code_check"
    description = (
        "Check Spark Program Code to identify potential issues snippets or input, output, logic errors"
    )
    belong_to = AgentEnum.idex
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }
