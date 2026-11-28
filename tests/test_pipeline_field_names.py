"""Regression tests: real Opportunity objects must flow through
qualification, ranking and the risk gate (field-name / unit mismatches)."""

from models.opportunity import Opportunity
from ranking.opportunity_score import OpportunityScorer
from risk.risk_gate import RiskGate
from validation.qualification import OpportunityQualification


def make_opportunity(**overrides):
    values = dict(
        strategy_id="S01",
        symbol="NIFTY",
        market="NSE",
        opportunity_type="CASH_FUTURES_CARRY",
        gross_edge=100.0,
        estimated_costs=10.0,
        risk_buffer=10.0,
        net_edge=80.0,
        capital_required=50000.0,
        estimated_margin=20000.0,
        liquidity_score=80.0,
        fill_probability=0.8,
        confidence_score=0.8,
    )
    values.update(overrides)
    return Opportunity(**values)


def test_qualification_reads_confidence_score():
    result = OpportunityQualification(
        min_fill_probability=0.5, min_confidence=0.5
    ).filter_qualified([make_opportunity()])

    assert result["qualified_count"] == 1


def test_scorer_uses_model_field_names():
    opportunity = make_opportunity()
    result = OpportunityScorer().score_one(opportunity)

    assert result.components["confidence"] > 0
    assert opportunity.opportunity_score == result.score


def test_risk_gate_approves_valid_model_object_and_flags_it():
    opportunity = make_opportunity()
    OpportunityScorer().score_one(opportunity)

    approved = RiskGate().filter_approved([opportunity])

    assert approved == [opportunity]
    assert opportunity.risk_approved is True


def test_risk_gate_still_rejects_unknown_margin():
    opportunity = make_opportunity(estimated_margin=0.0)
    OpportunityScorer().score_one(opportunity)

    assert RiskGate().filter_approved([opportunity]) == []


def test_risk_gate_still_accepts_plain_dicts():
    item = {
        "strategy_id": "S01", "net_edge": 50.0, "score": 80.0,
        "confidence": 0.9, "fill_probability": 0.9, "liquidity": 1000.0,
        "capital": 10000.0, "margin": 5000.0,
    }

    assert RiskGate().filter_approved([item]) == [item]
