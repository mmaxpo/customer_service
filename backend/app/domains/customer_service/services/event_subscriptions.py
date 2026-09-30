from __future__ import annotations

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.event_subscriptions import (
    CustomerServiceEventSubscriptionRepository,
)
from app.domains.customer_service.schemas.event_subscriptions import (
    EventSubscriptionCreate,
    EventSubscriptionUpdate,
)
from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)
from app.platform.jobs.service import JobService


class CustomerServiceEventSubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerServiceEventSubscriptionRepository(db)

    async def create(self, *, user_id, payload: EventSubscriptionCreate):
        await self._validate_workflow_source(
            user_id=user_id,
            workflow_template_id=payload.workflow_template_id,
            workflow_json=payload.workflow_json,
        )

        return await self.repo.create(
            user_id=user_id,
            name=payload.name,
            event_type=payload.event_type,
            channel=payload.channel,
            workflow_template_id=payload.workflow_template_id,
            workflow_json=payload.workflow_json,
            filters=payload.filters,
            is_active=payload.is_active,
            meta=payload.meta,
        )

    async def list_for_user(self, *, user_id):
        return await self.repo.list_for_user(user_id=user_id)

    async def get(self, *, user_id, subscription_id):
        subscription = await self.repo.get(
            user_id=user_id,
            subscription_id=subscription_id,
        )
        if subscription is None:
            raise HTTPException(status_code=404, detail="Event subscription not found")
        return subscription

    async def update(
        self, *, user_id, subscription_id, payload: EventSubscriptionUpdate
    ):
        subscription = await self.get(
            user_id=user_id,
            subscription_id=subscription_id,
        )

        values = payload.model_dump(exclude_unset=True)

        next_workflow_template_id = values.get(
            "workflow_template_id",
            subscription.workflow_template_id,
        )
        next_workflow_json = values.get(
            "workflow_json",
            subscription.workflow_json,
        )

        await self._validate_workflow_source(
            user_id=user_id,
            workflow_template_id=next_workflow_template_id,
            workflow_json=next_workflow_json,
        )

        return await self.repo.update(
            subscription=subscription,
            values=values,
        )

    async def delete(self, *, user_id, subscription_id):
        subscription = await self.get(
            user_id=user_id,
            subscription_id=subscription_id,
        )
        await self.repo.delete(subscription=subscription)
        return None

    async def enqueue_matching_workflows_for_event(
        self,
        *,
        event,
        commit: bool = True,
    ):
        if event.user_id is None:
            return {
                "matched": 0,
                "enqueued": [],
                "skipped": True,
                "reason": "event has no user_id",
            }

        payload = event.payload or {}
        channel = payload.get("channel")

        subscriptions = await self.repo.list_active_for_event(
            user_id=event.user_id,
            event_type=event.event_type,
            channel=channel,
        )

        enqueued = []
        skipped = []

        classification = CustomerServiceMessageClassifier().classify(
            payload.get("body") or ""
        )

        matched_subscriptions = []

        for subscription in subscriptions:
            if not self._matches_filters(
                subscription_filters=subscription.filters or {},
                payload=payload,
                classification=classification,
            ):
                skipped.append(
                    {
                        "subscription_id": str(subscription.id),
                        "reason": "filters_not_matched",
                    }
                )
                continue

            matched_subscriptions.append(subscription)

        selected_subscriptions, dispatch_skipped = self._select_dispatch_subscriptions(
            matched_subscriptions
        )
        skipped.extend(dispatch_skipped)

        for subscription in selected_subscriptions:
            workflow = subscription.workflow_json

            if workflow is None and subscription.workflow_template_id is not None:
                template = await self.repo.get_template(
                    user_id=subscription.user_id,
                    template_id=subscription.workflow_template_id,
                )
                workflow = template.workflow_json if template is not None else None

            if workflow is None:
                continue

            job = await JobService(self.db).enqueue(
                user_id=subscription.user_id,
                job_type="workflow.run",
                payload=jsonable_encoder(
                    {
                        "workflow": workflow,
                        "message": payload.get("body") or "",
                        "thread_id": payload.get("conversation_id"),
                        "extras": {
                            "customer_service": True,
                            "event": {
                                "id": str(event.id),
                                "event_type": event.event_type,
                                "source": event.source,
                                "payload": payload,
                                "meta": event.meta,
                            },
                            "subscription": {
                                "id": str(subscription.id),
                                "name": subscription.name,
                            },
                            # Live version published from the automation
                            # studio; None until the first published change.
                            "workflow_version": (subscription.meta or {}).get(
                                "live_version"
                            ),
                        },
                    }
                ),
                max_attempts=3,
                commit=commit,
            )

            enqueued.append(
                {
                    "subscription_id": str(subscription.id),
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                }
            )

        return {
            # Backward-compatible meaning: active event/channel candidates
            # considered before content-filter evaluation.
            "matched": len(subscriptions),
            "filter_matched": len(matched_subscriptions),
            "selected": len(selected_subscriptions),
            "enqueued": enqueued,
            "skipped": skipped,
            "classification": classification.model_dump(),
        }

    def _select_dispatch_subscriptions(self, subscriptions):
        """
        Select subscriptions after their event/channel/content filters match.

        Dispatch modes are stored in subscription.meta:

            standard:
                Normal fan-out behavior.

            exclusive:
                Only exclusive subscriptions with the highest priority run.

            fallback:
                Runs only when no non-fallback subscription matched.

        Compatibility:
            Existing subscriptions without dispatch metadata remain standard.
            A broad fallback subscription must be explicitly marked fallback.
        """
        if not subscriptions:
            return [], []

        def dispatch_meta(subscription):
            meta = subscription.meta or {}
            mode = str(meta.get("dispatch_mode") or "standard").lower()

            if mode not in {"standard", "exclusive", "fallback"}:
                mode = "standard"

            try:
                priority = int(meta.get("dispatch_priority") or 0)
            except (TypeError, ValueError):
                priority = 0

            return mode, priority

        non_fallback = []
        fallback = []

        for subscription in subscriptions:
            mode, priority = dispatch_meta(subscription)
            item = (subscription, mode, priority)

            if mode == "fallback":
                fallback.append(item)
            else:
                non_fallback.append(item)

        candidates = non_fallback if non_fallback else fallback

        exclusive = [item for item in candidates if item[1] == "exclusive"]

        if exclusive:
            winning_priority = max(item[2] for item in exclusive)
            selected_items = [item for item in exclusive if item[2] == winning_priority]
        else:
            selected_items = candidates

        selected_ids = {str(item[0].id) for item in selected_items}

        skipped = []

        subscriptions_with_meta = [
            (subscription, *dispatch_meta(subscription))
            for subscription in subscriptions
        ]

        for subscription, mode, priority in subscriptions_with_meta:
            if str(subscription.id) in selected_ids:
                continue

            reason = (
                "fallback_suppressed"
                if mode == "fallback" and non_fallback
                else "exclusive_subscription_won"
            )

            skipped.append(
                {
                    "subscription_id": str(subscription.id),
                    "reason": reason,
                    "dispatch_mode": mode,
                    "dispatch_priority": priority,
                }
            )

        return [item[0] for item in selected_items], skipped

    def _matches_filters(
        self,
        *,
        subscription_filters: dict,
        payload: dict,
        classification,
    ) -> bool:
        if not subscription_filters:
            return True

        intent = subscription_filters.get("intent")
        if intent and str(classification.intent) != str(intent):
            return False

        ticket_priority = subscription_filters.get("ticket_priority")
        workflow = payload.get("workflow") or {}
        action = workflow.get("action") if isinstance(workflow, dict) else {}
        priority = action.get("ticket_priority") if isinstance(action, dict) else None

        if (
            ticket_priority
            and str(priority or "").lower() != str(ticket_priority).lower()
        ):
            return False

        customer_email = subscription_filters.get("customer_email")
        if customer_email:
            payload_email = (
                payload.get("customer_email") or payload.get("email") or ""
            ).lower()

            if payload_email != str(customer_email).lower():
                return False

        keywords = subscription_filters.get("keywords") or []
        if keywords:
            body = (payload.get("body") or "").lower()
            if not any(str(keyword).lower() in body for keyword in keywords):
                return False

        return True

    async def upsert_website_chat_automation_subscription(
        self,
        *,
        user_id,
        workflow_template_id,
        enabled: bool,
    ):
        name = "Website chat automation"
        event_type = "customer.chat.message.created"
        channel = "website"

        existing = await self.repo.get_by_name(
            user_id=user_id,
            event_type=event_type,
            name=name,
        )

        if workflow_template_id is None or not enabled:
            if existing is None:
                return {
                    "subscription": None,
                    "enabled": False,
                    "action": "none",
                }

            subscription = await self.repo.update(
                subscription=existing,
                values={
                    "is_active": False,
                    "meta": {
                        **(existing.meta or {}),
                        "disabled_by_widget_settings": True,
                    },
                },
            )

            return {
                "subscription": subscription,
                "enabled": False,
                "action": "disabled",
            }

        await self._validate_workflow_source(
            user_id=user_id,
            workflow_template_id=workflow_template_id,
            workflow_json=None,
        )

        values = {
            "name": name,
            "event_type": event_type,
            "channel": channel,
            "workflow_template_id": workflow_template_id,
            "workflow_json": None,
            "filters": {},
            "is_active": True,
            "meta": {
                "source": "chat_widget_settings",
                "channel": "website_chat",
                "auto_answer": True,
                "workflow_template_id": str(workflow_template_id),
                "dispatch_mode": "fallback",
                "dispatch_priority": 0,
            },
        }

        if existing is not None:
            subscription = await self.repo.update(
                subscription=existing,
                values=values,
            )

            return {
                "subscription": subscription,
                "enabled": True,
                "action": "updated",
            }

        subscription = await self.repo.create(
            user_id=user_id,
            **values,
        )

        return {
            "subscription": subscription,
            "enabled": True,
            "action": "created",
        }

    async def seed_shopify_template_subscriptions(self, *, user_id):

        template_seed = (
            await __import__(
                "app.domains.customer_service.services.workflow_templates",
                fromlist=["WorkflowTemplateService"],
            )
            .WorkflowTemplateService(self.db)
            .seed_shopify_system_templates()
        )

        template_by_name = {
            template.name: template
            for template in [
                *template_seed["created"],
                *template_seed["existing"],
            ]
        }

        definitions = [
            {
                "name": "Run Shopify refund workflow",
                "template_name": "Shopify Refund Request Workflow",
                "filters": {"keywords": ["refund"]},
            },
            {
                "name": "Run Shopify cancellation workflow",
                "template_name": "Shopify Order Cancellation Workflow",
                "filters": {"keywords": ["cancel"]},
            },
            {
                "name": "Run Shopify shipping status workflow",
                "template_name": "Shopify Shipping Status Workflow",
                "filters": {
                    "keywords": ["where is my order", "late", "tracking", "shipping"]
                },
            },
            {
                "name": "Run Shopify damaged item workflow",
                "template_name": "Shopify Damaged Item Workflow",
                "filters": {"keywords": ["damaged", "broken"]},
            },
        ]

        created = []
        existing = []

        for definition in definitions:
            current = await self.repo.get_by_name(
                user_id=user_id,
                event_type="customer_service.omnichannel.message.received",
                name=definition["name"],
            )

            if current is not None:
                current = await self.repo.update(
                    subscription=current,
                    values={
                        "filters": definition["filters"],
                        "meta": {
                            **(current.meta or {}),
                            "source": "shopify_template_seed",
                            "template_name": definition["template_name"],
                            "dispatch_mode": "exclusive",
                            "dispatch_priority": 100,
                        },
                    },
                )
                existing.append(current)
                continue

            template = template_by_name.get(definition["template_name"])

            if template is None:
                continue

            created.append(
                await self.repo.create(
                    user_id=user_id,
                    name=definition["name"],
                    event_type="customer_service.omnichannel.message.received",
                    channel=None,
                    workflow_template_id=template.id,
                    workflow_json=None,
                    filters=definition["filters"],
                    is_active=True,
                    meta={
                        "source": "shopify_template_seed",
                        "template_name": definition["template_name"],
                        "dispatch_mode": "exclusive",
                        "dispatch_priority": 100,
                    },
                )
            )

        return {
            "created": created,
            "existing": existing,
            "created_count": len(created),
            "existing_count": len(existing),
        }

    async def set_active(
        self,
        *,
        user_id,
        subscription_id,
        is_active: bool,
    ):

        subscription = await self.get(
            user_id=user_id,
            subscription_id=subscription_id,
        )

        return await self.repo.update(
            subscription=subscription,
            values={"is_active": is_active},
        )

    async def _validate_workflow_source(
        self,
        *,
        user_id,
        workflow_template_id,
        workflow_json,
    ):

        if workflow_template_id is None and workflow_json is None:
            raise HTTPException(
                status_code=422,
                detail="workflow_template_id or workflow_json is required",
            )

        if workflow_template_id is not None:
            template = await self.repo.get_template(
                user_id=user_id,
                template_id=workflow_template_id,
            )

            if template is None:
                raise HTTPException(
                    status_code=422,
                    detail="workflow_template_id must reference a published accessible template",
                )
