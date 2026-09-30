from uuid import uuid4

from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelOutboundDeliveryJob,
    OmnichannelOutboundDeliveryJobStatus,
)


def test_outbound_delivery_job_defaults_to_queued():
    job = OmnichannelOutboundDeliveryJob(
        conversation_id=uuid4(),
        channel="whatsapp",
        external_account_id="wa-account-1",
        external_thread_id="thread-1",
        body="Hello customer",
    )

    assert job.status == OmnichannelOutboundDeliveryJobStatus.QUEUED
    assert job.attempts == 0
    assert job.sender_type == "agent"
