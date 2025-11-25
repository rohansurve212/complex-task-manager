"""
Manual testing script for RequestPool model.
Run: python test_request_pool_manual.py
"""

from pathlib import Path
from datetime import datetime, timezone, timedelta
import time
import sys
sys.path.append('.')

from models.request import Request, RequestState
from models.request_pool import RequestPool
from models.data_loader import load_requests_from_csv
from utils.logger import setup_logger

# Set up logging
logger = setup_logger('request_pool_test', log_level=10)

logger.info("=" * 60)
logger.info("TESTING REQUEST POOL - TICKET #4")
logger.info("=" * 60)

# Helper function to create test requests
def create_test_request(request_id, skill_id="internet", order_date=None, **kwargs):
    if order_date is None:
        order_date = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    return Request(
        request_id=request_id,
        external_id=f"EXT_{request_id}",
        skill_id=skill_id,
        request_source="bcom",
        product=skill_id,
        service_region="ontario",
        request_type="new",
        order_date=order_date,
        **kwargs
    )

# Test 1: Create pool and add requests
logger.info("\nTest 1: Creating pool and adding requests...")
pool = RequestPool()
logger.info(f"Created empty pool: {pool}")
logger.info(f"  - Size: {pool.size()}")
logger.info(f"  - Is empty: {pool.is_empty()}")

# Add some requests
base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
requests = [
    create_test_request("REQ_001", skill_id="internet", order_date=base_time),
    create_test_request("REQ_002", skill_id="voice", order_date=base_time + timedelta(hours=2)),
    create_test_request("REQ_003", skill_id="internet", order_date=base_time + timedelta(hours=4)),
    create_test_request("REQ_004", skill_id="tv", order_date=base_time + timedelta(hours=6)),
    create_test_request("REQ_005", skill_id="internet", order_date=base_time + timedelta(hours=8))
]

count = pool.add_requests(requests)
logger.info(f"Added {count} requests to pool")
logger.info(f"  - Total size: {pool.size()}")
logger.info(f"  - Skills: {pool.get_skills()}")

# Test 2: Filter by skill
logger.info("\nTest 2: Filtering by skill...")
internet_requests = pool.get_requests_by_skill("internet")
logger.info(f"Found {len(internet_requests)} internet requests")
for req in internet_requests:
    logger.info(f"  - {req.request_id}: {req.skill_id}")

# Test 3: Get available requests
logger.info("\nTest 3: Getting available requests...")
available = pool.get_available_requests()
logger.info(f"Total available (NEW state): {len(available)}")

available_internet = pool.get_available_requests(skill_id="internet")
logger.info(f"Available internet requests: {len(available_internet)}")

# Test 4: Sort by priority
logger.info("\nTest 4: Sorting by priority...")
current_time = datetime(2024, 5, 2, 12, 0, 0, tzinfo=timezone.utc)

sorted_requests = pool.sort_by_priority(available_internet, current_time, descending=True)
logger.info(f"Sorted {len(sorted_requests)} requests by priority (highest first):")
for req in sorted_requests:
    priority = req.calculate_priority_score(current_time)
    age_hours = req.get_age_minutes(current_time) / 60.0
    logger.info(f"  - {req.request_id}: priority={priority:.4f}, age={age_hours:.1f}h")

# Test 5: Assign requests
logger.info("\nTest 5: Assigning requests to agents...")
assignment_time = datetime(2024, 5, 2, 13, 0, 0, tzinfo=timezone.utc)

# Assign top 2 requests
for i, req in enumerate(sorted_requests[:2]):
    agent_id = f"agent_{i+1}"
    success = pool.assign_request_to_agent(req.request_id, agent_id, assignment_time)
    logger.info(f"Assigned {req.request_id} to {agent_id}: {success}")

# Check states
new_count = len(pool.get_requests_by_state(RequestState.NEW))
assigned_count = len(pool.get_requests_by_state(RequestState.ASSIGNED))
logger.info("After assignment:")
logger.info(f"  - NEW: {new_count}")
logger.info(f"  - ASSIGNED: {assigned_count}")

# Test 6: Complete requests
logger.info("\nTest 6: Completing requests...")
completion_time = assignment_time + timedelta(hours=2)

assigned_requests = pool.get_requests_by_state(RequestState.ASSIGNED)
for req in assigned_requests[:1]:  # Complete one request
    success = pool.complete_request(req.request_id, completion_time)
    logger.info(f"Completed {req.request_id}: {success}")
    handle_time = req.get_handle_time_seconds()
    logger.info(f"  - Handle time: {handle_time} seconds ({handle_time/3600:.2f} hours)")

