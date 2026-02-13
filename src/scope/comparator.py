"""
Scope Comparator
Compares two scope snapshots to detect changes.
"""

from dataclasses import dataclass
from typing import List, Set

from src.db.models import ScopeChangeType
from src.scope.base import ScopeData
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScopeChange:
    """Represents a single scope change."""
    
    change_type: ScopeChangeType
    item: str
    category: str  # "in_scope" or "out_of_scope"
    details: dict = None
    
    def __str__(self) -> str:
        """String representation."""
        symbol = {
            ScopeChangeType.ADDED: "+",
            ScopeChangeType.REMOVED: "-",
            ScopeChangeType.MODIFIED: "~",
        }.get(self.change_type, "?")
        
        return f"{symbol} [{self.category}] {self.item}"


@dataclass
class ScopeComparison:
    """Results from comparing two scope snapshots."""
    
    changes: List[ScopeChange]
    additions: List[ScopeChange]
    removals: List[ScopeChange]
    modifications: List[ScopeChange]
    unchanged_in_scope: Set[str]
    unchanged_out_scope: Set[str]
    has_changes: bool
    
    def summary(self) -> str:
        """Generate a summary string."""
        if not self.has_changes:
            return "No scope changes detected"
        
        parts = []
        if self.additions:
            parts.append(f"{len(self.additions)} added")
        if self.removals:
            parts.append(f"{len(self.removals)} removed")
        if self.modifications:
            parts.append(f"{len(self.modifications)} modified")
        
        return ", ".join(parts)


class ScopeComparator:
    """
    Compare scope snapshots to detect changes.
    
    Detects:
    - Additions: Items in current but not in previous
    - Removals: Items in previous but not in current
    - Modifications: Items that moved between in-scope and out-of-scope
    """
    
    def compare(
        self,
        previous: ScopeData,
        current: ScopeData,
    ) -> ScopeComparison:
        """
        Compare two scope snapshots.
        
        Args:
            previous: Previous scope snapshot
            current: Current scope snapshot
            
        Returns:
            ScopeComparison with detected changes
        """
        logger.info(
            f"Comparing scope: {previous.program_handle} "
            f"(prev checksum: {previous.checksum()[:8]}... "
            f"vs curr checksum: {current.checksum()[:8]}...)"
        )
        
        # Quick check: if checksums match, no changes
        if previous.checksum() == current.checksum():
            logger.info("Checksums match - no changes")
            return ScopeComparison(
                changes=[],
                additions=[],
                removals=[],
                modifications=[],
                unchanged_in_scope=set(current.in_scope),
                unchanged_out_scope=set(current.out_of_scope),
                has_changes=False,
            )
        
        # Convert to sets for efficient comparison
        prev_in = set(previous.in_scope)
        curr_in = set(current.in_scope)
        prev_out = set(previous.out_of_scope)
        curr_out = set(current.out_of_scope)
        
        changes = []
        additions = []
        removals = []
        modifications = []
        
        # Detect additions to in-scope
        for item in curr_in - prev_in:
            # Check if it moved from out-of-scope
            if item in prev_out:
                change = ScopeChange(
                    change_type=ScopeChangeType.MODIFIED,
                    item=item,
                    category="in_scope",
                    details={"from": "out_of_scope", "to": "in_scope"},
                )
                modifications.append(change)
            else:
                change = ScopeChange(
                    change_type=ScopeChangeType.ADDED,
                    item=item,
                    category="in_scope",
                )
                additions.append(change)
            changes.append(change)
        
        # Detect removals from in-scope
        for item in prev_in - curr_in:
            # Check if it moved to out-of-scope
            if item in curr_out:
                # Already handled in modifications above
                if item not in prev_out:
                    change = ScopeChange(
                        change_type=ScopeChangeType.MODIFIED,
                        item=item,
                        category="out_of_scope",
                        details={"from": "in_scope", "to": "out_of_scope"},
                    )
                    modifications.append(change)
                    changes.append(change)
            else:
                change = ScopeChange(
                    change_type=ScopeChangeType.REMOVED,
                    item=item,
                    category="in_scope",
                )
                removals.append(change)
                changes.append(change)
        
        # Detect additions to out-of-scope
        for item in curr_out - prev_out:
            # Skip if already handled as modification
            if item not in prev_in:
                change = ScopeChange(
                    change_type=ScopeChangeType.ADDED,
                    item=item,
                    category="out_of_scope",
                )
                additions.append(change)
                changes.append(change)
        
        # Detect removals from out-of-scope
        for item in prev_out - curr_out:
            # Skip if already handled as modification
            if item not in curr_in:
                change = ScopeChange(
                    change_type=ScopeChangeType.REMOVED,
                    item=item,
                    category="out_of_scope",
                )
                removals.append(change)
                changes.append(change)
        
        # Unchanged items
        unchanged_in = prev_in & curr_in
        unchanged_out = prev_out & curr_out
        
        has_changes = len(changes) > 0
        
        logger.info(
            f"Comparison complete: {len(additions)} added, "
            f"{len(removals)} removed, {len(modifications)} modified"
        )
        
        return ScopeComparison(
            changes=changes,
            additions=additions,
            removals=removals,
            modifications=modifications,
            unchanged_in_scope=unchanged_in,
            unchanged_out_scope=unchanged_out,
            has_changes=has_changes,
        )
    
    def format_changes(self, comparison: ScopeComparison) -> str:
        """
        Format changes as a readable string.
        
        Args:
            comparison: Comparison result
            
        Returns:
            Formatted string
        """
        if not comparison.has_changes:
            return "No changes detected"
        
        lines = [comparison.summary(), ""]
        
        if comparison.additions:
            lines.append("Additions:")
            for change in sorted(comparison.additions, key=lambda c: c.item):
                lines.append(f"  {change}")
            lines.append("")
        
        if comparison.removals:
            lines.append("Removals:")
            for change in sorted(comparison.removals, key=lambda c: c.item):
                lines.append(f"  {change}")
            lines.append("")
        
        if comparison.modifications:
            lines.append("Modifications:")
            for change in sorted(comparison.modifications, key=lambda c: c.item):
                details = change.details or {}
                from_cat = details.get("from", "unknown")
                to_cat = details.get("to", "unknown")
                lines.append(f"  ~ {change.item} ({from_cat} -> {to_cat})")
            lines.append("")
        
        return "\n".join(lines)
