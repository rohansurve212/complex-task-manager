"""
Performance Tests for Sprint 1 Components

Tests performance and scalability of the simulation components.
Tests memory usage, execution time, and bottlenecks.

Run with: pytest tests/integration/test_performance.py -v
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from models.agent import Agent
from models.request import Request
from models.request_pool import RequestPool


# ============================================================================
# TEST: Pool Performance
# ============================================================================

class TestPoolPerformance:
    """Test RequestPool performance with large datasets"""
    
    def test_add_performance_1000_requests(self):
        """Test adding 1000 requests"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Create requests
        requests = []
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id=["internet", "voice", "tv"][i % 3],
                request_source="bcom",
                product=["internet", "voice", "tv"][i % 3],
                service_region="ontario",
                request_type="new",
                order_date=base_time + timedelta(hours=i % 24),
                foc_target=8.0
            )
            requests.append(request)
        
        # Time the addition
        start_time = time.time()
        added = pool.add_requests(requests)
        elapsed = time.time() - start_time
        
        print(f"\nAdded {added} requests in {elapsed:.3f} seconds")
        print(f"Rate: {added/elapsed:.0f} requests/second")
        
        assert added == 1000
        assert elapsed < 1.0  # Should complete in under 1 second
    
    def test_filter_performance_1000_requests(self):
        """Test filtering 1000 requests by skill"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Add 1000 requests
        requests = []
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id=["internet", "voice", "tv"][i % 3],
                request_source="bcom",
                product=["internet", "voice", "tv"][i % 3],
                service_region="ontario",
                request_type="new",
                order_date=base_time,
                foc_target=8.0
            )
            requests.append(request)
        pool.add_requests(requests)
        
        # Time the filtering
        start_time = time.time()
        internet_requests = pool.get_requests_by_skill("internet")
        elapsed = time.time() - start_time
        
        print(f"\nFiltered {len(internet_requests)} internet requests from 1000 in {elapsed:.4f} seconds")
        
        assert len(internet_requests) > 0
        assert elapsed < 0.1  # Should be very fast with indexing
    
    def test_sort_performance_1000_requests(self):
        """Test sorting 1000 requests by priority"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Add 1000 requests with different ages
        requests = []
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i),
                foc_target=8.0
            )
            requests.append(request)
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 10, 0, 0, 0, tzinfo=timezone.utc)
        
        # Time the sorting
        start_time = time.time()
        sorted_requests = pool.sort_by_priority(requests, current_time, descending=True)
        elapsed = time.time() - start_time
        
        print(f"\nSorted {len(sorted_requests)} requests by priority in {elapsed:.3f} seconds")
        
        assert len(sorted_requests) == 1000
        assert elapsed < 1.0  # Should complete in under 1 second
    
    def test_complex_filter_performance(self):
        """Test complex filtering with multiple criteria"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Add 1000 requests with various attributes
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id=["internet", "voice", "tv"][i % 3],
                request_source="bcom",
                product=["internet", "voice", "tv"][i % 3],
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i % 100),
                foc_target=[5.0, 8.0, 10.0][i % 3],
                has_sla=(i % 2 == 0),
                is_escalated=(i % 5 == 0),
                is_winback=(i % 7 == 0)
            )
            pool.add_request(request)
        
        current_time = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)
        
        # Time complex filter
        start_time = time.time()
        filtered = pool.filter_requests(
            skill_id="internet",
            has_sla=True,
            is_escalated=True,
            min_age_days=1.0,
            max_age_days=3.0,
            current_time=current_time
        )
        elapsed = time.time() - start_time
        
        print(f"\nFiltered {len(filtered)} requests with complex criteria from 1000 in {elapsed:.3f} seconds")
        
        assert elapsed < 0.5  # Should be reasonably fast
    
    def test_assignment_performance_100_agents(self):
        """Test assignment operations with 100 agents"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Add 1000 requests
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time,
                foc_target=8.0
            )
            pool.add_request(request)
        
        # Create 100 agents
        agents = [
            Agent(agent_id=f"agent_{i:03d}", full_name=f"Agent {i}",
                  skillsets={"internet"})
            for i in range(100)
        ]
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # Time assignments
        start_time = time.time()
        assignments = 0
        
        for agent in agents:
            available = pool.get_available_requests(skill_id="internet")
            if available and agent.is_available:
                sorted_reqs = pool.sort_by_priority(available[:10], current_time, descending=True)
                request = sorted_reqs[0]
                pool.assign_request_to_agent(request.request_id, agent.agent_id, current_time)
                agent.assign_request(request.request_id, current_time)
                assignments += 1
        
        elapsed = time.time() - start_time
        
        print(f"\nAssigned {assignments} requests to 100 agents in {elapsed:.3f} seconds")
        print(f"Rate: {assignments/elapsed:.0f} assignments/second")
        
        assert assignments == 100
        assert elapsed < 5.0  # Should complete in under 5 seconds