# Check final states
logger.info("\nFinal state distribution:")
for state in [RequestState.NEW, RequestState.ASSIGNED, RequestState.COMPLETED]:
    count = len(pool.get_requests_by_state(state))
    logger.info(f"  - {state.value.upper()}: {count}")

# Test 7: Statistics
logger.info("\nTest 7: Pool statistics...")
stats_time = datetime(2024, 5, 3, 0, 0, 0, tzinfo=timezone.utc)
stats = pool.get_statistics(stats_time)

logger.info(f"Total requests: {stats['total_requests']}")
logger.info(f"Total added: {stats['total_added']}")
logger.info(f"Total assigned: {stats['total_assigned']}")
logger.info(f"Total removed: {stats['total_removed']}")

logger.info("\nBy skill:")
for skill, count in stats['by_skill'].items():
    logger.info(f"  - {skill}: {count}")

logger.info("\nBy state:")
for state, count in stats['by_state'].items():
    logger.info(f"  - {state}: {count}")

if 'age' in stats:
    logger.info("\nAge statistics:")
    logger.info(f"  - Min: {stats['age']['min_days']:.2f} days")
    logger.info(f"  - Max: {stats['age']['max_days']:.2f} days")
    logger.info(f"  - Avg: {stats['age']['avg_days']:.2f} days")

if 'foc_compliance' in stats:
    logger.info("\nFOC compliance:")
    logger.info(f"  - Compliant: {stats['foc_compliance']['compliant_count']}")
    logger.info(f"  - Breached: {stats['foc_compliance']['breached_count']}")
    logger.info(f"  - Rate: {stats['foc_compliance']['compliance_rate']*100:.1f}%")

# Test 8: Advanced filtering
logger.info("\nTest 8: Advanced filtering...")
pool2 = RequestPool()

# Add requests with various flags
requests2 = [
    create_test_request("REQ_101", skill_id="internet", has_sla=True, is_escalated=False, order_date=base_time),
    create_test_request("REQ_102", skill_id="internet", has_sla=True, is_escalated=True, order_date=base_time),
    create_test_request("REQ_103", skill_id="internet", has_sla=False, is_escalated=False, order_date=base_time),
    create_test_request("REQ_104", skill_id="voice", is_winback=True, order_date=base_time),
]
pool2.add_requests(requests2)

# Filter: internet + SLA + escalated
filtered = pool2.filter_requests(
    skill_id="internet",
    has_sla=True,
    is_escalated=True
)
logger.info(f"Internet + SLA + Escalated: {len(filtered)} requests")
for req in filtered:
    logger.info(f"  - {req.request_id}")

# Filter: winback requests
winback = pool2.filter_requests(is_winback=True)
logger.info(f"Winback requests: {len(winback)}")

# Test 9: Multi-tier bucketing (production-style)
logger.info("\nTest 9: Multi-tier bucketing (production-style)...")
pool3 = RequestPool()

# Create requests for different tiers
tier_requests = [
    # Tier 1: Escalated winback
    create_test_request("REQ_T1_001", is_escalated=True, is_winback=True, 
                       order_date=base_time, foc_target=5.0),
    # Tier 2: Winback
    create_test_request("REQ_T2_001", is_winback=True, 
                       order_date=base_time, foc_target=5.0),
    # Tier 3: Escalated SLA
    create_test_request("REQ_T3_001", is_escalated=True, has_sla=True,
                       order_date=base_time, foc_target=8.0),
    # Tier 4: Escalated non-SLA
    create_test_request("REQ_T4_001", is_escalated=True,
                       order_date=base_time, foc_target=8.0),
    # Tier 5: Commons
    create_test_request("REQ_T5_001", order_date=base_time, foc_target=8.0),
]
pool3.add_requests(tier_requests)

routing_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)

# Define tiers (matching production logic)
tiers = [
    ("Tier 1: Escalated Winback", {"is_escalated": True, "is_winback": True}),
    ("Tier 2: Winback", {"is_winback": True, "is_escalated": False}),
    ("Tier 3: Escalated SLA", {"is_escalated": True, "has_sla": True, "is_winback": False}),
    ("Tier 4: Escalated non-SLA", {"is_escalated": True, "has_sla": False, "is_winback": False}),
    ("Tier 5: Commons", {"is_escalated": False, "has_sla": False, "is_winback": False}),
]

