import app.domains.customer_service.models as models


def test_customer_service_models_are_exported_from_package():
    expected = {
        "Customer",
        "Conversation",
        "ConversationMessage",
        "Ticket",
        "SLAPolicy",
        "SLAViolation",
        "TicketAssignment",
        "CustomerServiceAgent",
        "CustomerServiceTeam",
        "CustomerServiceQueue",
        "CustomerServiceShopifyConnection",
        "CustomerServiceChannelConnection",
        "CustomerServiceWorkflowTemplate",
    }

    for name in expected:
        assert hasattr(models, name), name


def test_customer_service_model_tables_are_stable():
    assert models.Customer.__tablename__ == "cs_customers"
    assert models.Conversation.__tablename__ == "cs_conversations"
    assert models.ConversationMessage.__tablename__ == "cs_conversation_messages"
    assert models.Ticket.__tablename__ == "cs_tickets"
    assert models.CustomerServiceAgent.__tablename__ == "cs_agents"
    assert models.CustomerServiceTeam.__tablename__ == "cs_teams"
    assert models.CustomerServiceQueue.__tablename__ == "cs_queues"
