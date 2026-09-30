from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.security.secrets import decrypt_secret, encrypt_secret
from app.domains.customer_service.integrations.shopify.provider_factory import (
    ShopifyProviderFactory,
)
from app.domains.customer_service.models import CustomerServiceAuditLog
from app.models.models import WorkflowWait
from app.tenancy.models import Workspace
from app.domains.customer_service.providers.shopify import ShopifyProvider
from app.domains.customer_service.repositories.chat_repository import ChatRepository
from app.domains.customer_service.repositories.shopify import ShopifyRepository
from app.domains.customer_service.services.chat_service import CustomerChatService
from app.domains.customer_service.services.shopify_order_context import (
    ShopifyOrderContextBuilder,
)
from app.domains.customer_service.services.shopify_provider_installation import (
    ShopifyProviderInstallationProjector,
)
from app.domains.customer_service.services.shopify_provider_lifecycle import (
    ShopifyProviderLifecycleEvents,
)
from app.domains.customer_service.services.shopify_support_orchestrator import (
    ShopifySupportWorkflowOrchestrator,
)
from app.integrations.gateway import default_gateway


class ShopifyService:
    def __init__(
        self,
        db,
        provider: ShopifyProvider | None = None,
    ):
        self.db = db
        self.repo = ShopifyRepository(db)
        self.provider = provider or ShopifyProviderFactory.create()

    async def connect(
        self,
        *,
        user_id,
        workspace_id=None,
        shop_domain: str,
        access_token: str | None = None,
        granted_scopes: str | None = None,
    ):
        shop_domain = self._normalize_shop_domain(shop_domain)

        token_value = encrypt_secret(access_token)

        connection = await self.repo.create_connection(
            user_id=user_id,
            workspace_id=workspace_id,
            shop_domain=shop_domain,
            access_token_encrypted=token_value,
            granted_scopes=granted_scopes,
        )

        # Shopify install should make the storefront chat channel ready immediately.
        # The widget can be embedded from /app/chatbot using this generated public key.
        await CustomerChatService(
            ChatRepository(self.db)
        ).get_or_create_widget_settings(
            user_id=user_id,
        )

        installation = await ShopifyProviderInstallationProjector(
            self.db
        ).project_connected(
            user_id=user_id,
            connection_id=connection.id,
            shop_domain=(connection.shop_domain),
            has_access_token=bool(connection.access_token_encrypted),
        )

        await ShopifyProviderLifecycleEvents(self.db).connected(
            user_id=user_id,
            installation=installation,
        )

        await self.db.commit()

        return connection

    async def get_active_connection(self, *, user_id):
        active = await self.repo.list_active_connections(user_id=user_id)
        if len(active) > 1:
            raise HTTPException(
                status_code=409, detail="shopify_store_selection_required"
            )
        return active[0] if active else None

    async def list_connections(self, *, user_id):
        return await self.repo.list_active_connections(user_id=user_id)

    async def get_connection(self, *, user_id, connection_id):
        connection = await self.repo.get_connection(
            user_id=user_id, connection_id=connection_id
        )
        if connection is None:
            raise HTTPException(status_code=404, detail="Shopify connection not found")
        return connection

    async def update_connection_settings(
        self, *, user_id, connection_id, business_hours_override, timezone_override
    ):
        connection = await self.repo.update_store_settings(
            user_id=user_id,
            connection_id=connection_id,
            business_hours_override=business_hours_override,
            timezone_override=timezone_override,
        )
        if connection is None:
            raise HTTPException(status_code=404, detail="Shopify connection not found")
        return connection

    async def connection_read(self, *, connection):
        workspace = (
            await self.db.get(Workspace, connection.workspace_id)
            if connection.workspace_id is not None
            else None
        )
        return {
            "id": connection.id,
            "shop_domain": connection.shop_domain,
            "status": self._product_status(connection),
            "granted_scopes": connection.granted_scopes,
            "installed_at": connection.installed_at,
            "reauth_required_at": connection.reauth_required_at,
            "created_at": connection.created_at,
            "business_hours_override": connection.business_hours_override,
            "timezone_override": connection.timezone_override,
            "effective_business_hours": connection.business_hours_override
            if connection.business_hours_override is not None
            else getattr(workspace, "business_hours", None),
            "effective_timezone": connection.timezone_override
            or getattr(workspace, "timezone", None),
        }

    async def _resolve_connection(self, *, user_id, connection_id=None):
        if connection_id is not None:
            connection = await self.repo.get_active_connection_by_id(
                user_id=user_id, connection_id=connection_id
            )
            if connection is None:
                raise HTTPException(
                    status_code=404, detail="Shopify connection not found"
                )
            return connection
        active = await self.repo.list_active_connections(user_id=user_id)
        if len(active) > 1:
            raise HTTPException(
                status_code=409, detail="shopify_store_selection_required"
            )
        return active[0] if active else None

    async def delete_connection(self, *, user_id, connection_id):
        connection = await self.repo.deactivate_connection(
            user_id=user_id,
            connection_id=connection_id,
        )

        if connection is None:
            raise HTTPException(
                status_code=404,
                detail="Shopify connection not found",
            )

        installation = await ShopifyProviderInstallationProjector(
            self.db
        ).project_disconnected(
            user_id=user_id,
            connection_id=connection.id,
            shop_domain=(connection.shop_domain),
        )

        await ShopifyProviderLifecycleEvents(self.db).enabled_changed(
            user_id=user_id,
            installation=installation,
        )

        await self.db.commit()

        return connection

    async def test_connection(
        self,
        *,
        user_id,
        connection_id=None,
        order_ref: str | None = None,
    ) -> dict:
        connection = await self._resolve_connection(
            user_id=user_id, connection_id=connection_id
        )

        if connection is None:
            return {
                "ok": False,
                "shop_domain": None,
                "message": ("No active Shopify connection found."),
                "order_ref": order_ref,
                "order_name": None,
            }

        try:
            if order_ref:
                order = await self.get_order(
                    user_id=user_id,
                    connection_id=connection.id,
                    order_ref=order_ref,
                )
                shop = {
                    "id": None,
                    "name": None,
                    "myshopify_domain": (connection.shop_domain),
                }
                result = {
                    "ok": True,
                    "shop_domain": (connection.shop_domain),
                    "message": ("Shopify connection works and order was found."),
                    "order_ref": order_ref,
                    "order_name": order.get("order_name"),
                }
            else:
                shop = await self.provider.verify_connection(
                    shop_domain=(connection.shop_domain),
                    access_token=decrypt_secret(connection.access_token_encrypted),
                )
                result = {
                    "ok": True,
                    "shop_domain": (connection.shop_domain),
                    "message": ("Shopify credentials were verified successfully."),
                    "order_ref": None,
                    "order_name": None,
                }

            installation = await ShopifyProviderInstallationProjector(
                self.db
            ).project_verified(
                user_id=user_id,
                connection_id=(connection.id),
                shop_domain=(connection.shop_domain),
            )

            await ShopifyProviderLifecycleEvents(self.db).verified(
                user_id=user_id,
                installation=installation,
                shop=shop,
            )

            await self.db.commit()

            return result

        except Exception as exc:
            installation = await ShopifyProviderInstallationProjector(
                self.db
            ).project_verification_failed(
                user_id=user_id,
                connection_id=(connection.id),
                shop_domain=(connection.shop_domain),
                failure_message=str(exc),
            )

            await ShopifyProviderLifecycleEvents(self.db).verification_failed(
                user_id=user_id,
                installation=installation,
            )

            await self.db.commit()

            return {
                "ok": False,
                "shop_domain": (connection.shop_domain),
                "message": str(exc),
                "order_ref": order_ref,
                "order_name": None,
            }

    async def get_order(
        self,
        *,
        user_id,
        connection_id=None,
        order_ref: str,
    ) -> dict:
        connection = await self._resolve_connection(
            user_id=user_id, connection_id=connection_id
        )

        if connection is None:
            raise HTTPException(
                status_code=404,
                detail="No active Shopify connection found",
            )
        if connection.reauth_required_at is not None:
            raise HTTPException(
                status_code=401,
                detail="Shopify authorization expired; reconnect the store",
            )

        cached = await self.repo.find_cached_order(
            user_id=user_id,
            order_ref=order_ref,
            shop_domain=connection.shop_domain,
        )

        if cached is not None:
            context = (
                ShopifyOrderContextBuilder()
                .build(cached.payload)
                .model_dump(mode="json")
            )
            order_read = {
                "order_id": cached.order_id,
                "order_name": cached.order_name,
                "customer_email": cached.customer_email,
                "payload": cached.payload,
                "context": context,
            }
            order_read["summary"] = self._order_ai_summary(order_read)
            return order_read

        order = await default_gateway.call(
            provider="shopify",
            operation="get_order",
            func=lambda: self.provider.get_order(
                shop_domain=connection.shop_domain,
                access_token=decrypt_secret(connection.access_token_encrypted),
                order_ref=order_ref,
            ),
        )

        if order is None:
            raise HTTPException(status_code=404, detail="Shopify order not found")

        order_id = str(order.get("id") or order_ref)
        order_name = order.get("name")
        customer_email = order.get("email") or order.get("customer_email")

        cached = await self.repo.cache_order(
            user_id=user_id,
            shop_domain=connection.shop_domain,
            order_id=order_id,
            order_name=order_name,
            customer_email=customer_email,
            payload=order,
        )

        context = (
            ShopifyOrderContextBuilder().build(cached.payload).model_dump(mode="json")
        )
        order_read = {
            "order_id": cached.order_id,
            "order_name": cached.order_name,
            "customer_email": cached.customer_email,
            "payload": cached.payload,
            "context": context,
        }
        order_read["summary"] = self._order_ai_summary(order_read)
        return order_read

    async def get_order_fresh(
        self,
        *,
        user_id,
        connection_id=None,
        order_ref: str,
    ) -> dict:
        """
        Read current Shopify order state without using
        or writing the local order cache.

        Business-outcome verification must observe the
        provider's current state rather than a previously
        cached execution context.
        """
        connection = await self._resolve_connection(
            user_id=user_id, connection_id=connection_id
        )

        if connection is None:
            raise HTTPException(
                status_code=404,
                detail=("No active Shopify connection found"),
            )
        if connection.reauth_required_at is not None:
            raise HTTPException(
                status_code=401,
                detail="Shopify authorization expired; reconnect the store",
            )

        order = await default_gateway.call(
            provider="shopify",
            operation="get_order_fresh",
            func=lambda: self.provider.get_order(
                shop_domain=(connection.shop_domain),
                access_token=decrypt_secret(connection.access_token_encrypted),
                order_ref=order_ref,
            ),
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Shopify order not found",
            )

        return order

    async def prepare_support_workflow(
        self,
        *,
        user_id,
        connection_id=None,
        action: str,
        order_ref: str,
        reason: str | None = None,
        note: str | None = None,
        new_address: dict | None = None,
    ) -> dict:
        order_read = await self.get_order(
            user_id=user_id,
            connection_id=connection_id,
            order_ref=order_ref,
        )

        context = ShopifyOrderContextBuilder().build(
            order_read["payload"],
        )

        workflow = ShopifySupportWorkflowOrchestrator().handle(
            workflow_type=action,
            order_context=context,
            reason=reason,
            note=note,
            new_address=new_address,
        )

        return {
            "action": action,
            "order_id": order_read["order_id"],
            "order_name": order_read["order_name"],
            "context": context.model_dump(mode="json"),
            "workflow": workflow,
        }

    async def perform_order_action(
        self,
        *,
        user_id,
        connection_id=None,
        action: str,
        order_ref: str,
        reason: str | None = None,
        note: str | None = None,
        new_address: dict | None = None,
        amount: str | None = None,
        scope: dict | None = None,
        idempotency_key: str | None = None,
        approval_wait_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> dict:
        mutating_actions = {
            "refund",
            "cancel",
            "update_shipping_address",
            "reship",
            "add_note",
        }
        if action in mutating_actions and not idempotency_key:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Shopify action {action} requires an idempotency_key"
                ),
            )
        connection = await self._resolve_connection(
            user_id=user_id, connection_id=connection_id
        )
        if connection is None:
            raise HTTPException(status_code=404, detail="Shopify connection not found")
        if action in {"refund", "cancel", "reship", "update_shipping_address"} and getattr(
            self.provider, "requires_durable_approval", False
        ):
            await self._require_durable_approval(
                user_id=user_id,
                connection_id=connection.id,
                action=action,
                order_ref=order_ref,
                approval_wait_id=approval_wait_id,
                workflow_run_id=workflow_run_id,
            )
        if idempotency_key:
            lock_key = f"cs_shopify_action:{user_id}:{connection.id}:{idempotency_key}"
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

            existing = await self._find_shopify_action_by_idempotency_key(
                user_id=user_id,
                connection_id=connection.id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                return existing

        order_read = await self.get_order(
            user_id=user_id,
            connection_id=connection.id,
            order_ref=order_ref,
        )

        context = order_read.get("context") or {}
        order = (
            order_read.get("raw")
            or context.get("raw")
            or order_read.get("payload")
            or order_read
        )

        provider_kwargs = {
            "shop_domain": connection.shop_domain,
            "access_token": decrypt_secret(connection.access_token_encrypted),
            "order": order,
        }

        if action == "cancel" and context.get("can_cancel") is False:
            payload = {
                "status": "blocked",
                "message": "Order cannot be cancelled in its current state",
                "reason": reason,
            }
        elif action == "refund":
            payload = await self.provider.refund_order(
                **provider_kwargs,
                reason=reason,
                amount=amount,
                scope=scope,
            )
        elif action == "cancel":
            payload = await self.provider.cancel_order(
                **provider_kwargs,
                reason=reason,
            )
        elif action == "update_shipping_address":
            payload = await self.provider.change_order_address(
                **provider_kwargs,
                new_address=new_address or {},
                note=note,
            )
        elif action == "reship":
            payload = await self.provider.reship_order(
                **provider_kwargs,
                reason=reason,
                note=note,
                scope=scope,
            )
        elif action == "shipping_status":
            payload = await self.provider.get_shipping_status(
                **provider_kwargs,
            )
        elif action == "add_note":
            if not note or not note.strip():
                raise HTTPException(
                    status_code=422,
                    detail="Shopify action add_note requires a non-empty note",
                )
            payload = await self.provider.add_order_note(
                **provider_kwargs,
                note=note,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported Shopify action: {action}",
            )

        result = {
            "action": action,
            "order_id": order_read["order_id"],
            "order_name": order_read["order_name"],
            "status": payload.get("status", "prepared"),
            "message": payload.get("message", "Shopify action prepared"),
            "payload": payload,
            "scope": scope or {},
            "idempotency_key": idempotency_key,
        }

        if idempotency_key:
            self.db.add(
                CustomerServiceAuditLog(
                    user_id=user_id,
                    entity_type="shopify_action",
                    entity_id=None,
                    action="executed",
                    message=f"Shopify action {action} executed idempotently",
                    meta={
                        "idempotency_key": idempotency_key,
                        "connection_id": str(connection.id),
                        "shopify_action": action,
                        "order_ref": order_ref,
                        "result": result,
                    },
                )
            )
            await self.db.commit()

        return result

    async def _require_durable_approval(
        self,
        *,
        user_id,
        connection_id,
        action: str,
        order_ref: str,
        approval_wait_id: str | None,
        workflow_run_id: str | None,
    ) -> None:
        if not approval_wait_id or not workflow_run_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This Shopify action requires a resolved workflow approval. "
                    "Run it through an approval workflow."
                ),
            )
        wait = await self.db.scalar(
            select(WorkflowWait).where(
                WorkflowWait.id == approval_wait_id,
                WorkflowWait.user_id == user_id,
                WorkflowWait.workflow_run_id == str(workflow_run_id),
                WorkflowWait.wait_type == "approval",
                WorkflowWait.status == "resolved",
            )
        )
        resolution = wait.resolution if wait is not None else None
        if not isinstance(resolution, dict) or resolution.get("approved") is not True:
            raise HTTPException(
                status_code=409,
                detail="Shopify action approval is missing, rejected, or invalid",
            )
        approval_payload = wait.payload or {}
        approved_action = approval_payload.get("action")
        approved_order_ref = approval_payload.get("order_ref")
        approved_connection_id = approval_payload.get("connection_id")
        if approved_action and approved_action != action:
            raise HTTPException(
                status_code=409, detail="Approval action does not match"
            )
        if approved_order_ref and str(approved_order_ref) != str(order_ref):
            raise HTTPException(status_code=409, detail="Approval order does not match")
        if approved_connection_id and str(approved_connection_id) != str(connection_id):
            raise HTTPException(status_code=409, detail="Approval store does not match")

    async def _find_shopify_action_by_idempotency_key(
        self,
        *,
        user_id,
        connection_id=None,
        idempotency_key: str,
    ) -> dict | None:
        result = await self.db.execute(
            select(CustomerServiceAuditLog).where(
                CustomerServiceAuditLog.user_id == user_id,
                CustomerServiceAuditLog.entity_type == "shopify_action",
            )
        )

        for row in result.scalars().all():
            meta = row.meta or {}
            if meta.get("idempotency_key") == idempotency_key and (
                connection_id is None or meta.get("connection_id") == str(connection_id)
            ):
                return meta.get("result")

        return None

    async def _record_shopify_action_idempotency_result(
        self,
        *,
        user_id,
        action: str,
        order_ref: str,
        idempotency_key: str,
        result: dict,
    ) -> None:
        existing = await self._find_shopify_action_by_idempotency_key(
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return

        self.db.add(
            CustomerServiceAuditLog(
                user_id=user_id,
                entity_type="shopify_action",
                entity_id=None,
                action="executed",
                message=f"Shopify action {action} executed idempotently",
                meta={
                    "idempotency_key": idempotency_key,
                    "shopify_action": action,
                    "order_ref": order_ref,
                    "result": result,
                },
            )
        )
        await self.db.commit()

    def _order_ai_summary(self, order_read: dict) -> dict:
        context = order_read.get("context") or {}
        tracking = context.get("tracking") or {}
        items = (context.get("raw") or {}).get("line_items") or []

        return {
            "order_id": order_read.get("order_id"),
            "order_name": order_read.get("order_name"),
            "financial_status": context.get("financial_status"),
            "fulfillment_status": context.get("fulfillment_status") or "unfulfilled",
            "is_paid": context.get("is_paid"),
            "is_fulfilled": context.get("is_fulfilled"),
            "total_price": context.get("total_price"),
            "currency": context.get("currency"),
            "tracking_number": tracking.get("tracking_number"),
            "tracking_url": tracking.get("tracking_url"),
            "carrier": tracking.get("carrier"),
            "available_actions": {
                "refund": {
                    "available": bool(context.get("can_refund")),
                    "requires_human_approval": True,
                },
                "cancel": {
                    "available": bool(context.get("can_cancel")),
                    "requires_human_approval": True,
                },
                "change_address": {
                    "available": bool(context.get("can_change_address")),
                    "requires_human_approval": True,
                },
            },
            "items": [
                {
                    "name": item.get("title") or item.get("name"),
                    "quantity": item.get("quantity"),
                    "fulfillment_status": item.get("fulfillment_status"),
                }
                for item in items[:5]
                if isinstance(item, dict)
            ],
            "customer_safe_note": (
                "No tracking is available yet because the order is not fulfilled."
                if not tracking.get("tracking_number")
                and not context.get("is_fulfilled")
                else None
            ),
        }

    def _normalize_shop_domain(self, shop_domain: str) -> str:
        value = (shop_domain or "").strip().lower()
        value = value.replace("https://", "").replace("http://", "").rstrip("/")

        if not value:
            raise HTTPException(status_code=422, detail="shop_domain is required")

        return value

    @staticmethod
    def _product_status(connection) -> str:
        if connection.status != "active" or connection.revoked_at is not None:
            return "disconnected"
        if connection.reauth_required_at is not None:
            return "error"
        return "connected"
