import os
import json
from typing import List, Dict, Optional
from pydantic import Field
from string import Template
from expertdx.llms import AzureOpenAIChat
from expertdx.diagnostics import DiagnosticState, DiagnosticItem, create_diagnostic_item, product_id2name
from .prompt import CAUSAL_ANALYSIS_PROMPT, CAUSAL_ANALYSIS_DEMO, SUMMARY_PROMPT, PRODUCT_DESCRIPTION
from ..base import Tool, AgentEnum
from .. import tool_registry


@tool_registry.register("rule_analyzer")
class RuleDiagTool(Tool):
    name = "rule_analyzer"
    description = "Analyze the causal relationship among the results of rule-based diagnosis."
    belong_to = AgentEnum.helper

    llm: AzureOpenAIChat

    task_id: str = Field(default="")
    diagnostic_state: Optional[DiagnosticState] = Field(default=None)
    save: bool = Field(default=True)
    offline_test: bool = Field(default=True)

    def __call__(
            self,
            task_id,
            stream=True,
            merge_runtime=True,
            **kwargs
    ) -> DiagnosticState:

        self.task_id = task_id
        rule_path = f"{self.data_dir}/{task_id}/rule_diagnostic_results.json"
        try:
            with open(rule_path) as f:
                diagnose_result = json.load(f)["productRuleList"]
        except FileNotFoundError as e:
            raise FileNotFoundError(f"rule diagnostic results file not found: {rule_path}.")

        # step 1: extract items
        self.logger.info("extract diagnostic items from rule-based diagnosis.")
        diagnostic_items = self.extract_rules_items(diagnose_result)
        self.diagnostic_state = DiagnosticState(diagnostic_items=diagnostic_items)

        # step 2: causal analysis
        self.logger.info("causal analysis.")
        causal_relationships = self.causal_analysis()
        self.diagnostic_state.causal_relationships = causal_relationships

        # # step 3: summarize (optional; llm-prompt)
        # self.summarize()

        return self.diagnostic_state

    def extract_rules_items(self, diagnose_results: List[Dict]) -> List[DiagnosticItem]:
        with open(f"{self.data_dir}/rule_descriptions/rule_description.json") as f:
            rule_description_dict = json.load(f)

        diagnostic_items = list()
        for product_rule_results in diagnose_results:
            product_id = product_rule_results["productId"]
            product_name = product_id2name(product_id).lower()
            product_rule_groups = product_rule_results["children"]

            for group in product_rule_groups:
                rules = group["children"]
                for rule in rules:
                    rule_name = rule["ruleName"]
                    rule_reason = rule["reason"]
                    rule_suggest = rule["suggest"]
                    rule_severity_status = rule["ruleResultStatus"]
                    rule_type = self.get_rule_type(group["id"])
                    symptom = rule_reason
                    expert_analysis = None
                    try:
                        rule_description = rule_description_dict[product_name][group["id"]][rule_name][
                            "description"]
                    except KeyError:
                        self.logger.debug(f"description of {product_name}: {rule_name} not found.")
                        rule_description = None
                    if product_name == "hdfs":
                        rule_severity_status = -1

                    item = create_diagnostic_item(
                        name=rule_name,
                        product_id=int(product_id),
                        diagnostic_criteria_type='rule',
                        diagnostic_criteria_subtype=rule_type,
                        diagnostic_criteria_name=rule_name,
                        diagnostic_criteria_description=rule_description,
                        symptom=symptom,
                        severity_status=int(rule_severity_status),
                        expert_suggests=rule_suggest,
                        expert_analysis=expert_analysis
                    )
                    diagnostic_items.append(item)

        return diagnostic_items

    def causal_analysis(self, stream: bool = True, consist_k: int = 3) -> Dict:
        # exclude normal nodes
        anomalies = self.diagnostic_state.get_items_by_attr(
            severity_status_list=[-1, 1, 2, 3]
        )
        anomaly_state = DiagnosticState(diagnostic_items=anomalies)
        system_prompt = Template(CAUSAL_ANALYSIS_PROMPT).substitute(product_description=PRODUCT_DESCRIPTION)
        # self-consistency
        repeated = []
        for i in range(consist_k):
            response = self.llm.generate_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content":
                        f"## Rule-based Diagnostic Results\n"
                        f"{json.dumps({'anomalies': anomaly_state.to_list()}, indent=2, ensure_ascii=False)}"
                     },
                    {"role": "user", "content": CAUSAL_ANALYSIS_DEMO},      # in-context learning
                ],
                stream=stream,
                response_format={"type": "json_object"},
            )
            content = response.message.content
            _causal_relationship = json.loads(content)["causal_relationships"]
            repeated.append(_causal_relationship)

        causal_relationships = {}
        for i in range(consist_k):
            for item in repeated[i]:
                key = (item["cause"], item["effect"])
                if key not in causal_relationships:
                    causal_relationships[key] = item["description"]
        causal_relationships = [{"cause": key[0], "effect": key[1], "description": description} for key, description in
                  causal_relationships.items()]
        return causal_relationships

    def summarize(self, state: DiagnosticState = None, stream: bool = True) -> str:
        if state is None:
            state = self.diagnostic_state

        response = self.llm.generate_response(
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content":
                    f"## Diagnostic Results\n{json.dumps(state.to_list(add_causes=True), indent=4, ensure_ascii=False)}"},
            ],
            stream=stream
        )
        summary = response.message.content

        filename = os.path.join(self.data_dir, f"{self.task_id}/results/{self.llm.model}/llm_analysis.txt")
        dir_path = os.path.dirname(filename)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(filename, "w") as f:
            f.write(summary)

        return summary

    @staticmethod
    def get_rule_type(group_name):
        if group_name.startswith('metric'):
            rule_type = 'metric-based'
        elif group_name.startswith('resource'):
            rule_type = 'resource-based'
        else:
            rule_type = 'log-based'
        return rule_type