# ============================================================================
# TEST: Agent Performance
# ============================================================================

class TestAgentPerformance:
    """Test Agent model performance"""
    
    def test_create_1000_agents(self):
        """Test creating 1000 agents"""
        start_time = time.time()
        
        agents = []
        for i in range(1000):
            agent = Agent(
                agent_id=f"agent_{i:04d}",
                full_name=f"Agent {i}",
                skillsets={"internet", "voice", "tv"}
            )
            agents.append(agent)
        
        elapsed = time.time() - start_time
        
        print(f"\nCreated {len(agents)} agents in {elapsed:.3f} seconds")
        print(f"Rate: {len(agents)/elapsed:.0f} agents/second")
        
        assert len(agents) == 1000
        assert elapsed < 1.0
    
    def test_agent_work_history_performance(self):
        """Test agent with large work history"""
        agent = Agent(
            agent_id="test_agent",
            full_name="Test Agent",
            skillsets={"internet"}
        )
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Simulate 1000 completed assignments
        start_time = time.time()
        
        for i in range(1000):
            assignment_time = base_time + timedelta(hours=i)
            completion_time = assignment_time + timedelta(hours=1)
            
            agent.assign_request(f"REQ_{i:04d}", assignment_time)
            agent.complete_request(completion_time)
        
        elapsed = time.time() - start_time
        
        print(f"\nProcessed {agent.work_count} assignments in {elapsed:.3f} seconds")
        
        assert agent.work_count == 1000
        assert len(agent.work_history) == 1000
        assert elapsed < 2.0


# ============================================================================
# TEST: Request Performance
# ============================================================================

class TestRequestPerformance:
    """Test Request model performance"""
    
    def test_create_1000_requests(self):
        """Test creating 1000 requests"""
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        start_time = time.time()
        
        requests = []
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time,
                foc_target=8.0
            )
            requests.append(request)
        
        elapsed = time.time() - start_time
        
        print(f"\nCreated {len(requests)} requests in {elapsed:.3f} seconds")
        print(f"Rate: {len(requests)/elapsed:.0f} requests/second")
        
        assert len(requests) == 1000
        assert elapsed < 1.0
    
    def test_priority_calculation_performance(self):
        """Test calculating priority for 1000 requests"""
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Create 1000 requests
        requests = []
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i % 100),
                foc_target=8.0
            )
            requests.append(request)
        
        current_time = datetime(2024, 5, 10, 0, 0, 0, tzinfo=timezone.utc)
        
        # Time priority calculations
        start_time = time.time()
        
        priorities = [req.calculate_priority_score(current_time) for req in requests]
        
        elapsed = time.time() - start_time
        
        print(f"\nCalculated priority for {len(priorities)} requests in {elapsed:.3f} seconds")
        print(f"Rate: {len(priorities)/elapsed:.0f} calculations/second")
        
        assert len(priorities) == 1000
        assert elapsed < 0.5


# ============================================================================
# TEST: Scalability
# ============================================================================

