import os
import re
import json
from typing import List, Dict, Optional, Union
from string import Template
from pydantic import Field
from expertdx.llms import BaseLLM, AzureOpenAIChat
from expertdx.toolkit import Toolkit
from expertdx.diagnostics import DiagnosticState, DiagnosticItem, Severity,\
    create_diagnostic_item, create_diagnostic_criteria, product_name2id, update_item_name
from expertdx.message import SystemMessage, UserMessage, ToolMessage, AssistantMessage
from expertdx.utils.debug_utils import debug_on_end
from expertdx.plot import plot_causal_graph
from .. import agent_registry
from ..tool_agent import ToolAgent, AgentAction, AgentFinish
from ..module_agent import ModuleAgent
from .prompt import ROLE_DESCRIPTION, PRODUCT_DESCRIPTION, SELECT_PROMPT, \
    EXPAND_ANALYZE_PROMPT, EXPAND_GENERATE_PROMPT, EXPAND_EXTRACT_PROMPT, \
    VERIFY_PROMPT, VERIFY_UPDATE_PROMPT, SUMMARY_PROMPT

DEBUG = True


@agent_registry.register("helper_agent")
class HelperAgent(ToolAgent):
    name = "helper_agent"
    role_description = Template(ROLE_DESCRIPTION).substitute(product_description=PRODUCT_DESCRIPTION)

    llm: BaseLLM = Field(default_factory=AzureOpenAIChat)
    toolkit: Toolkit = Field(default_factory=Toolkit)
    module_agents: List[ModuleAgent] = Field(default=[])

    task_id: str = Field(default="")

    diag_rule: List = Field(default_factory=list)
    diag_report: Dict = Field(default_factory=dict)
    diag_summary: str = Field(default="")

    data_dir: str = Field(default="data")
    history: List[dict] = Field(default=[])

    def causal_analyze(self, task_id, plot=True, consist_k: int = 3) -> DiagnosticState:
        self.task_id = task_id
        self.logger.info("[step 0: causal analysis]")

        if DEBUG:
            filename = self._get_filepath("step0_causal_graph.json")
            if os.path.exists(filename):
                self.load_history()
                with open(filename) as f:
                    causal_graph = json.load(f)
                items = DiagnosticItem.from_dict(causal_graph["nodes"])
                rels = causal_graph["edges"]
                state = DiagnosticState(diagnostic_items=items, causal_relationships=rels)
                return state

        rule_analyzer = self.toolkit.get_tool_by_name("rule_analyzer")
        state = rule_analyzer(task_id=task_id, consist_k=consist_k)
        causal_graph = {
            "nodes": state.to_list(),
            "edges": state.causal_relationships
        }

        filename = self._get_filepath("step0_causal_graph.json")
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(causal_graph, f, indent=2, ensure_ascii=False)

        # save history and plot
        step_info = {
            "step": self.iteration,
            "action": "causal_analysis",
            "node_name": None,
            "content": None,
            "diagnostic_state": state.to_dict()
        }
        self.update_history(step_info)
        self.save_history()
        if plot:
            self.plot(state, "step0_causal_analysis")

        return state

    @debug_on_end
    def select(self, state: DiagnosticState, stream=True, plot=True) -> DiagnosticItem:
        self.iteration += 1
        self.logger.info(f"[step {self.iteration}: select]")

        if DEBUG:
            filename = self._get_filepath(f"step{self.iteration}_select.json")
            if os.path.exists(filename):
                self.load_history()
                with open(filename) as f:
                    content = json.load(f)

                name = content["name"]
                item = state.get_item_by_name(name)
                item.set_possible_root_cause(not content["need_verify"])

                self.logger.info(f"[step {self.iteration}: select] `{name}`.")
                return item

        input_items = {
            "diagnostic_items": state.to_list(add_causes=True, only_not_fixed=True)
        }
        response = self.llm.generate_response(
            messages=[
                {"role": "system", "content": self.role_description},
                {"role": "user", "content": Template(SELECT_PROMPT).substitute(
                    items=json.dumps(input_items, indent=2, ensure_ascii=False))}
            ],
            stream=stream,
            response_format={"type": "json_object"},
        )
        content = json.loads(response.message.content)
        filename = self._get_filepath(f"step{self.iteration}_select.json")
        with open(filename, "w") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        total_tokens = response.total_tokens
        send_tokens = response.send_tokens
        recv_tokens = response.recv_tokens

        name = content["name"]
        item = state.get_item_by_name(name)
        item.set_possible_root_cause(not content["need_verify"])

        # save history and plot
        self.logger.info(f"[step {self.iteration}: select] `{name}`.")
        step_info = {
            "step": self.iteration,
            "action": "select",
            "node_name": name,
            "content": content,
            "diagnostic_state": state.to_dict(),
            "tokens": [send_tokens, recv_tokens, total_tokens]
        }
        self.update_history(step_info)
        self.save_history()
        if plot:
            self.plot(state, f"step{self.iteration}_select", select_name=item.name)

        return item

    @debug_on_end
    def expand(self, anomaly: DiagnosticItem, state: DiagnosticState, consist_k: int = 3,
               plot=True, stream: bool = True) -> List[DiagnosticItem]:
        self.iteration += 1
        self.logger.info(f"[step {self.iteration}: expand {anomaly.name}]")

        if DEBUG:
            analysis_filename = self._get_filepath(f"step{self.iteration}_expand_analysis.md")
            filename = self._get_filepath(f"step{self.iteration}_expand.json")
            if os.path.exists(filename):
                self.load_history()
                with open(analysis_filename) as f:
                    analysis = f.read()
                with open(filename) as f:
                    subgraph = json.load(f)

                suspects = list()
                for node in subgraph["nodes"]:
                    suspect = create_diagnostic_item(
                        name=node["name"],
                        product_id=product_name2id(node["product"]),
                        severity_status=-1,
                        expert_analysis=node["expert_analysis"],
                        expert_suggests=node["expert_suggests"]
                    )
                    suspects.append(suspect)

                # update anomaly syptom analysis
                match = re.search(r'(### Symptom Analysis.*?)(###|$)', analysis, re.DOTALL)
                try:
                    symptom_analysis = match.group(1)
                    anomaly.expert_analysis = symptom_analysis
                except AttributeError as e:
                    self.logger.warning(e)

                state.update(suspects, subgraph["edges"])
                self.logger.info(f"[step {self.iteration}: expand] "
                                 f"`{anomaly.name}` -> {[_.name for _ in suspects]}.")
                return suspects

        total_tokens, send_tokens, recv_tokens = 0, 0, 0
        # 1) analyze symptoms
        self.logger.info(f"[step {self.iteration}: expand] analysis symptoms.")
        messages = [
            {"role": "system", "content": self.role_description},
            {"role": "user", "content": Template(EXPAND_ANALYZE_PROMPT).substitute(anomaly=anomaly)},
        ]
        response = self.llm.generate_response(
            messages=messages,
            stream=stream
        )
        analysis = response.message.content
        messages.append({"role": "assistant", "content": analysis})

        total_tokens += response.total_tokens
        send_tokens += response.send_tokens
        recv_tokens += response.recv_tokens

        # 2) generate root causes
        repeated = []
        messages.append({"role": "user", "content": EXPAND_GENERATE_PROMPT})
        for i in range(consist_k):
            response = self.llm.generate_response(
                messages=messages,
                stream=stream
            )
            causes = response.message.content
            repeated.append(causes)

            total_tokens += response.total_tokens
            send_tokens += response.send_tokens
            recv_tokens += response.recv_tokens

        analysis_filename = self._get_filepath(f"step{self.iteration}_expand_analysis.md")
        with open(analysis_filename, "w") as f:
            f.write(analysis + "\n\n" + "\n\n".join(repeated))

        # 3) generate DiagnosticItems and CausalRelationships
        self.logger.info(f"[step {self.iteration}: expand] extract nodes and edges.")
        cause_analysis = "\n\n".join([f"Analysis #{i+1}\n{repeated[i]}\n" for i in range(consist_k)])

        module_names = [agent.name.split('_')[0] for agent in self.module_agents]
        lines = PRODUCT_DESCRIPTION.split('\n')
        pattern = re.compile(r'- (\w+):')
        kept_lines = []
        for line in lines:
            match = pattern.search(line)
            if match and match.group(1) in module_names:
                kept_lines.append(line)
        kept_description = '\n'.join(kept_lines)

        messages.append({"role": "user", "content": Template(EXPAND_EXTRACT_PROMPT).substitute(
            k=consist_k, anomaly=anomaly.name, cause_analysis=cause_analysis, product_description=kept_description)})

        response = self.llm.generate_response(
            messages=messages,
            stream=stream,
            response_format={"type": "json_object"},
        )
        content = response.message.content
        subgraph = json.loads(content)

        filename = self._get_filepath(f"step{self.iteration}_expand.json")
        with open(filename, "w") as f:
            json.dump(subgraph, f, indent=2, ensure_ascii=False)

        total_tokens += response.total_tokens
        send_tokens += response.send_tokens
        recv_tokens += response.recv_tokens

        # update diagnostic state
        suspects = list()
        for node in subgraph["nodes"]:
            suspect = create_diagnostic_item(
                name=node["name"],
                product_id=product_name2id(node["product"]),
                severity_status=-1,
                expert_analysis=node["expert_analysis"],
                expert_suggests=node["expert_suggests"]
            )
            suspects.append(suspect)
        state.update(suspects, subgraph["edges"])

        # update anomaly symptom analysis
        match = re.search(r'(### Symptom Analysis.*?)(###|$)', analysis, re.DOTALL)
        try:
            symptom_analysis = match.group(1)
            anomaly.expert_analysis = symptom_analysis
        except AttributeError as e:
            self.logger.warning(e)

        # save history and plot
        self.logger.info(f"[step {self.iteration}: expand] `{anomaly.name}` -> {[_.name for _ in suspects]}.")
        step_info = {
            "step": self.iteration,
            "action": "expand",
            "node_name": ",".join([node.name for node in suspects]),
            "content": {
                "analysis": analysis,
                "subgraph": subgraph
            },
            "diagnostic_state": state.to_dict(),
            "tokens": [send_tokens, recv_tokens, total_tokens]
        }
        self.update_history(step_info)
        self.save_history()
        if plot:
            self.plot(state, f"step{self.iteration}_expand", select_name=[_.name for _ in suspects])

        return suspects

    @debug_on_end
    def verify(self, item: DiagnosticItem, state: DiagnosticState, stream: bool = False, plot: bool = True) -> bool:
        self.iteration += 1
        self.logger.info(f"[step {self.iteration}: verify]")

        if DEBUG:
            filename = self._get_filepath(f"step{self.iteration}_verify.json")
            if os.path.exists(filename):
                self.load_history()
                with open(filename) as f:
                    node = json.load(f)
                update_item_name(item, state, node["name"])
                item.symptom = node["symptom"]
                item.severity = Severity[node["severity"].upper()]
                item.expert_analysis = node["expert_analysis"]
                item.expert_suggests = node["expert_suggests"]
                item.diagnostic_criteria = create_diagnostic_criteria(
                    node["diagnostic_criteria"]["name"],
                    node["diagnostic_criteria"]["type"],
                    None,
                    node["diagnostic_criteria"]["description"]
                )
                abnormal = (item.severity != Severity.NORMAL)
                self.logger.info(
                    f"[step {self.iteration}: verify] `{item.name}`: {'abnormal' if abnormal else 'normal'}")
                return abnormal

        total_tokens, send_tokens, recv_tokens = 0, 0, 0

        causal_relationship = state.get_relationships_by_cause(item.name)[0]
        effect_item = state.get_item_by_name(causal_relationship["effect"])

        tool_calls_cnt = 0
        self.memory.reset()
        self.memory.add_message(SystemMessage(content=self.role_description))
        self.memory.add_message(UserMessage(content=Template(VERIFY_PROMPT).substitute(
            anomaly_name=effect_item.name,
            cause_name=item.name,
            anomaly_analysis=effect_item.expert_analysis,
            causal_analysis=causal_relationship["description"]
        )))
        while tool_calls_cnt < self.max_tool_calls:
            response = self.llm.generate_response(
                messages=self.memory.get_messages(),
                stream=stream,
                tools=self._get_tools(),
                tool_choice="auto",
            )
            output = self._parse(response)

            total_tokens += response.total_tokens
            send_tokens += response.send_tokens
            recv_tokens += response.recv_tokens

            if isinstance(output, AgentAction):
                self.logger.info(f"Action: {output}")
                tool_calls_cnt += 1

                assistant_message = response.message
                self.memory.add_message(AssistantMessage(content=str(assistant_message.tool_calls[0].function)))

                # tool observation
                tool = self.toolkit.get_tool_by_name(output.tool)
                module_agent = self._get_module_agent_by_name(tool.belong_to)
                assert module_agent is not None, f"module agent for {tool.belong_to} not found."
                observation = module_agent.tool_call(tool, {"task_id": self.task_id})
                self.memory.add_message(ToolMessage(name=tool.name, content=observation))

            elif isinstance(output, AgentFinish):
                self.memory.add_message(UserMessage(content=output.return_values))
                self.logger.info(f"Return Values: {output.return_values}")

                summary_filename = self._get_filepath(f"step{self.iteration}_query_summary.md")
                with open(summary_filename, "w") as f:
                    f.write(output.return_values)

                break

        self.memory.add_message(UserMessage(content=VERIFY_UPDATE_PROMPT))
        response = self.llm.generate_response(
            messages=self.memory.get_messages(),
            stream=True,
            response_format={"type": "json_object"},
        )
        self.memory.add_message(UserMessage(content=response.message.content))
        node = json.loads(response.message.content)
        filename = self._get_filepath(f"step{self.iteration}_verify.json")
        with open(filename, "w") as f:
            json.dump(node, f, indent=2, ensure_ascii=False)

        update_item_name(item, state, node["name"])
        item.symptom = node["symptom"]
        item.severity = Severity[node["severity"].upper()]
        item.expert_analysis = node["expert_analysis"]
        item.expert_suggests = node["expert_suggests"]
        item.diagnostic_criteria = create_diagnostic_criteria(
            node["diagnostic_criteria"]["name"],
            node["diagnostic_criteria"]["type"],
            None,
            node["diagnostic_criteria"]["description"]
        )

        total_tokens += response.total_tokens
        send_tokens += response.send_tokens
        recv_tokens += response.recv_tokens

        mem_filename = self._get_filepath(f"step{self.iteration}_verify_memory.json")
        with open(mem_filename, "w") as f:
            json.dump({"memory": self.memory.get_messages()}, f, indent=2, ensure_ascii=False)

        # save history and plot
        abnormal = (item.severity != Severity.NORMAL)
        self.logger.info(f"[step {self.iteration}: verify] `{item.name}`: {'abnormal' if abnormal else 'normal'}")
        step_info = {
            "step": self.iteration,
            "action": "verify",
            "node_name": item.name,
            "content": self.memory.get_messages(),
            "diagnostic_state": state.to_dict(),
            "tokens": [send_tokens, recv_tokens, total_tokens]
        }
        self.update_history(step_info)
        self.save_history()
        if plot:
            self.plot(state, f"step{self.iteration}_verify", select_name=item.name)

        return abnormal

    @debug_on_end
    def summarize(self):
        self.logger.info(f"[summarize diagnostic history]")
        total_tokens, send_tokens, recv_tokens = 0, 0, 0

        filename = self._get_filepath(f"summary.txt")
        history = []

        for info in self.history:
            if info["action"] == "causal_analysis":
                history.append({
                    "step": info["step"],
                    "action": info["action"],
                    "diagnostic_state": info["diagnostic_state"],
                })
            elif info["action"] == "select":
                history.append({
                    "step": info["step"],
                    "action": info["action"],
                    "node_name": info["node_name"],
                    "content": info["content"],
                })
            elif info["action"] == "expand":
                history.append({
                    "step": info["step"],
                    "action": info["action"],
                    "node_name": info["node_name"],
                    "content": info["content"],
                })
            elif info["action"] == "verify":
                history.append({
                    "step": info["step"],
                    "action": info["action"],
                    "node_name": info["node_name"],
                    "content": info["content"],
                })

        prompt = Template(SUMMARY_PROMPT).substitute(history=json.dumps(history, indent=2, ensure_ascii=False))
        response = self.llm.generate_response(
            messages=[{"role": "system", "content": prompt}],
            stream=True,
        )
        summary_content = response.message.content
        with open(filename, "w") as f:
            f.write(summary_content)

        total_tokens += response.total_tokens
        send_tokens += response.send_tokens
        recv_tokens += response.recv_tokens
        return summary_content

    def update_history(self, step_info: dict) -> None:
        self.history.append(step_info)

    def save_history(self) -> None:
        output_file = self._get_filepath("run_history.json")
        with open(output_file, "w") as f:
            f.write(json.dumps(self.history, indent=4, ensure_ascii=False))
        self.logger.debug(f"save run history to {output_file}")

    def load_history(self) -> None:
        output_file = self._get_filepath("run_history.json")
        with open(output_file) as f:
            self.history = json.load(f)
        self.logger.debug(f"load run history from {output_file}")

    def plot(self, state: DiagnosticState, filename: str, select_name: Optional[Union[str, List]] = None):
        fig_path = self._get_filepath(f"plot/{filename}.png")
        plot_causal_graph(state, fig_path, select_name)
        self.logger.debug(f"save figure to {fig_path}")

    def _get_tools(self, **kwargs) -> List[Dict]:
        # Rule Analyzer is used once at the beginning and further excluded
        return self.toolkit.get_tool_descriptions(exclude_tools=['rule_analyzer'])

    def _get_filepath(self, filename: str) -> str:
        file_path = os.path.join(self.data_dir, f"{self.task_id}/results/{filename}")
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        return file_path

    def _get_module_agent_by_name(self, name) -> Optional[ToolAgent]:
        return next((agent for agent in self.module_agents if agent.name == name), None)


