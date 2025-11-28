"""
Absent Agent Manager

Manages which agents are marked as absent each simulation day.
Randomly selects a percentage of agents to be absent with equal probability.
"""

import random
from typing import List, Set
from datetime import datetime
import logging

from models import Agent

logger = logging.getLogger("simulation")


class AbsentAgentManager:
    """
    Manages agent absence during simulation.
    
    Randomly selects a configured percentage of agents to be absent each day,
    ensuring each agent has equal probability of being selected.
    """
    
    def __init__(
        self,
        agents: List[Agent],
        absent_percentage: float = 0.1,
        random_seed: int = None
    ):
        """
        Initialize absent agent manager.
        
        Args:
            agents: List of all agents in simulation
            absent_percentage: Percentage of agents to mark absent (0.0-1.0)
            random_seed: Random seed for reproducibility (None = random)
        """
        self.agents = agents
        self.absent_percentage = absent_percentage
        self.current_absent_ids: Set[str] = set()
        self.last_rotation_day: int = -1
        
        # Set random seed if provided
        if random_seed is not None:
            random.seed(random_seed)
        
        logger.info(f"AbsentAgentManager initialized: {len(agents)} agents, "
                   f"{absent_percentage*100:.1f}% absent rate")
    
    def rotate_absent_agents(self, current_time: datetime) -> None:
        """
        Rotate absent agents if a new day has started.
        
        Randomly selects agents to be absent for the new day.
        
        Args:
            current_time: Current simulation time
        """
        current_day = current_time.day
        
        # Check if we need to rotate (new day)
        if current_day != self.last_rotation_day:
            self._select_new_absent_agents()
            self.last_rotation_day = current_day
            logger.info(f"Day {current_day}: Rotated absent agents - "
                       f"{len(self.current_absent_ids)} agents now absent")
    
    def _select_new_absent_agents(self) -> None:
        """
        Randomly select agents to be absent.
        
        Each agent has equal probability of being selected.
        """
        # Calculate how many agents should be absent
        num_absent = int(len(self.agents) * self.absent_percentage)
        
        # Randomly select agents
        absent_agents = random.sample(self.agents, num_absent)
        
        # Update absent status
        self.current_absent_ids = {agent.agent_id for agent in absent_agents}
        
        # Mark agents as absent/present
        for agent in self.agents:
            agent.is_absent = (agent.agent_id in self.current_absent_ids)
    
    def get_absent_agent_ids(self) -> List[str]:
        """
        Get list of currently absent agent IDs.
        
        Returns:
            List[str]: Agent IDs of currently absent agents
        """
        return list(self.current_absent_ids)
    
    def is_agent_absent(self, agent_id: str) -> bool:
        """
        Check if specific agent is currently absent.
        
        Args:
            agent_id: Agent ID to check
            
        Returns:
            bool: True if agent is absent
        """
        return agent_id in self.current_absent_ids
    
    def get_statistics(self) -> dict:
        """
        Get absence statistics.
        
        Returns:
            dict: Statistics about agent absence
        """
        return {
            'total_agents': len(self.agents),
            'absent_count': len(self.current_absent_ids),
            'absent_percentage': len(self.current_absent_ids) / len(self.agents) if self.agents else 0,
            'absent_agent_ids': list(self.current_absent_ids)
        }