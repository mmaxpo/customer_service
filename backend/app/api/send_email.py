from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_active_user
from app.models.schemas import UserInDB
from app.services.email_service import EmailType, send_email

router = APIRouter(prefix="/email", tags=["Email"])


# -------------------------
# Request Schema
# -------------------------
class EmailRequest(BaseModel):
    type: EmailType
    to: str
    subject: str
    html: str


# -------------------------
# Send Email Endpoint
# -------------------------
@router.post("/send")
def send_email_api(
    payload: EmailRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return send_email(
        email_type=payload.type,
        to=payload.to,
        subject=payload.subject,
        html=payload.html,
    )
