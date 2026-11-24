
"""
India Arbitrage Lab
Scanner Module

Exports the scanner components for use by the application.
"""

from .detector import ScannerDetector
from .opportunity_scanner import OpportunityScanner

__all__ = [
    "ScannerDetector",
    "OpportunityScanner",
]