class TestScalability:
    """Test system scalability"""
    
    def test_scalability_100_agents_1000_requests(self):
        """Test system with 100 agents and 1000 requests"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        print("\n=== Scalability Test: 100 Agents, 1000 Requests ===")
        
        # Create requests
        start = time.time()
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id=["internet", "voice", "tv"][i % 3],
                request_source="bcom",
                product=["internet", "voice", "tv"][i % 3],
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i % 100),
                foc_target=8.0
            )
            pool.add_request(request)
        request_time = time.time() - start
        print(f"Created 1000 requests: {request_time:.3f}s")
        
        # Create agents
        start = time.time()
        agents = [
            Agent(agent_id=f"agent_{i:03d}", full_name=f"Agent {i}",
                  skillsets={"internet", "voice", "tv"})
            for i in range(100)
        ]
        agent_time = time.time() - start
        print(f"Created 100 agents: {agent_time:.3f}s")
        
        # Simulate routing
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        start = time.time()
        assignments = 0
        
        for agent in agents:
            for skill in agent.skillsets:
                available = pool.get_available_requests(skill_id=skill)
                if available and agent.is_available:
                    sorted_reqs = pool.sort_by_priority(available[:10], current_time, descending=True)
                    request = sorted_reqs[0]
                    pool.assign_request_to_agent(request.request_id, agent.agent_id, current_time)
                    agent.assign_request(request.request_id, current_time)
                    assignments += 1
                    break
        
        routing_time = time.time() - start
        print(f"Routed {assignments} requests: {routing_time:.3f}s")
        
        # Get statistics
        start = time.time()
        stats = pool.get_statistics(current_time)
        stats_time = time.time() - start
        print(f"Calculated statistics: {stats_time:.3f}s")
        print(f"Statistics: {stats}")
        
        print(f"\nTotal time: {request_time + agent_time + routing_time + stats_time:.3f}s")
        
        # Assertions
        assert assignments == 100
        assert request_time + agent_time + routing_time + stats_time < 10.0
    
    def test_memory_efficiency(self):
        """Test memory usage with large datasets"""
        import sys
        
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Get initial memory
        initial_size = sys.getsizeof(pool)
        
        # Add 1000 requests
        for i in range(1000):
            request = Request(
                request_id=f"REQ_{i:04d}",
                external_id=f"EXT_{i:04d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time,
                foc_target=8.0
            )
            pool.add_request(request)
        
        # Get final memory
        final_size = sys.getsizeof(pool)
        
        print("\nMemory usage:")
        print(f"  Initial: {initial_size} bytes")
        print(f"  Final: {final_size} bytes")
        print(f"  Per request: {(final_size - initial_size) / 1000:.2f} bytes")
        
        # Memory should be reasonable
        assert final_size < 10 * 1024 * 1024  # Less than 10MB for 1000 requests


# ============================================================================
# TEST: Stress Tests
# ============================================================================

class TestStressTests:
    """Stress tests to find breaking points"""
    
    @pytest.mark.slow
    def test_large_pool_10000_requests(self):
        """Test with 10,000 requests (marked slow)"""
        pool = RequestPool()
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        print("\n=== Stress Test: 10,000 Requests ===")
        
        start_time = time.time()
        
        # Add 10,000 requests
        for i in range(10000):
            request = Request(
                request_id=f"REQ_{i:05d}",
                external_id=f"EXT_{i:05d}",
                skill_id=["internet", "voice", "tv"][i % 3],
                request_source="bcom",
                product=["internet", "voice", "tv"][i % 3],
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i % 500),
                foc_target=8.0
            )
            pool.add_request(request)
        
        add_time = time.time() - start_time
        print(f"Added 10,000 requests in {add_time:.3f}s")
        
        # Filter
        start = time.time()
        internet = pool.get_requests_by_skill("internet")
        filter_time = time.time() - start
        print(f"Filtered {len(internet)} internet requests in {filter_time:.3f}s")
        
        # Sort
        current_time = datetime(2024, 5, 10, 0, 0, 0, tzinfo=timezone.utc)
        start = time.time()
        sorted_reqs = pool.sort_by_priority(internet[:1000], current_time, descending=True)
        sort_time = time.time() - start
        print(f"Sorted {len(sorted_reqs)} requests in {sort_time:.3f}s")
        
        # Statistics
        start = time.time()
        stats = pool.get_statistics(current_time)
        stats_time = time.time() - start
        print(f"Calculated statistics in {stats_time:.3f}s")
        print(f"Statistics: {stats}")
        
        print(f"\nTotal time: {add_time + filter_time + sort_time + stats_time:.3f}s")
        
        assert pool.size() == 10000
        assert add_time < 10.0  # Should complete in under 10 seconds


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    # Run without slow tests by default
    pytest.main([__file__, '-v', '--tb=short', '-m', 'not slow'])