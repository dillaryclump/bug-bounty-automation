"""
Scope Monitoring Module
Tracks bug bounty program scope changes and validates assets.
"""

from src.scope.base import BaseScopeParser, ScopeData, ScopeParserFactory
from src.scope.hackerone import HackerOneParser
from src.scope.bugcrowd import BugcrowdParser
from src.scope.comparator import ScopeComparator, ScopeComparison, ScopeChange
from src.scope.validator import ScopeValidator, ValidationResult

__all__ = [
    "BaseScopeParser",
    "ScopeData",
    "ScopeParserFactory",
    "HackerOneParser",
    "BugcrowdParser",
    "ScopeComparator",
    "ScopeComparison",
    "ScopeChange",
    "ScopeValidator",
    "ValidationResult",
]
