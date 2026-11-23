from dataclasses import dataclass, asdict
from math import isfinite


@dataclass
class NetEdgeResult:
    gross_edge: float
    total_costs: float
    risk_buffer: float
    net_edge: float
    net_edge_percent: float
    is_profitable: bool
    meets_minimum_edge: bool

    def to_dict(self):
        return asdict(self)


class NetEdgeCalculator:
    """
    Calculates net opportunity edge after estimated costs
    and risk buffer.

    All monetary values must use the same currency unit (INR).
    """

    @staticmethod
    def _validate(name: str, value: float):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric")

        if not isfinite(value):
            raise ValueError(f"{name} must be finite")

        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    def calculate(
        self,
        gross_edge: float,
        total_costs: float,
        risk_buffer: float = 0.0,
        capital_required: float = 0.0,
        minimum_net_edge: float = 0.0,
    ) -> NetEdgeResult:

        self._validate("gross_edge", gross_edge)
        self._validate("total_costs", total_costs)
        self._validate("risk_buffer", risk_buffer)
        self._validate("capital_required", capital_required)
        self._validate("minimum_net_edge", minimum_net_edge)

        net_edge = gross_edge - total_costs - risk_buffer

        if capital_required > 0:
            net_edge_percent = (net_edge / capital_required) * 100.0
        else:
            net_edge_percent = 0.0

        is_profitable = net_edge > 0

        meets_minimum_edge = net_edge >= minimum_net_edge

        return NetEdgeResult(
            gross_edge=round(gross_edge, 4),
            total_costs=round(total_costs, 4),
            risk_buffer=round(risk_buffer, 4),
            net_edge=round(net_edge, 4),
            net_edge_percent=round(net_edge_percent, 6),
            is_profitable=is_profitable,
            meets_minimum_edge=meets_minimum_edge,
        )

    def calculate_from_opportunity(self, opportunity):
        """
        Calculate net edge using an Opportunity model instance.
        Updates the opportunity's net_edge field.
        """

        result = self.calculate(
            gross_edge=opportunity.gross_edge,
            total_costs=opportunity.estimated_costs,
            risk_buffer=opportunity.risk_buffer,
            capital_required=opportunity.capital_required,
        )

        opportunity.net_edge = result.net_edge

        return result
      
