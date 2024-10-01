import json
from typing import Optional, List, Tuple
from pydantic import Field
from expertdx.agents import HelperAgent, ModuleAgent
from expertdx.diagnostics import DiagnosticState, DiagnosticItem, Product
from expertdx.environments.base import Environment
from . import env_registry


@env_registry.register('diagnosis')
class DiagEnvironment(Environment):
    task_id: str = Field(default="")
    helper: Optional[HelperAgent] = Field(default=None)
    state: Optional[DiagnosticState] = Field(default=None)
    offline: bool = Field(default=True)

    def __init__(self, **data):
        super().__init__(**data)

        helper = next(filter(lambda agent: agent.name == 'helper_agent', self.agents), None)
        assert helper, "must initialize a helper agent."
        self.helper = helper

    def run(self, task_id, plot=True) -> Tuple[list, str]:
        self.task_id = task_id
        self.state = self.helper.causal_analyze(task_id, plot=plot)

        root_causes = list()
        while not self.state.is_fixed():
            anomaly = self.helper.select(self.state, plot=plot)
            root_causes += self.root_cause_analyze(anomaly)

        root_causes, summary = self.helper.summarize()
        return root_causes, summary

    def root_cause_analyze(self, item: DiagnosticItem) -> List[DiagnosticItem]:
        """
        find all root causes under and mitigate the current anomaly;
        :param item: anomaly/suspect node
        :return: all root-cause nodes
        """
        if item.is_suspect():
            self.helper.verify(item, state=self.state)

        if item.is_abnormal():
            if item.is_possible_root_cause():
                while not item.is_fixed():
                    agent = self.get_module_agent(item.product)
                    fixed = agent.mitigate(self.task_id, item, state=self.state)
                    if fixed:
                        self.back_propagate(item)
                return [item, ]
            else:
                root_causes = []
                suspects = self.helper.expand(item, state=self.state)
                while not item.is_fixed():
                    suspect = suspects.pop(0)
                    root_causes += self.root_cause_analyze(suspect)
                return root_causes

    def back_propagate(self, anomaly: DiagnosticItem):
        cause = anomaly
        rels = self.state.get_relationships_by_cause(cause.name)

        for rel in rels:
            effect_name = rel["effect"]
            effect = self.state.get_item_by_name(effect_name)
            if effect.is_fixed():
                continue
            agent = self.get_module_agent(effect.product)
            is_fixed = agent.check_mitigation(data={"task_id": self.task_id, "anomaly": effect.name, "cause": anomaly.name})
            if is_fixed:
                effect.set_fixed()
                self.back_propagate(effect)

    def get_module_agent(self, product: Product) -> ModuleAgent:
        product_name = product.name.lower()
        for agent in self.agents:
            if isinstance(agent, ModuleAgent) and agent.name == f"{product_name}_agent":
                return agent
        raise ValueError(f"{product_name} not found in {[agent.name for agent in self.agents]}")