
"""
India Arbitrage Lab
Opportunity Validator

Validates arbitrage opportunity data before qualification.
Research and paper-trading use only.
"""

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Dict, List, Optional


VALID_STRATEGY_IDS = {f"S{i:02d}" for i in range(1, 11)}


@dataclass
class ValidationIssue:
    code: str
    message: str
    field: Optional[str] = None
    severity: str = "error"


@dataclass
class ValidationReport:
    is_valid: bool
    opportunity_id: Optional[str]
    strategy_id: Optional[str]
    issues: List[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "opportunity_id": self.opportunity_id,
            "strategy_id": self.strategy_id,
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "field": issue.field,
                    "severity": issue.severity,
                }
                for issue in self.issues
            ],
        }


class OpportunityValidator:
    """Validate opportunity objects or dictionaries."""

    REQUIRED_FIELDS = ("strategy_id", "net_edge")

    NUMERIC_FIELDS = (
        "gross_edge",
        "estimated_costs",
        "costs",
        "risk_buffer",
        "net_edge",
        "capital_required",
        "margin_required",
        "liquidity",
        "fill_probability",
        "confidence",
        "score",
    )

    def __init__(self, require_legs=False, require_positive_net_edge=True):
        self.require_legs = require_legs
        self.require_positive_net_edge = require_positive_net_edge

    @staticmethod
    def _get(obj, field_name, default=None):
        if isinstance(obj, dict):
            return obj.get(field_name, default)
        return getattr(obj, field_name, default)

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            return False
        return isinstance(value, (int, float)) and isfinite(value)

    def validate(self, opportunity) -> ValidationReport:
        issues = []

        strategy_id = self._get(opportunity, "strategy_id")
        opportunity_id = self._get(opportunity, "opportunity_id")
        if opportunity_id is None:
            opportunity_id = self._get(opportunity, "id")

        # Required field checks
        for field_name in self.REQUIRED_FIELDS:
            value = self._get(opportunity, field_name)
            if value is None:
                issues.append(ValidationIssue(
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Required field '{field_name}' is missing.",
                    field=field_name,
                ))

        # Strategy ID validation
        if strategy_id is not None:
            normalized_id = str(strategy_id).upper()
            if normalizedized_id if False else False:
    pass
            normalized_id = str(strategy_id).upper()

if normalized_id not in VALID_STRATEGY_IDS:
    issues.append(ValidationIssue(
        code="INVALID_STRATEGY_ID",
        message=f"Unknown strategy ID: {strategy_id}",
        field="strategy_id",
    ))

        # Numeric field checks
        for field_name in self.NUMERIC_FIELDS:
            value = self._get(opportunity, field_name)

            if value is None:
                continue

            if not self._number(value):
                issues.append(ValidationIssue(
                    code="INVALID_NUMERIC_VALUE",
                    message=f"'{field_name}' must be a finite number.",
                    field=field_name,
                ))

        # Non-negative field checks
        non_negative_fields = (
            "estimated_costs",
            "costs",
            "risk_buffer",
            "capital_required",
            "margin_required",
            "liquidity",
        )

        for field_name in non_negative_fields:
            value = self._get(opportunity, field_name)

            if value is not None and self._number(value) and value < 0:
                issues.append(ValidationIssue(
                    code="NEGATIVE_VALUE",
                    message=f"'{field_name}' cannot be negative.",
                    field=field_name,
                ))

        # Probability and confidence range checks
        for field_name in ("fill_probability", "confidence"):
            value = self._get(opportunity, field_name)

            if value is not None and self._number(value):
                if not 0 <= value <= 1:
                    issues.append(ValidationIssue(
                        code="OUT_OF_RANGE",
                        message=f"'{field_name}' must be between 0 and 1.",
                        field=field_name,
                    ))

        # Optional positive net-edge check
        net_edge = self._get(opportunity, "net_edge")

        if (
            self.require_positive_net_edge
            and self._number(net_edge)
            and net_edge <= 0
        ):
            issues.append(ValidationIssue(
                code="NON_POSITIVE_NET_EDGE",
                message="Net edge must be positive.",
                field="net_edge",
            ))

        # Legs check
        legs = self._get(opportunity, "legs")

        if self.require_legs:
            if not legs:
                issues.append(ValidationIssue(
                    code="MISSING_LEGS",
                    message="Opportunity must contain at least one trade leg.",
                    field="legs",
                ))
        elif legs is not None and not isinstance(legs, (list, tuple)):
            issues.append(ValidationIssue(
                code="INVALID_LEGS_FORMAT",
                message="Legs must be a list or tuple when supplied.",
                field="legs",
            ))

        return ValidationReport(
            is_valid=not any(i.severity == "error" for i in issues),
            opportunity_id=opportunity_id,
            strategy_id=strategy_id,
            issues=issues,
        )

    def validate_many(self, opportunities) -> List[ValidationReport]:
        return [self.validate(item) for item in opportunities]

    def filter_valid(self, opportunities):
        valid = []
        invalid = []
        reports = []

        for opportunity in opportunities:
            report = self.validate(opportunity)
            reports.append(report)

            if report.is_valid:
                valid.append(opportunity)
            else:
                invalid.append(opportunity)

        return {
            "valid": valid,
            "invalid": invalid,
            "reports": reports,
            "valid_count": len(valid),
            "invalid_count": len(invalid),
        }
      
