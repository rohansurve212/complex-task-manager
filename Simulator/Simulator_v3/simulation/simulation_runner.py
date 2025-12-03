"""
Main simulation runner for STM Routing Simulator v3.0.

This module orchestrates the entire discrete event simulation, including:
- Initialization of all components
- Pre-loading initial request pool
- Daily absent agent rotation
- Agent processes (placeholder for Ticket #8)
- Metrics collection
- Results reporting
"""

from datetime import datetime
from typing import List, Dict, Optional
import logging

from simulation.simulation_environment import SimulationEnvironment, SimulationState
from simulation.absent_agent_manager import AbsentAgentManager
from simulation.request_attribute_generator import RequestAttributeGenerator
from simulation.time_utils import get_next_day_start, get_current_datetime
from models.agent import Agent
from models.request import Request
from models.request_pool import RequestPool
from config.scenario_config import ScenarioConfig
from metrics.metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimulationRunner:
    """
    Main simulation orchestrator for STM Routing Simulator.
    
    This class manages the entire simulation lifecycle:
    1. Initialize all components (agents, requests, managers, metrics)
    2. Pre-load initial request pool with realistic attributes
    3. Set up daily rotation for absent agents
    4. Run agent processes (handling requests)
    5. Collect metrics throughout simulation
    6. Return final results
    
    Attributes:
        config (ScenarioConfig): Scenario configuration
        sim_env (SimulationEnvironment): SimPy environment wrapper
        agents (List[Agent]): List of agents
        request_pool (RequestPool): Pool of pending requests
        absent_manager (AbsentAgentManager): Manages absent agents
        metrics_collector (MetricsCollector): Collects simulation metrics
    """
    
    def __init__(
        self,
        config: ScenarioConfig,
        start_datetime: Optional[datetime] = None
    ):
        """
        Initialize simulation runner.
        
        Args:
            config: Scenario configuration
            start_datetime: Simulation start datetime (defaults to Monday 8 AM EST = 13:00 UTC)
        """
        self.config = config
        
        # Default to Monday 8 AM EST (13:00 UTC) if not specified
        if start_datetime is None:
            start_datetime = datetime(2024, 1, 15, 13, 0, 0)  # Monday 8 AM EST = 13:00 UTC
        
        # Initialize simulation environment
        self.sim_env = SimulationEnvironment(
            start_datetime=start_datetime,
            duration_hours=50.0  # 5 business days × 10 hours/day
        )
        
        # Initialize components
        self.agents: List[Agent] = []
        self.request_pool: Optional[RequestPool] = None
        self.absent_manager: Optional[AbsentAgentManager] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.attribute_generator: Optional[RequestAttributeGenerator] = None
        
        # Track processes
        self._agent_processes: List = []
        self._rotation_process = None
        
        logger.info(f"SimulationRunner initialized with start_datetime={start_datetime}")
    
    def initialize_components(self):
        """
        Initialize all simulation components.
        
        Creates:
        - Agents from configuration
        - Request pool
        - Absent agent manager
        - Request attribute generator
        - Metrics collector
        """
        logger.info("Initializing simulation components...")
        
        # Create agents
        self.agents = self._create_agents()
        logger.info(f"Created {len(self.agents)} agents")
        
        # Create request pool
        self.request_pool = RequestPool()
        logger.info("Created request pool")
        
        # Create absent agent manager
        self.absent_manager = AbsentAgentManager(
            agents=self.agents,
            absent_percentage=self.config.routing.absent_agent_percentage,
            random_seed=self.config.routing.random_seed
        )
        logger.info(f"Created absent agent manager (absence rate: {self.config.routing.absent_agent_percentage*100}%)")
        
        # Create request attribute generator with ALL probabilities
        self.attribute_generator = RequestAttributeGenerator(
            customer_reply_probability=self.config.routing.customer_reply_probability,
            internal_note_probability=self.config.routing.internal_note_probability,
            locked_tag_probability=self.config.routing.locked_tag_probability,
            followup_date_probability=self.config.routing.followup_date_probability,
            expected_completion_date_probability=self.config.routing.expected_completion_date_probability,
            sticky_assignment_probability=self.config.routing.sticky_assignment_probability,
            escalated_probability=self.config.routing.escalated_probability,
            winback_probability=self.config.routing.winback_probability,
            atl_rf_probability=self.config.routing.atl_rf_probability,
            sla_probability=self.config.routing.sla_probability,
            random_seed=self.config.routing.random_seed
        )
        logger.info("Created request attribute generator")
        
        # Create metrics collector
        self.metrics_collector = MetricsCollector()
        logger.info("Created metrics collector")
        
        logger.info("All components initialized successfully")
    
    def _create_agents(self) -> List[Agent]:
        """
        Create agents from configuration.
        
        Returns:
            List[Agent]: List of created agents
        """
        agents = []
        for agent_data in self.config.agents:
            agent = Agent(
                agent_id=agent_data['agent_id'],
                skills=agent_data['skills']
            )
            agents.append(agent)
        
        return agents
    
    def preload_requests(self, num_requests: int = 100):
        """
        Pre-load initial request pool with realistic attributes.
        
        Args:
            num_requests: Number of initial requests to create
        """
        logger.info(f"Pre-loading {num_requests} requests...")
        
        current_time = get_current_datetime(self.sim_env.env, self.sim_env.start_datetime)
        requests = []
        
        # Create basic requests
        for i in range(num_requests):
            request = Request(
                request_id=f"REQ{i:05d}",
                customer_id=f"CUST{(i % 50):03d}",  # 50 different customers
                product=f"Product{chr(65 + (i % 5))}",  # ProductA-ProductE
                created_at=current_time
            )
            requests.append(request)
        
        # Generate realistic attributes
        self.attribute_generator.generate_batch(requests, self.agents, current_time)
        
        # Add to request pool
        for request in requests:
            self.request_pool.add_request(request)
        
        logger.info(f"Pre-loaded {num_requests} requests with realistic attributes")
        
        # Log some statistics
        customer_replies = sum(1 for r in requests if r.has_customer_update())
        internal_notes = sum(1 for r in requests if r.has_internal_note())
        with_ecd = sum(1 for r in requests if r.has_expected_completion_date())
        sticky_assigned = sum(1 for r in requests if r.sticky_agent_id is not None)
        escalated = sum(1 for r in requests if r.is_escalated)
        winback = sum(1 for r in requests if r.is_winback)
        atl_rf = sum(1 for r in requests if r.is_atl_rf)
        has_sla = sum(1 for r in requests if r.has_sla)
        
        logger.info(f"  - Customer replies: {customer_replies}")
        logger.info(f"  - Internal notes: {internal_notes}")
        logger.info(f"  - With ECD: {with_ecd}")
        logger.info(f"  - Sticky assigned: {sticky_assigned}")
        logger.info(f"  - Escalated: {escalated}")
        logger.info(f"  - Winback: {winback}")
        logger.info(f"  - Atlantic RF: {atl_rf}")
        logger.info(f"  - Has SLA: {has_sla}")
    
    def _daily_rotation_process(self):
        """
        SimPy process for daily absent agent rotation.
        
        Runs at the start of each day to rotate which agents are absent.
        """
        logger.info("Starting daily rotation process")
        
        # Rotate at simulation start (day 0)
        current_time = get_current_datetime(self.sim_env.env, self.sim_env.start_datetime)
        self.absent_manager.rotate_absent_agents(current_time)
        logger.info(f"Initial rotation: {len(self.absent_manager.get_absent_agent_ids())} agents absent")
        
        # Rotate at start of each subsequent day
        for day in range(1, 5):  # Days 1-4 (we already did day 0)
            # Wait until next day starts
            next_day_time = get_next_day_start(self.sim_env.now)
            wait_time = next_day_time - self.sim_env.now
            yield self.sim_env.timeout(wait_time)
            
            # Rotate absent agents
            current_time = get_current_datetime(self.sim_env.env, self.sim_env.start_datetime)
            self.absent_manager.rotate_absent_agents(current_time)
            logger.info(
                f"Day {day} rotation at {self.sim_env.current_time_str}: "
                f"{len(self.absent_manager.get_absent_agent_ids())} agents absent"
            )
    
    def _agent_process(self, agent: Agent):
        """
        SimPy process for individual agent (PLACEHOLDER for Ticket #8).
        
        This is a stub that will be implemented in Ticket #8.
        For now, agents just wait and don't process requests.
        
        Args:
            agent: The agent this process represents
        """
        logger.debug(f"Agent {agent.agent_id} process started (placeholder)")
        
        # Placeholder: just wait until simulation ends
        while True:
            # In Ticket #8, this will:
            # 1. Check if agent is absent
            # 2. Get next request from production routing
            # 3. Process the request
            # 4. Update metrics
            # 5. Repeat
            
            # For now, just wait 1 hour and do nothing
            yield self.sim_env.timeout(1.0)
    
    def start_processes(self):
        """
        Start all SimPy processes (rotation + agent processes).
        """
        logger.info("Starting simulation processes...")
        
        # Start daily rotation process
        self._rotation_process = self.sim_env.process(self._daily_rotation_process())
        logger.info("Daily rotation process started")
        
        # Start agent processes (placeholder for Ticket #8)
        for agent in self.agents:
            process = self.sim_env.process(self._agent_process(agent))
            self._agent_processes.append(process)
        
        logger.info(f"Started {len(self._agent_processes)} agent processes (placeholder)")
    
    def run(self, num_preload_requests: int = 100) -> Dict:
        """
        Run the complete simulation.
        
        Args:
            num_preload_requests: Number of requests to pre-load
            
        Returns:
            Dict: Simulation results including metrics and statistics
        """
        logger.info("=" * 60)
        logger.info("Starting STM Routing Simulator v3.0")
        logger.info("=" * 60)
        
        # Initialize all components
        self.initialize_components()
        
        # Pre-load initial requests
        self.preload_requests(num_preload_requests)
        
        # Start all processes
        self.start_processes()
        
        # Run simulation
        logger.info(f"Running simulation for {self.sim_env.duration_hours} hours (5 business days, 10 hours each)...")
        logger.info(f"Start: {self.sim_env.start_datetime} (Monday 8 AM EST = 13:00 UTC)")
        
        try:
            self.sim_env.run()
            logger.info("Simulation completed successfully")
        except Exception as e:
            logger.error(f"Simulation failed with error: {e}")
            raise
        
        # Collect final results
        results = self._collect_results()
        
        logger.info("=" * 60)
        logger.info("Simulation finished")
        logger.info("=" * 60)
        
        return results
    
    def _collect_results(self) -> Dict:
        """
        Collect and return simulation results.
        
        Returns:
            Dict: Complete simulation results
        """
        logger.info("Collecting simulation results...")
        
        # Get environment statistics
        env_stats = self.sim_env.get_statistics()
        
        # Get absent agent statistics
        absent_stats = self.absent_manager.get_statistics()
        
        # Get request pool statistics
        pool_stats = {
            'total_requests': len(self.request_pool.get_all_requests()),
            'pending_requests': len(self.request_pool.get_pending_requests()),
            'assigned_requests': len(self.request_pool.get_assigned_requests()),
            'completed_requests': len(self.request_pool.get_completed_requests())
        }
        
        # Get agent statistics
        agent_stats = {
            'total_agents': len(self.agents),
            'agents_by_skill': self._count_agents_by_skill()
        }
        
        # Combine all results
        results = {
            'simulation': env_stats,
            'agents': agent_stats,
            'absent_agents': absent_stats,
            'requests': pool_stats,
            'metrics': {
                'note': 'Metrics collection will be implemented in Ticket #9'
            },
            'config': {
                'pilot_program_enabled': self.config.routing.pilot_program_enabled,
                'absent_percentage': self.config.routing.absent_agent_percentage,
                'preload_count': pool_stats['total_requests']
            }
        }
        
        logger.info("Results collected successfully")
        return results
    
    def _count_agents_by_skill(self) -> Dict[str, int]:
        """
        Count agents by skill.
        
        Returns:
            Dict[str, int]: Skill -> count mapping
        """
        skill_counts = {}
        for agent in self.agents:
            for skill in agent.skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        return skill_counts