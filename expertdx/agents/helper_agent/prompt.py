ROLE_DESCRIPTION = """As an expert in diagnosing anomalies on cloud computing platforms, I need you to analyze an incidental task to identify the `root cause` and suggest solutions to prevent future recurrences.

## Background
`Root causes` refer to anomalies that (1) instigate subsequent anomalies, and (2) can be directly remedied to resolve the incident.
${product_description}

"""

SELECT_PROMPT = """
## Goal
Your goal is to analyze the current `diagnostic state` to pinpoint the `root cause` as accurately as possible. From the detected anomalies, either identify the root cause directly or select the anomaly closest to the root cause for further root cause inference.

## Expertise
Prioritize issues in the following order:
if you cannot identify the root cause directly, consider through:
1. Specificity and Clarity (anomalies regarding concrete user program error, e.g. `AccessControl...`, `ArrayIndex...`, `Broadcast...` related).
2. Explicit Description (ExitCode with rich `symptoms`, detailed `description`).
3. Severity (Prioritize confirmed anomalies over suspected ones).
4. Node Association (Point to more confirmed anomalies). 
5. Ease of Localization: Favor issues that can be easily investigated and attributed to a specific segment of code, configuration, or system component. 

Empirically, issues related to Spark and YARN are often close to the root causes.

## Output Format
Output in JSON format:
```json
{
    "name": (diagnostic_item.name),
    "analysis": (Explanation of why the current diagnostic item is chosen as the closest to the root cause),
    "need_verify_analysis": (analyze whether need further check of codes or logs to offer concrete mitigation actions),
    "need_verify": (true or false),
}
```

## Input
${items}
"""

EXPAND_ANALYZE_PROMPT = """
## Goal
Briefly understand the information in the current anomaly symptoms. For incomplete symptom descriptions, such as exit codes, analyze their meanings.
Without solutions.

## Output Format
### Symptom Analysis
1. ...

## Input
${anomaly}
"""

EXPAND_GENERATE_PROMPT = """
## Goal
Based on symptom analysis, analyze possible causes of the current anomaly, including resource configuration, user program code, ...
- The cause analysis should be as complete as possible, with no omissions.
- Order by importance from high to low: prioritize user task-related Spark configuration issues, followed by YARN resources, other issues.
- Only consider fatal causes.
- Without solutions.
- DO NOT MAKEUP.

## Output Format
### Possible Cause Analysis:
1. ...: ... 
2. ...
"""

EXPAND_EXTRACT_PROMPT = """
## Goal
Given ${k} sets of cause analysis, merge them into a JSON formatted subgraph. Extract `nodes` and `edges` from generated cause analysis, with:
- If there are cause nodes with the same meaning, only one should be retained to avoid redundancy 
- Convert each cause into a `diagnostic item`.
- Generate the causal relationship between the potential cause `diagnostic item` and the current anomaly ${anomaly}.
- Order by importance from high to low: prioritize user task-related Spark configuration issues, followed by YARN resources, other issues.
- Only consider fatal causes.

## Product Description
${product_description}

## Output Format
- Output in JSON format.
```json
{
    "nodes": [
        {
            "name": (Summarize the name of the possible `diagnostic item`),
            "product": (choose one name from `Product Description`),
            "expert_analysis": (Description of the anomaly item),
            "expert_suggests": (Suggested troubleshooting and repair measures for the anomaly),
        },
        ...
    ],
    "edges": [
    {
        "cause": (Name of the possible cause),
        "effect": ${anomaly},
        "description": (Description of how the cause might lead to the effect)
    }
}
```

## Input
${cause_analysis}
"""

VERIFY_PROMPT = """
## Goal
Your goal is to rigorously determine the **root cause**, by making multiple tool calls. 
Identify a concrete root cause, try to directly fix it, e.g., on configuration or user code. 
In each iteration, you should analyze the existing observations and then decide which tools to use next, what content needs further inspection if any and why. resolution is not necessary.

## Expertise
- A conclusive judgment requires solid factual support, based on observations from logs, metrics, user code, etc., gathered through tool usage.
- Give priority to examining user-related content (such as configuration and code/SQL), followed by content with low permissions. Then, proceed to check the Yarn resource group and cluster-related content.
- In situations lacking a clear direction, default to checking YARN Application Master (AM) logs, i.e., Spark driver logs, as a preliminary action.
- Unless there is high certainty, refrain from hastily concluding the absence of an anomaly. 

## Input
Observed Anomaly `${anomaly_name}`: `${anomaly_analysis}`
Possible Cause Analysis: `${causal_analysis}`
Your task involves a methodical approach to diagnosing and confirming the root cause of an anomaly, necessitating a strategic use of diagnostic tools and a careful analysis of their outputs.


## Output
- If further tool calls are necessary, specify which tools to use next.
- If `${cause_name}` can be definitively identified as the root cause, provide the following output:
    - If `${cause_name}` is confirmed to be anomalous:
        ```
        ### Whether Root Cause  
        true  
        
        ### Root Cause  
        (Summarize a name for the root cause type)  
        
        ### Concrete Mitigation Step
        (how to fix configuration of how to fix user code)
        
        ### Diagnostic Path Summary  
        1. (What tool was called, what results were observed, and their implications)  
        2. ...  
        
        ### Anomaly Causal Chain  
        1. (How one event led to another)  
        2. ...  
        ```
    - If `${cause_name}` is confirmed to be non-anomalous:
        ```
        ### Whether Root Cause  
        false  
        
        ### Diagnostic Path Summary  
        1. ...  
        ```
"""

VERIFY_UPDATE_PROMPT = """
## Goal
Update the given `diagnostic item` based on observation analysis.

### Input
${anomaly}

### Output format
Output in JSON format
```json
{
    "name": (Name of the diagnostic item),
    "product": (The big data component related to the diagnostic item, e.g., yarn/spark/hdfs...),
    "symptom": (The detected problem symptoms),
    "severity": (critical or normal),
    "diagnostic_criteria": {
        "type": (The basis of diagnosis, log or code),
        "name": (The names of the log or code),
        "subtype": null,
        "description": (Brief description of this diagnostic basis)
    },
    "expert_suggests": (Brief suggestions for mitigation),
    "expert_analysis": (Summarized analysis from previous analysis),
    "potential_causes": null
}
```

"""

SUMMARY_PROMPT = """As a big data system diagnostic expert, you need to summarize the following task diagnostic process. The diagnostic process includes the following action types:
- causal analysis: carry out causal analysis on exceptions captured by rules for subsequent root cause analysis of faults;
- select: choose the root cause for repair, or the fault closest to the root cause for in-depth analysis;
- expand: analyze what the possible root causes might be for a fault manifestation;
- query: for suspected root causes, analyze through tool calls whether they occur and whether they are the root cause of the task fault;

The diagnostic process is as follows:
${history}
"""

PRODUCT_DESCRIPTION = """The cloud computing platform includes multiple interconnected components:
- supersql: Unified SQL engine for cross-source data access.
- idex: Online IDE for streamlined data workflows.
- spark: In-memory computation for fast processing.
- yarn: Manages computing resources in clouds.
- us: Visual platform for distributed task scheduling and management.
- hdfs: Distributed file system for storing large datasets.
"""
