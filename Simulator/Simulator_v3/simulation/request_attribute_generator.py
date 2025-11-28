"""
Request Attribute Generator

Generates random attributes for requests to simulate production behavior:
- Customer replies
- Internal notes
- Tags (LOCKED, etc.)
- Follow-up dates
- Expected completion dates
- Sticky agent assignments
"""

import random
from typing import List
from datetime import datetime, timedelta
import logging

from models import Request, Agent

logger = logging.getLogger("simulation")


class RequestAttributeGenerator:
    """
    Generates random attributes for requests based on configured probabilities.
    
    Simulates production request states like customer replies, internal notes,
    follow-up dates, etc.
    """
    
    def __init__(
        self,
        customer_reply_prob: float = 0.15,
        internal_note_prob: float = 0.20,
        locked_tag_prob: float = 0.05,
        followup_date_prob: float = 0.30,
        expected_completion_date_prob: float = 0.25,
        sticky_assignment_prob: float = 0.40,
        random_seed: int = None
    ):
        """
        Initialize attribute generator.
        
        Args:
            customer_reply_prob: Probability of 'customerreplied' status
            internal_note_prob: Probability of 'NEW_INTERNAL_NOTE' tag
            locked_tag_prob: Probability of 'LOCKED' tag
            followup_date_prob: Probability of follow-up date being set
            expected_completion_date_prob: Probability of ECD being set
            sticky_assignment_prob: Probability of sticky agent assignment
            random_seed: Random seed for reproducibility
        """
        self.customer_reply_prob = customer_reply_prob
        self.internal_note_prob = internal_note_prob
        self.locked_tag_prob = locked_tag_prob
        self.followup_date_prob = followup_date_prob
        self.expected_completion_date_prob = expected_completion_date_prob
        self.sticky_assignment_prob = sticky_assignment_prob
        
        if random_seed is not None:
            random.seed(random_seed)
        
        logger.info(f"RequestAttributeGenerator initialized with probabilities: "
                   f"customer_reply={customer_reply_prob:.2f}, "
                   f"internal_note={internal_note_prob:.2f}")
    
    def generate_attributes(
        self,
        request: Request,
        agents: List[Agent],
        current_time: datetime
    ) -> None:
        """
        Generate random attributes for a request.
        
        Modifies the request in-place, adding random attributes based on
        configured probabilities.
        
        Args:
            request: Request to modify
            agents: List of agents (for sticky assignment)
            current_time: Current simulation time
        """
        # Status: customerreplied or keep as 'new'
        if random.random() < self.customer_reply_prob:
            request.workorder_status = "customerreplied"
        
        # Tags
        if random.random() < self.internal_note_prob:
            request.add_tag("NEW_INTERNAL_NOTE")
        
        if random.random() < self.locked_tag_prob:
            request.add_tag("LOCKED")
        
        # Follow-up date (1-14 days in the future)
        if random.random() < self.followup_date_prob:
            days_ahead = random.uniform(1, 14)
            request.workorder_followup_date = current_time + timedelta(days=days_ahead)
        
        # Expected completion date (2-21 days in the future)
        if random.random() < self.expected_completion_date_prob:
            days_ahead = random.uniform(2, 21)
            request.workorder_expected_completion_date = current_time + timedelta(days=days_ahead)
        
        # Sticky agent assignment
        if random.random() < self.sticky_assignment_prob and agents:
            # Assign to random agent with matching skill
            matching_agents = [a for a in agents if request.skill_id in a.skillsets]
            if matching_agents:
                sticky_agent = random.choice(matching_agents)
                request.sticky_agent_id = sticky_agent.agent_id
    
    def generate_batch(
        self,
        requests: List[Request],
        agents: List[Agent],
        current_time: datetime
    ) -> None:
        """
        Generate attributes for a batch of requests.
        
        Args:
            requests: List of requests to process
            agents: List of agents (for sticky assignment)
            current_time: Current simulation time
        """
        for request in requests:
            self.generate_attributes(request, agents, current_time)
        
        logger.info(f"Generated attributes for {len(requests)} requests")