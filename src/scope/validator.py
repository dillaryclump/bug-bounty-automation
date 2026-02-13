"""
Scope Validator
Validates if discovered assets are within program scope.
"""

import ipaddress
import re
from dataclasses import dataclass
from typing import List, Optional, Set

from src.scope.base import ScopeData
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of scope validation."""
    
    asset: str
    in_scope: bool
    reason: str
    matched_rule: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation."""
        status = "✓" if self.in_scope else "✗"
        msg = f"{status} {self.asset}: {self.reason}"
        if self.matched_rule:
            msg += f" (matched: {self.matched_rule})"
        return msg


class ScopeValidator:
    """
    Validate assets against program scope.
    
    Supports:
    - Exact domain matching
    - Wildcard matching (*.example.com)
    - IP address matching
    - CIDR range matching
    - Subdomain matching
    """
    
    def __init__(self, scope_data: ScopeData):
        """
        Initialize validator.
        
        Args:
            scope_data: Program scope to validate against
        """
        self.scope_data = scope_data
        
        # Prepare matching patterns
        self._prepare_patterns()
    
    def _prepare_patterns(self):
        """Prepare regex patterns and CIDR ranges for efficient matching."""
        self.in_scope_patterns = []
        self.in_scope_cidrs = []
        self.in_scope_exact = set()
        
        self.out_scope_patterns = []
        self.out_scope_cidrs = []
        self.out_scope_exact = set()
        
        # Process in-scope items
        for item in self.scope_data.in_scope:
            self._categorize_rule(
                item,
                self.in_scope_patterns,
                self.in_scope_cidrs,
                self.in_scope_exact,
            )
        
        # Process out-of-scope items
        for item in self.scope_data.out_of_scope:
            self._categorize_rule(
                item,
                self.out_scope_patterns,
                self.out_scope_cidrs,
                self.out_scope_exact,
            )
    
    def _categorize_rule(
        self,
        rule: str,
        patterns: List,
        cidrs: List,
        exact: Set,
    ):
        """Categorize a scope rule for efficient matching."""
        # Wildcard pattern
        if "*" in rule:
            # Convert wildcard to regex
            # *.example.com -> .*\.example\.com$
            pattern = re.escape(rule).replace(r"\*", ".*")
            patterns.append((rule, re.compile(f"^{pattern}$", re.IGNORECASE)))
        
        # CIDR range
        elif "/" in rule:
            try:
                network = ipaddress.ip_network(rule, strict=False)
                cidrs.append((rule, network))
            except ValueError:
                logger.warning(f"Invalid CIDR: {rule}")
        
        # Exact match
        else:
            exact.add(rule.lower())
    
    def validate(self, asset: str) -> ValidationResult:
        """
        Validate if an asset is in scope.
        
        Args:
            asset: Asset to validate (domain, subdomain, or IP)
            
        Returns:
            ValidationResult
        """
        # Normalize
        asset_lower = asset.lower().strip()
        
        # 1. Check out-of-scope first (exclusions take priority)
        
        # Exact out-of-scope match
        if asset_lower in self.out_scope_exact:
            return ValidationResult(
                asset=asset,
                in_scope=False,
                reason="Explicitly out of scope",
                matched_rule=asset_lower,
            )
        
        # Pattern out-of-scope match
        for rule, pattern in self.out_scope_patterns:
            if pattern.match(asset_lower):
                return ValidationResult(
                    asset=asset,
                    in_scope=False,
                    reason="Matches out-of-scope pattern",
                    matched_rule=rule,
                )
        
        # CIDR out-of-scope match
        if self._is_ip(asset_lower):
            try:
                ip = ipaddress.ip_address(asset_lower)
                for rule, network in self.out_scope_cidrs:
                    if ip in network:
                        return ValidationResult(
                            asset=asset,
                            in_scope=False,
                            reason="In out-of-scope CIDR range",
                            matched_rule=rule,
                        )
            except ValueError:
                pass
        
        # 2. Check in-scope
        
        # Exact in-scope match
        if asset_lower in self.in_scope_exact:
            return ValidationResult(
                asset=asset,
                in_scope=True,
                reason="Explicitly in scope",
                matched_rule=asset_lower,
            )
        
        # Pattern in-scope match
        for rule, pattern in self.in_scope_patterns:
            if pattern.match(asset_lower):
                return ValidationResult(
                    asset=asset,
                    in_scope=True,
                    reason="Matches in-scope pattern",
                    matched_rule=rule,
                )
        
        # CIDR in-scope match
        if self._is_ip(asset_lower):
            try:
                ip = ipaddress.ip_address(asset_lower)
                for rule, network in self.in_scope_cidrs:
                    if ip in network:
                        return ValidationResult(
                            asset=asset,
                            in_scope=True,
                            reason="In in-scope CIDR range",
                            matched_rule=rule,
                        )
            except ValueError:
                pass
        
        # 3. Check subdomain matching
        # If asset is subdomain of an in-scope domain, it may be in scope
        for in_scope_item in self.in_scope_exact:
            if self._is_subdomain_of(asset_lower, in_scope_item):
                return ValidationResult(
                    asset=asset,
                    in_scope=True,
                    reason="Subdomain of in-scope domain",
                    matched_rule=in_scope_item,
                )
        
        # 4. Not found in scope
        return ValidationResult(
            asset=asset,
            in_scope=False,
            reason="Not found in program scope",
        )
    
    def validate_batch(self, assets: List[str]) -> List[ValidationResult]:
        """
        Validate multiple assets.
        
        Args:
            assets: List of assets to validate
            
        Returns:
            List of ValidationResults
        """
        return [self.validate(asset) for asset in assets]
    
    def filter_in_scope(self, assets: List[str]) -> List[str]:
        """
        Filter assets to only those in scope.
        
        Args:
            assets: List of assets
            
        Returns:
            List of in-scope assets
        """
        return [
            asset
            for asset in assets
            if self.validate(asset).in_scope
        ]
    
    def filter_out_scope(self, assets: List[str]) -> List[str]:
        """
        Filter assets to only those out of scope.
        
        Args:
            assets: List of assets
            
        Returns:
            List of out-of-scope assets
        """
        return [
            asset
            for asset in assets
            if not self.validate(asset).in_scope
        ]
    
    def _is_ip(self, value: str) -> bool:
        """Check if value is an IP address."""
        return re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', value) is not None
    
    def _is_subdomain_of(self, subdomain: str, domain: str) -> bool:
        """
        Check if subdomain is a subdomain of domain.
        
        Example:
            api.example.com is subdomain of example.com
            test.api.example.com is subdomain of example.com
        """
        if subdomain == domain:
            return False
        
        return subdomain.endswith(f".{domain}")
