# from typing import Optional
# from redis.asyncio.client import Redis
# from db.config import settings
#
# redis: Optional[Redis] = None
#
# async def init_redis() -> None:
#     global redis
#     redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
#
# async def close_redis() -> None:
#     global redis
#     if redis is not None:
#         await redis.aclose()
#         redis = None
