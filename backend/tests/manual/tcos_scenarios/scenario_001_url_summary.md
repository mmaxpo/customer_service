# Scenario 001 — URL Summary

Goal:
Summarize this URL for me: https://example.com

Expected:
- Cognitive status: completed
- Planner status: compiled
- Runtime status: ok
- web_extract exists
- summary exists
- answer equals summary
- final answer is not empty

Current result:
PASSED manually.

Observed improvements made:
- response artifact answer_from translated to runtime vars/answer_key
- llm.generate fallback_from_var added for empty provider output
- URL summary LLM budget increased
