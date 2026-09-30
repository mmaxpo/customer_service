from pydantic import BaseModel


class CustomerRiskRead(BaseModel):
    customer_id: str
    risk_score: int
    risk_level: str
    signals: list[str]


class CustomerRiskLeaderboardItem(BaseModel):
    customer_id: str
    name: str | None = None
    risk_score: int
    risk_level: str
