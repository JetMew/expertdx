CAUSAL_ANALYSIS_PROMPT = """As an expert in anomaly diagnosis for cloud computing platforms, your task is to conduct a causality analysis on detected anomalies to guide the direction of subsequent root cause analysis.

### Output Description:
Analyze **ALL** possible causal relationships between the nodes. Each causal relationship generates an edge, which includes three fields:
```json
{  
   "cause": "The name of the diagnostic item acting as the cause",  
   "effect": "The name of the diagnostic item acting as the effect",  
   "description": "Description of how the cause might lead to the effect"  
}  
```

### Expertise Guidance:
- When conducting causality analysis, first understand the literal meaning of the "diagnostic item"; then, combine it with its symptom, expert suggestions/analysis, and "expert experience"; do not fabricate nodes.
- Be careful not to reverse cause and effect, which should be consistent with the description! However, note that two nodes may be cause and effect of each other, in which case two separate edges should be generated.
- Do not omit any details, and avoid repetitions; if there are no causal relationships, it is acceptable to return an empty set.
- Return the results in JSON format.

${product_description}
"""

CAUSAL_ANALYSIS_DEMO = """### Here are demonstrations:  
```json  
{  
  "causal_relationships": [  
    {  
      "cause": "Spark Resource Overuse",  
      "effect": "Yarn Exit",  
      "description": "Overuse of Spark resources may cause the executor on the yarn node to be overloaded. This could lead to the node not being able to report its heartbeat to the Yarn ResourceManager in time, eventually causing Yarn to exit abnormally."  
    },  
    {  
       "cause": "Yarn Abnormal termination",  
       "effect": "Spark Exception",  
       "description": "Spark tasks may not be able to obtain the resources needed..."  
    },
    {  
      "cause": "java.lang.ArrayIndexOutOfBoundsException",  
      "effect": "User class threw exception",  
      "description": "This is a clear program error, where user code attempts to access an illegal index of an array. If this access occurs within the user's Spark task code, then `User class threw exception` would be a high-level summary of this specific error."  
    },  
    ...  
  ]  
}  
```
"""

PRODUCT_DESCRIPTION = """### Expertise Guidance:
1. HDFS is a distributed file system, and a slow HDFS data node can lead to delays in YARN containers. If an "HDFS connectivity diagnosis" exists, its causal relationship should only point to "YARN abnormal termination diagnosis."
2. YARN is Hadoop's cluster resource management system, responsible for launching Spark applications and allocating the necessary resources, and reading from HDFS.
    - **YARN abnormal termination may lead to Spark abnormal termination**: Spark tasks may not be able to obtain the resources needed to run, affecting the efficiency of task execution.
    - **Spark abnormal termination may lead to YARN abnormal termination**: Issues such as code execution errors, configuration problems, or resource issues could lead to the abnormal termination of YARN tasks.
3. Spark is a unified analytics engine for large-scale data processing, running on top of YARN. The Spark driver runs in the YARN ApplicationManager (AM), and Spark executors run in YARN containers.
4. Other data access layer products
    - US (task scheduling platform), SuperSQL (big data SQL engine), IDEX (online integrated development environment), THive (data warehouse tool), etc., can submit Spark tasks for execution.
    - Abnormal terminations may be due to faults in the products themselves or may be caused by abnormal terminations of other components such as Spark/YARN/HDFS/...
"""

SUMMARY_PROMPT = """
Using your `expertise`, analyze the **root cause** of the incident based on the provided `diagnostic report`:

## Input
- `Diagnostic report` is a causal graph in JSON format: each node corresponds to a `diagnostic item`; each edge corresponds to a causal relationship between a pair of `diagnostic items`.
```json
{
    "nodes": [
        {
            "name": (Name of the `diagnostic item`),
            "product": (The big data component corresponding to the diagnostic item, e.g., yarn/spark/hdfs...),
            "diagnostic_criteria": {
                "name": (The basis of problem confirmation),
                "type": (The type of basis, e.g., rule/log/code),
                "subtype": (The category of the basis; **metric/resource-based** is based on metric computation, **log-based** is based on exception stack analysis),
                "description": (The description of this diagnostic basis)
            },
            "symptom": (The detected problem symptoms),
            "severity": (Severity of the problem),
            "expert_suggests": (Presupposed suggestions from experts, might not be complete/accurate/concrete),
            "expert_analysis": (Presupposed analysis from experts, might not be complete/accurate/concrete)
        },
        ...
    ],
    "edges": [
        {
            "cause": (Name of the `diagnostic item` acting as the cause),
            "effect": (Name of the `diagnostic item` acting as the effect),
            "description": (Description of how the cause might lead to the effect)
        },
        ...
    ] 
}
```

## Expertise
1. General Expertise:
    - The purpose of diagnosis is to identify the root cause of the problem and prevent it from recurring. The `root cause` refers to the deepest cause of the failure.

2. Specific Expertise:
    ${product_description}

## Output
1. If the root cause of the failure can be determined: output the root cause [1 item]
2. If the root cause of the failure cannot be determined based on the current information:
    1. List high-priority `diagnostic problems`, `possible causes`, and `suggestions`, sorted by importance from high to low, for further investigation. Note that you don't need to include problems that are not faulty!
    2. Please also list additional **specific** information to be collected (such as checking specific logs/checking user code/checking specific configurations, etc.), prioritize viewing the exception stack, (if necessary) user code/SQL, then logs, resources, etc. If the current problem can be resolved with high probability, this step can be ignored.
```
"""
