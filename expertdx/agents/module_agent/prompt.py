ANALYZE_PROMPT = """## GOAL
Briefly analyze the following observation from Tool ${name}.

### Tool Description:
${description}

### Tool Observation: 
{observation}

"""

MITIGATE_PROMPT = """## GOAL
Provide specific mitigation suggestions for the following root cause:

## Input
${anomaly}: 
"""