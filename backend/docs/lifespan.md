## Good to keep in lifespan
- Postgres pool/engine (business DB)
- Redis client
- LangGraph checkpointer (saver)
- Queue connection (RabbitMQ)
- LLM client (OpenAI/Anthropic SDK client)
- Observability (tracer, metrics)

## What lifespan guarantees
- Runs on startup of the FastAPI app for that worker process
- Runs before requests are served (for that worker)
- Runs again for each worker if you run --workers N
- Ensures proper cleanup on shutdown (your context manager handles it)

