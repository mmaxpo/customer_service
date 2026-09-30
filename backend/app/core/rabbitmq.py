# import aio_pika
# from db.config import settings
#
# async def rabbitmq_ping() -> bool:
#     connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
#     try:
#         channel = await connection.channel()
#         await channel.declare_queue("healthcheck", durable=False, auto_delete=True)
#         return True
#     finally:
#         await connection.close()