logger.info("Routing order by tier:")
for tier_name, filters in tiers:
    tier_requests = pool3.filter_requests(state=RequestState.NEW, **filters)
    if tier_requests:
        sorted_tier = pool3.sort_by_priority(tier_requests, routing_time, descending=True)
        logger.info(f"\n{tier_name}:")
        for req in sorted_tier:
            priority = req.calculate_priority_score(routing_time)
            logger.info(f"  - {req.request_id}: priority={priority:.4f}")

# Test 10: Load from CSV and pool operations
logger.info("\nTest 10: Loading from CSV and pool operations...")
csv_path = Path("tests/fixtures/sample_requests.csv")
if csv_path.exists():
    requests_from_csv = load_requests_from_csv(csv_path)
    logger.info(f"Loaded {len(requests_from_csv)} requests from CSV")
    
    # Create new pool
    csv_pool = RequestPool()
    csv_pool.add_requests(requests_from_csv)
    
    logger.info(f"Pool size: {csv_pool.size()}")
    logger.info(f"Unique skills: {csv_pool.get_skills()}")
    
    # Get skill distribution
    distribution = csv_pool.get_skill_distribution()
    logger.info("\nSkill distribution:")
    for skill, count in sorted(distribution.items()):
        logger.info(f"  - {skill}: {count}")
    
    # Get available requests for each skill
    logger.info("\nAvailable requests by skill:")
    for skill in csv_pool.get_skills():
        available = csv_pool.get_available_requests(skill_id=skill)
        logger.info(f"  - {skill}: {len(available)} available")
else:
    logger.warning("Sample CSV not found, skipping CSV tests")

# Test 11: Snapshot functionality
logger.info("\nTest 11: Pool snapshot...")
original_pool = RequestPool()
snap_requests = [
    create_test_request("REQ_S1", skill_id="internet", order_date=base_time),
    create_test_request("REQ_S2", skill_id="voice", order_date=base_time),
]
original_pool.add_requests(snap_requests)

logger.info(f"Original pool size: {original_pool.size()}")

# Create snapshot
snapshot = original_pool.snapshot()
logger.info(f"Snapshot created, size: {snapshot.size()}")

# Modify original
original_pool.remove_request("REQ_S1")
original_pool.add_request(create_test_request("REQ_S3", skill_id="tv", order_date=base_time))

logger.info("\nAfter modifications:")
logger.info(f"  - Original pool size: {original_pool.size()}")
logger.info(f"  - Snapshot size: {snapshot.size()} (unchanged)")
logger.info(f"  - Original contains REQ_S1: {original_pool.contains('REQ_S1')}")
logger.info(f"  - Snapshot contains REQ_S1: {snapshot.contains('REQ_S1')}")

# Test 12: Iteration
logger.info("\nTest 12: Pool iteration...")
iter_pool = RequestPool()
iter_requests = [
    create_test_request(f"REQ_I{i}", skill_id="internet", order_date=base_time)
    for i in range(5)
]
iter_pool.add_requests(iter_requests)

logger.info(f"Iterating over pool with {len(iter_pool)} requests:")
for i, request in enumerate(iter_pool, 1):
    logger.info(f"  {i}. {request.request_id} - {request.skill_id}")

# Test 13: Performance test
logger.info("\nTest 13: Performance test (large pool)...")

large_pool = RequestPool()
num_requests = 1000

# Add many requests
start_time = time.time()
large_requests = [
    create_test_request(
        f"REQ_L{i:04d}",
        skill_id=["internet", "voice", "tv"][i % 3],
        order_date=base_time + timedelta(hours=i % 24)
    )
    for i in range(num_requests)
]
large_pool.add_requests(large_requests)
add_time = time.time() - start_time
logger.info(f"Added {num_requests} requests in {add_time:.3f} seconds")

# Filter by skill
start_time = time.time()
internet = large_pool.get_requests_by_skill("internet")
filter_time = time.time() - start_time
logger.info(f"Filtered {len(internet)} internet requests in {filter_time:.3f} seconds")

# Sort by priority
start_time = time.time()
current = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
sorted_list = large_pool.sort_by_priority(internet, current, descending=True)
sort_time = time.time() - start_time
logger.info(f"Sorted {len(sorted_list)} requests in {sort_time:.3f} seconds")

# Get statistics
start_time = time.time()
large_stats = large_pool.get_statistics(current)
stats_time = time.time() - start_time
logger.info(f"Calculated statistics in {stats_time:.3f} seconds")

logger.info("\n" + "=" * 60)
logger.info("ALL MANUAL TESTS COMPLETED SUCCESSFULLY!")
logger.info("=" * 60)