import yaml
import json
import logging
from typing import List, Dict
from expertdx.llms import BaseLLM, llm_registry
from expertdx.tools import tool_registry
from expertdx.toolkit import Toolkit
from expertdx.agents import Agent, agent_registry
from expertdx.environments import env_registry

DATA_DIR = "data"


def load_llm(llm_config: Dict, prefix: str = "") -> BaseLLM:
    llm_type = llm_config.pop("type")
    logging.debug(f"{prefix}initialize llm: {llm_type}")
    return llm_registry.build(llm_type, **llm_config)


def load_toolkit(tool_configs: List[Dict], offline: bool = True, data_dir: str = DATA_DIR) -> Toolkit:
    toolkit = Toolkit()
    for tool_config in tool_configs:
        tool_type = tool_config.pop("type")
        tool_config["offline"] = offline
        tool_config["data_dir"] = data_dir
        if tool_type == "rule_analyzer":
            tool_config["llm"] = load_llm(tool_config.get("llm"), prefix=f"({tool_type}) ")
        toolkit.tools.append(tool_registry.build(tool_type, **tool_config))
    return toolkit


def load_agent(agent_config: Dict) -> Agent:
    agent_type = agent_config.pop("type")
    agent = agent_registry.build(agent_type, **agent_config)
    return agent


def load_env(task_id, config_path="config/local.yaml"):
    logging.info(f"load config from {config_path}")
    with open(config_path) as f:
        task_config = yaml.safe_load(f)

    env_config = task_config["environment"]
    offline = env_config["offline"]
    data_dir = env_config["data_dir"]

    products = ["spark", "yarn", "hdfs", "idex"]  # by default
    with open(f"{data_dir}/{task_id}/rule_diagnostic_results.json") as f:
        link = json.load(f)["link"]
    for prod in link:
        prod_name = prod["key"]
        if prod_name in products:
            continue
        if prod_name == "supersql":
            products.remove("idex")
            products.append(prod_name)

    helper_agent = None
    module_agents = []
    all_tools = []
    for agent_config in env_config["agents"]:
        agent_name = agent_config["name"]
        if agent_name != "helper_agent" and agent_name.split('_')[0] not in products:
            continue
        agent_config["llm"] = load_llm(agent_config.get("llm"))
        agent_config["toolkit"] = load_toolkit(agent_config.pop("tools", []), offline=offline, data_dir=data_dir)
        agent_config["data_dir"] = data_dir
        agent = load_agent(agent_config)
        logging.info(f"allocate agent: {agent.name}, toolkit: {', '.join(agent.toolkit.get_tool_names())}")

        if agent_name == 'helper_agent':
            helper_agent = agent
        else:
            module_agents.append(agent)
        all_tools.extend(agent.toolkit.get_tools())

    assert helper_agent, "must initialize a helper agent."
    helper_agent.toolkit.tools = [tool for tool in all_tools]
    helper_agent.module_agents = module_agents

    env_config["task_id"] = task_id
    env_config["agents"] = [helper_agent, ] + module_agents
    env_type = env_config.pop("type")
    env = env_registry.build(env_type, **env_config)
    return env
