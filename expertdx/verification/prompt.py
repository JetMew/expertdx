DECODE_PROMPT = """As an expert on cloud computing platforms, I will provide you with a `root cause` and a list of `anomalies`.
I need you to help me estimate the probability of the given root cause triggering each anomaly, on a scale from 0 to 1, where 0 means it’s impossible, and 1 means it’s certain to trigger.


## input
root cause: ${cause}

## output format
${anomalies}

## Goal
first give a **brief** analysis on each anomaly
"""


EXTRACT_PROMPT = """## Goal
Extract a 0-1 vector.

## Output
- Presented in the order of the anomalies as provided.
- Output in JSON format
```json
{
    "prediction":[...]
}
```
"""

ENCODE_PROMPT = """As an expert in cloud computing platforms, I will provide you with a `diagnosed root cause` and a list of `common root cause` names. 
I need you to help me identify which of the listed root causes are synonymous with the diagnosed root cause by returning a binary vector, where 1 indicates identical meaning and 0 indicates different meanings.


## input
diagnosed root cause: ${cause}

common root cause: ${anomalies}

## Output Format
- Presented in the order of the anomalies as provided.
- Output in JSON format
```json
{
    "prediction":[...]
}
```

"""

SAMPLED_CAUSES = [
]
