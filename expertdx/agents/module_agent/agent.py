import os
import json
import requests
from pydantic import Field
from string import Template
from expertdx.llms import BaseLLM, AzureOpenAIChat
from expertdx.toolkit import Tool
from expertdx.diagnostics import DiagnosticState, DiagnosticItem
from .. import agent_registry
from ..tool_agent import ToolAgent
from .prompt import MITIGATE_PROMPT, ANALYZE_PROMPT

DEBUG = True


@agent_registry.register("module_agent")
class ModuleAgent(ToolAgent):
    name: str
    role_description: str
    llm: BaseLLM = Field(default_factory=AzureOpenAIChat)

    task_id: str = Field(default="")
    data_dir: str = Field(default="data")
    offline: bool = Field(default=True)

    def tool_call(self, tool: Tool, data: dict) -> str:
        self.task_id = data.get("task_id", "")
        try:
            observation = tool(data=data)
            response = self.llm.generate_response(
                messages=[
                    {"role": "system", "content": self.role_description},
                    {"role": "user", "content": Template(ANALYZE_PROMPT).substitute(
                        name=tool.name,
                        description=tool.description,
                        observation=observation
                    )}
                ]
            )
            analysis = response.message.content
        except:
            observation = input()
            analysis = observation
        self.logger.info(f"Observation Analysis: {analysis}")
        return analysis

    def mitigate(self, task_id: str, anomaly: DiagnosticItem, state: DiagnosticState, stream=True):
        self.task_id = task_id
        self.logger.info(f"[{self.name}: mitigate {anomaly.name}]")

        if DEBUG:
            filename = self._get_filepath(f"{self.name}_mitigate.txt")
            if os.path.exists(filename):
                anomaly.set_fixed()
                return True

        messages = [
            {"role": "system", "content": self.role_description},
            {"role": "user", "content": Template(MITIGATE_PROMPT).substitute(
                anomaly=json.dumps(anomaly.to_dict(), indent=2, ensure_ascii=False))},
        ]
        response = self.llm.generate_response(
            messages=messages,
            stream=stream
        )
        solution = response.message.content

        total_tokens = response.total_tokens
        send_tokens = response.send_tokens
        recv_tokens = response.recv_tokens

        filename = self._get_filepath(f"{self.name}_mitigate.txt")
        with open(filename, "w") as f:
            f.write(solution)

        is_fixed = self.check_mitigation({"task_id": task_id, "anomaly": anomaly.name, "cause": None, "suggests": solution})
        anomaly.set_fixed()

        step_info = {
            "step": self.iteration,
            "action": "mitigate",
            "node_name": anomaly.name,
            "content": solution,
            "diagnostic_state": state.to_dict(),
            "tokens": [send_tokens, recv_tokens, total_tokens]
        }
        self.load_and_update_history(step_info)
        return is_fixed

    def check_mitigation(self, data: dict):
        # online: provide mitigation suggestion to re-run task for check
        if self.offline:
            return True  # default
        else:
            url = ""
            headers = {
                'accept': '*/*',
                'Content-Type': 'application/json'
            }
            r = requests.post(url=url, headers=headers, data=json.dumps(data))
            res = r.json()
            return res["is_fixed"]

    def _get_filepath(self, filename: str) -> str:
        file_path = os.path.join(self.data_dir, f"{self.task_id}/results/{filename}")
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        return file_path

    def load_and_update_history(self, step_info: dict):
        output_file = self._get_filepath("run_history.json")
        with open(output_file) as f:
            history = json.load(f)
        history.append(step_info)
        with open(output_file, "w") as f:
            f.write(json.dumps(history, indent=4, ensure_ascii=False))
        self.logger.debug(f"save run history to {output_file}")
