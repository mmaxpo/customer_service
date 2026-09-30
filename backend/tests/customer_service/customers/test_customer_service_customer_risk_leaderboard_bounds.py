from app.domains.customer_service.services.customer_risk import CustomerRiskService


def test_customer_risk_leaderboard_candidate_limit_is_bounded():
    service = CustomerRiskService(db=None)

    assert service._leaderboard_candidate_limit(1) == 100
    assert service._leaderboard_candidate_limit(25) == 500
    assert service._leaderboard_candidate_limit(100) == 1000
