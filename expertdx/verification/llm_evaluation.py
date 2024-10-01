import os
import re
import json
from string import Template
from pydantic import Field, BaseModel
from expertdx.llms import AzureOpenAIChat


class LLMEval(BaseModel):
    llm: AzureOpenAIChat
    acc_prompt: str = Field(default="")
    coh_prompt: str = Field(default="")
    con_prompt: str = Field(default="")
    rel_prompt: str = Field(default="")

    def load_prompts(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
        with open(os.path.join(path, "accuracy.txt")) as f:
            self.acc_prompt = f.read()
        with open(os.path.join(path, "coherence.txt")) as f:
            self.coh_prompt = f.read()
        with open(os.path.join(path, "consistency.txt.txt")) as f:
            self.con_prompt = f.read()
        with open(os.path.join(path, "relevance.txt")) as f:
            self.rel_prompt = f.read()

    def evaluate_metric(self, report, metric="coherence"):
        if metric == "coherence":
            prompt = Template(self.coh_prompt)
        elif metric == "consistency.txt":
            prompt = Template(self.con_prompt)
        elif metric == "relevance":
            prompt = Template(self.rel_prompt)
        else:
            raise NotImplementedError(f"invalid automated metric: {metric}.")

        input_content = prompt.substitute(report=report)
        response = self.llm.generate_response(
            messages=[{"role": "system", "content": input_content}], stream=True
        )
        content = response.message.content

        pattern = rf"- {metric.capitalize()} Score: (\d+)"
        match = re.search(pattern, content)
        if match:
            score = match.group(1)
            print(f"{metric.capitalize()} Score:", score)
            return score, content
        else:
            try:
                score = int(content)
                print(f"{metric.capitalize()} Score:", score)
                return score, content
            except:
                raise NotImplementedError(f"{metric.capitalize()} score not found in content\n{content}.")

    def evaluate(self, report):
        scores = []
        for metric in ["coherence", "consistency.txt", "relevance"]:
            score, content = self.evaluate_metric(report, metric)
            scores.append(score)

        return scores
