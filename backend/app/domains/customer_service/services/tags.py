from app.domains.customer_service.repositories.tags import ConversationTagRepository


class ConversationTagService:
    def __init__(self, db):
        self.repo = ConversationTagRepository(db)

    async def add_tag(self, *, user_id, conversation_id, name: str):
        return await self.repo.add(
            user_id=user_id,
            conversation_id=conversation_id,
            name=name,
        )

    async def list_tags(self, *, user_id, conversation_id):
        return await self.repo.list_for_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def remove_tag(self, *, user_id, conversation_id, name: str):
        return await self.repo.remove(
            user_id=user_id,
            conversation_id=conversation_id,
            name=name,
        )
