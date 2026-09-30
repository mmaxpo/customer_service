from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Customer,
    CustomerServiceExternalConversationLink,
)
from app.domains.customer_service.repositories.customer_identities import (
    CustomerIdentityRepository,
)


@dataclass(frozen=True, slots=True)
class CustomerIdentityEvidence:
    identity_type: str
    value: str
    namespace: str = "global"
    provider: str | None = None
    external_account_id: str | None = None
    verified: bool = False
    source: str | None = None


class CustomerIdentityConflictError(RuntimeError):
    def __init__(self, customer_ids: set[UUID]):
        self.customer_ids = frozenset(customer_ids)
        super().__init__("Customer identity evidence resolves to multiple customers")


class CustomerIdentityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerIdentityRepository(db)

    @staticmethod
    def normalize(
        *,
        identity_type: str,
        value: str,
    ) -> str:
        normalized_type = identity_type.strip().lower()
        raw = str(value).strip()

        if not raw:
            raise ValueError("Customer identity value must not be blank")

        if normalized_type == "email":
            return raw.lower()

        if normalized_type == "phone":
            has_plus = raw.startswith("+")
            digits = re.sub(r"\D", "", raw)

            if not digits:
                raise ValueError("Customer phone identity contains no digits")

            return f"+{digits}" if has_plus else digits

        return raw

    @staticmethod
    def normalize_namespace(value: str | None) -> str:
        normalized = str(value or "global").strip().lower()
        return normalized or "global"

    async def resolve_existing(
        self,
        *,
        user_id: UUID,
        evidence: list[CustomerIdentityEvidence],
    ) -> Customer | None:
        matches: dict[UUID, Customer] = {}

        for item in evidence:
            normalized_value = self.normalize(
                identity_type=item.identity_type,
                value=item.value,
            )

            namespace = self.normalize_namespace(item.namespace)

            identity = await self.repo.find(
                user_id=user_id,
                identity_type=item.identity_type.strip().lower(),
                namespace=namespace,
                normalized_value=normalized_value,
            )

            if identity is None:
                continue

            customer = await self.db.scalar(
                select(Customer).where(
                    Customer.user_id == user_id,
                    Customer.id == identity.customer_id,
                )
            )

            if customer is None:
                continue

            while customer.merged_into_id is not None:
                customer = await self.db.scalar(
                    select(Customer).where(
                        Customer.user_id == user_id,
                        Customer.id == customer.merged_into_id,
                    )
                )
                if customer is None:
                    break

            if customer is not None:
                matches[customer.id] = customer

        if len(matches) > 1:
            raise CustomerIdentityConflictError(set(matches))

        return next(iter(matches.values()), None)

    async def attach(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None,
        customer: Customer,
        evidence: list[CustomerIdentityEvidence],
    ) -> Customer:
        prepared: list[
            tuple[
                CustomerIdentityEvidence,
                str,
                str,
            ]
        ] = []

        for item in evidence:
            normalized_value = self.normalize(
                identity_type=item.identity_type,
                value=item.value,
            )

            namespace = self.normalize_namespace(item.namespace)

            prepared.append(
                (
                    item,
                    namespace,
                    normalized_value,
                )
            )

        lock_keys = sorted(
            {
                (
                    "cs_customer_identity_v2:"
                    f"{user_id}:"
                    f"{item.identity_type.strip().lower()}:"
                    f"{namespace}:"
                    f"{normalized_value}"
                )
                for item, namespace, normalized_value in prepared
            }
        )

        for lock_key in lock_keys:
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

        # Lock the customer row before attaching identities.
        #
        # Customer merge also locks source/target customer rows.
        # Therefore an identity attachment racing with a merge
        # either completes before the merge or waits, then follows
        # merged_into_id to the canonical target.
        canonical_customer = await self._canonical_customer(
            user_id=user_id,
            customer_id=customer.id,
            lock=True,
        )

        if canonical_customer is None:
            raise RuntimeError("Customer disappeared while attaching identity")

        customer = canonical_customer

        for item, namespace, normalized_value in prepared:
            existing = await self.repo.find(
                user_id=user_id,
                identity_type=(item.identity_type.strip().lower()),
                namespace=namespace,
                normalized_value=normalized_value,
            )

            if existing is not None and existing.customer_id != customer.id:
                existing_customer = await self._canonical_customer(
                    user_id=user_id,
                    customer_id=existing.customer_id,
                    lock=True,
                )

                if (
                    existing_customer is not None
                    and existing_customer.id == customer.id
                ):
                    existing.customer_id = customer.id
                    await self.db.flush()
                    continue

                raise CustomerIdentityConflictError(
                    {
                        existing.customer_id,
                        customer.id,
                    }
                )

            row = await self.repo.create_if_absent(
                user_id=user_id,
                workspace_id=workspace_id,
                customer_id=customer.id,
                identity_type=(item.identity_type.strip().lower()),
                namespace=namespace,
                value=str(item.value).strip(),
                normalized_value=normalized_value,
                provider=item.provider,
                external_account_id=(item.external_account_id),
                verified=item.verified,
                source=item.source,
            )

            if row.customer_id != customer.id:
                row_customer = await self._canonical_customer(
                    user_id=user_id,
                    customer_id=row.customer_id,
                    lock=True,
                )

                if row_customer is not None and row_customer.id == customer.id:
                    row.customer_id = customer.id
                    await self.db.flush()
                    continue

                raise CustomerIdentityConflictError(
                    {
                        row.customer_id,
                        customer.id,
                    }
                )

        return customer

    async def _canonical_customer(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        lock: bool = False,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.user_id == user_id,
            Customer.id == customer_id,
        )

        if lock:
            statement = statement.with_for_update()

        customer = await self.db.scalar(statement)

        visited: set[UUID] = set()

        while customer is not None and customer.merged_into_id is not None:
            if customer.id in visited:
                raise RuntimeError("Customer merge cycle detected")

            visited.add(customer.id)

            statement = select(Customer).where(
                Customer.user_id == user_id,
                Customer.id == customer.merged_into_id,
            )

            if lock:
                statement = statement.with_for_update()

            customer = await self.db.scalar(statement)

        return customer

    async def _resolve_legacy_customer(
        self,
        *,
        user_id: UUID,
        evidence: list[CustomerIdentityEvidence],
    ) -> Customer | None:
        """
        Transitional adoption path for customers created before the
        durable identity registry existed.

        It never merges customers automatically. If different legacy
        identity evidence resolves to different customers, resolution
        fails explicitly.
        """
        matches: dict[UUID, Customer] = {}

        for item in evidence:
            identity_type = item.identity_type.strip().lower()

            normalized_value = self.normalize(
                identity_type=identity_type,
                value=item.value,
            )

            customer_ids: set[UUID] = set()

            if identity_type == "email":
                rows = await self.db.scalars(
                    select(Customer.id).where(
                        Customer.user_id == user_id,
                        Customer.email.is_not(None),
                        func.lower(Customer.email) == normalized_value,
                    )
                )

                customer_ids.update(rows.all())

            elif identity_type == "phone":
                digits = normalized_value.lstrip("+")

                rows = await self.db.scalars(
                    select(Customer.id).where(
                        Customer.user_id == user_id,
                        Customer.phone.is_not(None),
                        func.regexp_replace(
                            Customer.phone,
                            r"\D",
                            "",
                            "g",
                        )
                        == digits,
                    )
                )

                customer_ids.update(rows.all())

            elif (
                identity_type == "provider_customer"
                and item.provider
                and item.external_account_id
            ):
                rows = await self.db.scalars(
                    select(CustomerServiceExternalConversationLink.customer_id).where(
                        CustomerServiceExternalConversationLink.user_id == user_id,
                        CustomerServiceExternalConversationLink.channel
                        == item.provider,
                        CustomerServiceExternalConversationLink.external_account_id
                        == item.external_account_id,
                        CustomerServiceExternalConversationLink.external_customer_id
                        == str(item.value).strip(),
                    )
                )

                customer_ids.update(rows.all())

            for customer_id in customer_ids:
                customer = await self._canonical_customer(
                    user_id=user_id,
                    customer_id=customer_id,
                )

                if customer is not None:
                    matches[customer.id] = customer

        if len(matches) > 1:
            raise CustomerIdentityConflictError(set(matches))

        return next(iter(matches.values()), None)

    async def resolve_or_create(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None,
        evidence: list[CustomerIdentityEvidence],
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> Customer:
        if not evidence:
            raise ValueError("Customer identity evidence is required")

        prepared = []

        for item in evidence:
            normalized = self.normalize(
                identity_type=item.identity_type,
                value=item.value,
            )
            namespace = self.normalize_namespace(item.namespace)
            prepared.append(
                (
                    item,
                    namespace,
                    normalized,
                )
            )

        lock_keys = sorted(
            {
                (
                    "cs_customer_identity_v2:"
                    f"{user_id}:"
                    f"{item.identity_type.strip().lower()}:"
                    f"{namespace}:"
                    f"{normalized}"
                )
                for item, namespace, normalized in prepared
            }
        )

        for lock_key in lock_keys:
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

        customer = await self.resolve_existing(
            user_id=user_id,
            evidence=evidence,
        )

        if customer is None:
            customer = await self._resolve_legacy_customer(
                user_id=user_id,
                evidence=evidence,
            )

        if customer is None:
            customer = Customer(
                user_id=user_id,
                workspace_id=workspace_id,
                name=(name or "").strip() or None,
                email=(
                    self.normalize(
                        identity_type="email",
                        value=email,
                    )
                    if email
                    else None
                ),
                phone=(
                    self.normalize(
                        identity_type="phone",
                        value=phone,
                    )
                    if phone
                    else None
                ),
            )

            self.db.add(customer)
            await self.db.flush()

        customer = await self.attach(
            user_id=user_id,
            workspace_id=workspace_id,
            customer=customer,
            evidence=evidence,
        )

        if not customer.email and email:
            customer.email = self.normalize(
                identity_type="email",
                value=email,
            )

        if not customer.phone and phone:
            customer.phone = self.normalize(
                identity_type="phone",
                value=phone,
            )

        if not customer.name and name:
            customer.name = name.strip() or None

        await self.db.flush()
        await self.db.refresh(customer)

        return customer
