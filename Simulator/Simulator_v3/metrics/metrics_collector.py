"""
Metrics collector for STM Routing Simulator v3.0.

PLACEHOLDER for Ticket #9: Metrics Collection Implementation

This is a minimal stub that allows simulation_runner.py to work without errors.
Full metrics collection functionality will be implemented in Ticket #9.
"""

from typing import Dict, Any


class MetricsCollector:
    """
    Placeholder metrics collector.
    
    This class will be fully implemented in Ticket #9 to collect:
    - Request processing times
    - Agent utilization
    - Queue statistics
    - Routing decisions
    - Wait times
    - Completion rates
    
    For now, it's a stub that does nothing but doesn't break the code.
    """
    
    def __init__(self):
        """Initialize placeholder metrics collector."""
        self._metrics: Dict[str, Any] = {
            'note': 'Full metrics collection will be implemented in Ticket #9'
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected metrics (placeholder).
        
        Returns:
            Dict containing placeholder message
        """
        return self._metrics.copy()
    
    def reset(self):
        """Reset all metrics (placeholder)."""
        self._metrics = {
            'note': 'Full metrics collection will be implemented in Ticket #9'
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return "MetricsCollector(placeholder for Ticket #9)"