from pydantic import BaseModel


class OmnichannelWebhookIngest(BaseModel):
    provider: str
    payload: dict
    signature: str | None = None
