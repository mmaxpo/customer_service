from __future__ import annotations

import re
from app.tcos.planner.business_ir.factory import (
    simple_linear_plan,
    task_with_capability,
)
from app.tcos.planner.business_ir.models import BusinessPlan, BusinessTaskCategory


def build_url_summary_business_plan(goal_text: str = "") -> BusinessPlan:
    url_match = re.search(r"https?://[^\\s]+", goal_text or "")
    url = url_match.group(0) if url_match else ""

    return simple_linear_plan(
        plan_id="url_summary_plan",
        goal_id="url_summary_goal",
        goal_title="Summarize URL",
        tasks=[
            (
                lambda task: task.model_copy(
                    update={
                        "metadata": {
                            "config": {"url": url, "artifact_as": "web_extract"}
                        }
                    }
                )
            )(
                task_with_capability(
                    task_id="fetch_url",
                    name="Fetch and extract URL",
                    category=BusinessTaskCategory.ACTION,
                    capability_id="runtime.web_fetch_extract",
                )
            ),
            (
                lambda task: task.model_copy(
                    update={
                        "metadata": {
                            "config": {
                                "prompt": "Summarize this extracted webpage clearly and concisely:\n\n{{ web_extract.text }}",
                                "system": "You summarize extracted web pages. Be accurate, concise, and do not invent facts.",
                                "save_as": "summary",
                                "max_tokens": 900,
                                "token_budget_mode": "standard",
                                "fallback_from_var": "web_extract.text",
                            }
                        }
                    }
                )
            )(
                task_with_capability(
                    task_id="summarize_content",
                    name="Summarize extracted content",
                    category=BusinessTaskCategory.COMMUNICATION,
                    capability_id="runtime.llm_generate",
                )
            ),
            (
                lambda task: task.model_copy(
                    update={"metadata": {"config": {"answer_from": "summary"}}}
                )
            )(
                task_with_capability(
                    task_id="send_response",
                    name="Send summary response",
                    category=BusinessTaskCategory.COMMUNICATION,
                    capability_id="runtime.response",
                )
            ),
        ],
    )
