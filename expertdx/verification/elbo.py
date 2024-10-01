import json
import re
import numpy as np
from numpy import ndarray
from scipy.stats import beta, entropy
from typing import List, Dict
from string import Template
from expertdx.llms import BaseLLM
from expertdx.diagnostics import DiagnosticState, Severity
from .prompt import DECODE_PROMPT, EXTRACT_PROMPT, ENCODE_PROMPT, SAMPLED_CAUSES


def calculate_elbo(llm, causes, observation, alpha=0.5):
    """
    Calculate the ELBO value.
    """
    # Calculate the first term: log p(O|C)
    log_prob_o_given_c = calculate_log_prob_o_given_c(llm, causes, observation)

    # Simulate the prior distribution p(C)
    p_C = stick_breaking_process(alpha)

    # Infer q_phi(C|O) by ExpertDX
    q_phi_C_given_O = llm_encode(llm, causes, SAMPLED_CAUSES)

    # KL divergence calculation
    kl_divergence = entropy(q_phi_C_given_O, p_C)

    # Compute ELBO
    elbo = log_prob_o_given_c - kl_divergence

    return elbo


def calculate_log_prob_o_given_c(llm: BaseLLM, causes: List[str], observation: Dict[str, int]) -> float:
    """
    Calculate the log joint probability of the observation sequence O given condition C.
    """
    prediction = llm_decode(llm, causes, observation)
    log_prob_sum = 0
    for o_i, p_i in zip(observation.values(), prediction):
        p_i = max(min(p_i, 1 - 1e-15), 1e-15)
        log_prob_sum += o_i * np.log(p_i) + (1 - o_i) * np.log(1 - p_i)
    return log_prob_sum


def stick_breaking_process(alpha=0.5) -> ndarray:
    """
    Generate samples from a Dirichlet Process using the Stick-Breaking Process.
    """
    num_samples = len(SAMPLED_CAUSES)
    betas = beta.rvs(1, alpha, size=num_samples)
    pis = np.zeros(num_samples)
    remaining_stick_length = 1.0

    for i in range(num_samples):
        pis[i] = betas[i] * remaining_stick_length
        remaining_stick_length *= (1 - betas[i])
    return pis


def parse_diagnostic_outcome(state: DiagnosticState):
    """
    Parse cause_name, observation in diagnostic outcome.
    """
    yarn_exitcode = [0, 1, 10, 13, 15, 137, 143, -100]
    observation = {}
    for item in state.diagnostic_items:
        if item.severity is Severity.UNKNOWN:
            continue
        if item.product.name.lower() == 'yarn': # yarn exit code
            matches = re.findall(r"退出码:\s*(-?\d+)", str(item.symptom))
            code = int(matches[0])
            for exitcode in yarn_exitcode:
                observation[f"(yarn) exitcode {exitcode}"] = 1 if exitcode == code else 0
            continue
        observation[f"({item.product.name}) {item.name}"] = 0 if item.severity is Severity.NORMAL else 1

    return observation


def llm_decode(llm: BaseLLM, causes, observation) -> List[int]:
    """
    returns the probability p_i given condition C and observation o_i.
    """
    anomalies = "\n".join([f"- {k}:" for k in observation])
    messages = [{"role": "system", "content": Template(DECODE_PROMPT).substitute(
        cause=json.dumps({"root_causes": [cause.to_dict() for cause in causes]}, indent=2, ensure_ascii=False), anomalies=anomalies
    )}]
    response = llm.generate_response(
        messages=messages, stream=True
    )
    messages.append({"role": "assistant", "content": response.message.content})
    messages.append({"role": "user", "content": EXTRACT_PROMPT})
    response = llm.generate_response(
        messages=messages, stream=True, response_format={"type": "json_object"}
    )
    content = response.message.content
    prediction = json.loads(content)["prediction"]
    return prediction


def llm_encode(llm, causes, sampled_causes) -> List[int]:
    """
    return the inference of ExpertDX on sampled root causes.
    """
    anomalies = "\n".join([f"- {c}" for c in sampled_causes])
    messages = [{"role": "system", "content": Template(ENCODE_PROMPT).substitute(
        cause=json.dumps({"root_causes": [cause.to_dict() for cause in causes]}, indent=2, ensure_ascii=False), anomalies=anomalies
    )}]
    response = llm.generate_response(
        messages=messages, stream=True, response_format={"type": "json_object"}
    )
    content = response.message.content
    prediction = json.loads(content)["prediction"]
    return prediction
