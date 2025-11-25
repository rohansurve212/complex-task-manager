"""
Manual testing script for Request model.
Run: python test_request_manual.py
"""

from pathlib import Path
from datetime import datetime, timezone
import sys
sys.path.append('.')

from models.request import Request
from models.data_loader import (
    load_requests_from_csv,
    filter_requests_by_skill,
    get_request_statistics
)
from utils.logger import setup_logger

# Set up logging
logger = setup_logger('request_test', log_level=10)

logger.info("=" * 60)
logger.info("TESTING REQUEST MODEL - TICKET #3")
logger.info("=" * 60)

# Test 1: Create a simple request
logger.info("\nTest 1: Creating a simple request...")
order_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
current_time = datetime(2024, 5, 2, 10, 0, 0, tzinfo=timezone.utc)

request = Request(
    request_id="REQ_001",
    external_id="EXT_001",
    skill_id="internet",
    request_source="bcom",
    product="internet",
    service_region="ontario",
    request_type="new",
    order_date=order_time,
    foc_target=8.0,
    has_sla=True
)

logger.info(f"Created request: {request}")
logger.info(f"  - Skill: {request.skill_id}")
logger.info(f"  - FOC Target: {request.foc_target} days")
logger.info(f"  - State: {request.state}")

# Test 2: Age calculations
logger.info("\nTest 2: Age calculations...")
age_minutes = request.get_age_minutes(current_time)
age_days = request.get_age_days(current_time)
logger.info(f"Age: {age_minutes} minutes ({age_days} days)")

# Test 3: Priority score
logger.info("\nTest 3: Priority score calculation...")
priority = request.calculate_priority_score(current_time)
logger.info(f"Priority score: {priority:.4f}")
logger.info(f"  - Formula: {age_minutes} min / ({request.foc_target} days * 1440 min/day)")

# Test 4: FOC compliance
logger.info("\nTest 4: FOC compliance...")
is_compliant = request.is_foc_compliant(current_time)
time_remaining = request.time_until_foc_breach(current_time)
compliance_pct = request.get_foc_compliance_percentage(current_time)
logger.info(f"FOC Compliant: {is_compliant}")
logger.info(f"Time until breach: {time_remaining} days")
logger.info(f"FOC consumed: {compliance_pct:.1f}%")

# Test 5: State transitions
logger.info("\nTest 5: State transitions...")
logger.info(f"Initial state: {request.state}")

assignment_time = datetime(2024, 5, 2, 11, 0, 0, tzinfo=timezone.utc)
request.assign_to_agent("john.doe", assignment_time)
logger.info(f"After assignment: {request.state}")
logger.info(f"  - Assigned to: {request.assigned_agent_id}")

completion_time = datetime(2024, 5, 2, 13, 0, 0, tzinfo=timezone.utc)
request.mark_completed(completion_time)
logger.info(f"After completion: {request.state}")
handle_time = request.get_handle_time_seconds()
logger.info(f"  - Handle time: {handle_time} seconds ({handle_time/3600:.2f} hours)")

# Test 6: Load from CSV
logger.info("\nTest 6: Loading requests from CSV...")
csv_path = Path("tests/fixtures/sample_requests.csv")
if csv_path.exists():
    requests = load_requests_from_csv(csv_path)
    logger.info(f"Loaded {len(requests)} requests from CSV")
    
    # Show first request
    first = requests[0]
    logger.info(f"First request: {first.request_id}")
    logger.info(f"  - Skill: {first.skill_id}")
    logger.info(f"  - Product: {first.product}")
    logger.info(f"  - Region: {first.service_region}")
    logger.info(f"  - FOC Target: {first.foc_target} days")
    logger.info(f"  - Has SLA: {first.has_sla}")
    logger.info(f"  - Escalated: {first.is_escalated}")
    
    # Test 7: Filter by skill
    logger.info("\nTest 7: Filtering by skill...")
    internet_requests = filter_requests_by_skill(requests, "internet")
    logger.info(f"Found {len(internet_requests)} internet requests")
    
    # Test 8: Get statistics
    logger.info("\nTest 8: Request statistics...")
    stats = get_request_statistics(requests)
    logger.info(f"Total requests: {stats['total_requests']}")
    logger.info(f"Unique skills: {stats['unique_skills']}")
    logger.info(f"SLA requests: {stats['sla_count']}")
    logger.info(f"Escalated: {stats['escalated_count']}")
    logger.info(f"Winback: {stats['winback_count']}")
    logger.info(f"Avg FOC target: {stats['avg_foc_target']:.2f} days")
    
    # Test 9: Priority comparison
    logger.info("\nTest 9: Priority comparison...")
    current = datetime(2024, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
    
    # Calculate priorities for all requests
    priorities = []
    for req in requests[:5]:  # First 5 requests
        score = req.calculate_priority_score(current)
        age = req.get_age_days(current)
        priorities.append((req.request_id, score, age, req.foc_target))
    
    # Sort by priority (highest first)
    priorities.sort(key=lambda x: x[1], reverse=True)
    
    logger.info("Top 5 requests by priority:")
    for req_id, score, age, foc in priorities:
        logger.info(f"  {req_id}: score={score:.4f}, age={age:.2f}d, foc={foc}d")
else:
    logger.warning("Sample CSV not found, skipping CSV tests")

logger.info("\n" + "=" * 60)
logger.info("ALL MANUAL TESTS COMPLETED SUCCESSFULLY!")
logger.info("=" * 60)