import os
import yaml
from expertdx.verification import LLMEval, calculate_elbo, parse_diagnostic_outcome
from expertdx.initialize import load_env, load_llm
from expertdx.utils.logging_utils import setup_logger


def run_experiment(task_id):
    output_file = f"logs/{task_id}.log"
    if not os.path.exists(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    setup_logger(output_file)

    llm_config_path = "config/llm.yaml"
    with open(llm_config_path) as f:
        task_config = yaml.safe_load(f)
    llm_config = task_config["llm"]
    llm = load_llm(llm_config)

    root_causes, state, summary = run_diagnosis(task_id)
    observation = parse_diagnostic_outcome(state)

    scores = run_llm_eval(llm, summary)
    elbo = calculate_elbo(llm, root_causes, observation)
    return scores, elbo


def run_diagnosis(task_id):
    env = load_env("config/local.yaml")
    root_causes, summary = env.run(task_id=task_id)
    return root_causes, env.state, summary


def run_llm_eval(llm, report):
    llm_eval = LLMEval(llm=llm)
    llm_eval.load_prompts()
    scores = llm_eval.evaluate(report)
    return scores
