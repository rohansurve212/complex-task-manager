#!/usr/bin/env python3
"""
Generate Baseline and Proposed Scenario Files for Wholesale SLA Impact Demo

This script generates two scenario files:
1. baseline_scenario.yaml - All 13 customers with foc_target=8.0, has_sla=False
2. proposed_scenario.yaml - 1 SLA customer (CUST_A) with foc_target=1.0, has_sla=True; 12 non-SLA with foc_target=8.0, has_sla=False

Total: 500 requests from 13 customers
- 1 SLA customer (CUST_A): 30 requests (6%)
- 12 Non-SLA customers (CUST_B-M): 470 requests (94%)
"""

import yaml
from typing import List, Dict


# Customer configuration
# Single SLA customer
SLA_CUSTOMER = {
    'CUST_A': 30,
}

# All other customers (now 12 non-SLA)
NON_SLA_CUSTOMERS = {
    'CUST_B': 30,
    'CUST_C': 30,
    'CUST_D': 30,
    'CUST_E': 30,
    'CUST_F': 25,
    'CUST_G': 25,
    'CUST_H': 50,
    'CUST_I': 50,
    'CUST_J': 50,
    'CUST_K': 50,
    'CUST_L': 50,
    'CUST_M': 50,
}

# Skills
SKILLS = ['WholesaleBasic', 'WholesaleAdvanced', 'WholesaleExpert']

# Request types
REQUEST_TYPES = ['new', 'change']

# Products
PRODUCTS = ['WholesalePro', 'WholesaleStandard', 'WholesalePremium']


def generate_agents() -> List[Dict]:
    """Generate 56 wholesale team agents"""
    
    # Agent name pools for variety
    first_names = [
        'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie', 'Drew', 'Avery', 'Quinn',
        'Dakota', 'Skyler', 'Cameron', 'Peyton', 'Reese', 'Parker', 'Hayden', 'Emerson', 'Finley', 'River',
        'Sage', 'Phoenix', 'Rowan', 'Blake', 'Charlie', 'Ellis', 'Harper', 'Kendall', 'Logan', 'Milan',
        'Oakley', 'Presley', 'Remy', 'Sawyer', 'Spencer', 'Tatum', 'Winter', 'Zion', 'Arden', 'Bailey',
        'Carson', 'Devon', 'Eden', 'Gray', 'Harley', 'Indigo', 'Jules', 'Kay', 'Lane', 'Monroe',
        'Nico', 'Ocean', 'Perry', 'Rain', 'Shay', 'True'
    ]
    
    last_names = [
        'Thompson', 'Martinez', 'Chen', 'Kim', 'Rodriguez', 'Patel', 'Anderson', 'Williams', 'Johnson', 'Davis',
        'Brown', 'Garcia', 'Miller', 'Wilson', 'Moore', 'Taylor', 'Jackson', 'White', 'Harris', 'Martin',
        'Lee', 'Walker', 'Hall', 'Allen', 'Young', 'King', 'Wright', 'Lopez', 'Hill', 'Scott',
        'Green', 'Adams', 'Baker', 'Nelson', 'Carter', 'Mitchell', 'Roberts', 'Turner', 'Phillips', 'Campbell',
        'Parker', 'Evans', 'Edwards', 'Collins', 'Stewart', 'Morris', 'Rogers', 'Reed', 'Cook', 'Morgan',
        'Bell', 'Murphy', 'Bailey', 'Rivera', 'Cooper', 'Richardson'
    ]
    
    # Skillset distribution patterns
    skillset_patterns = [
        ['WholesaleBasic', 'WholesaleAdvanced'],           # 40% of agents
        ['WholesaleBasic', 'WholesaleExpert'],             # 20% of agents
        ['WholesaleAdvanced', 'WholesaleExpert'],          # 20% of agents
        ['WholesaleBasic', 'WholesaleAdvanced', 'WholesaleExpert'],  # 20% of agents
    ]
    
    agents = []
    for i in range(56):
        agent_id = f'AGENT{i+1:03d}'
        full_name = f'{first_names[i % len(first_names)]} {last_names[i % len(last_names)]}'
        
        # Distribute skillsets based on patterns
        if i < 22:  # First 40% (22 agents)
            skillsets = skillset_patterns[0]
        elif i < 33:  # Next 20% (11 agents)
            skillsets = skillset_patterns[1]
        elif i < 44:  # Next 20% (11 agents)
            skillsets = skillset_patterns[2]
        else:  # Last 20% (12 agents)
            skillsets = skillset_patterns[3]
        
        agents.append({
            'agent_id': agent_id,
            'full_name': full_name,
            'skillsets': skillsets
        })
    
    return agents


def generate_requests(customer_id: str, num_requests: int, foc_target: float, has_sla: bool, start_offset: int) -> List[Dict]:
    """
    Generate requests for a customer
    
    Args:
        customer_id: Customer identifier (e.g., 'CUST_A')
        num_requests: Number of requests to generate
        foc_target: FOC target in days
        has_sla: Whether customer has SLA
        start_offset: Starting offset in hours for request age distribution
    """
    requests = []
    
    # Distribute requests across 30 days (0 to 720 hours ago)
    max_age_hours = 720  # 30 days
    
    for i in range(1, num_requests + 1):
        # Calculate age offset (negative = in the past)
        offset_hours = -(i * max_age_hours / num_requests)
        
        # Cycle through skills
        skill_idx = (i - 1) % len(SKILLS)
        skill = SKILLS[skill_idx]
        
        # Alternate request types
        request_type = REQUEST_TYPES[(i - 1) % len(REQUEST_TYPES)]
        
        # Cycle through products
        product_idx = (i - 1) % len(PRODUCTS)
        product = PRODUCTS[product_idx]
        
        request = {
            'request_id': f'REQ_{customer_id}_{i:03d}',
            'external_id': f'EXT_{customer_id}_{i:03d}',
            'skill_id': skill,
            'request_source': 'wholesale',
            'product': product,
            'service_region': 'National',
            'request_type': request_type,
            'order_date_offset_hours': offset_hours,
            'foc_target': foc_target,
            'has_sla': has_sla,
            'golden_customer_id': customer_id,
            'workorder_status': 'new'
        }
        
        requests.append(request)
    
    return requests


def generate_baseline_scenario() -> Dict:
    """Generate baseline scenario - all customers without SLA"""
    print("Generating baseline scenario...")
    
    scenario = {
        'name': 'Baseline - Wholesale Team (No SLA Assignments)',
        'description': 'Current state with 500 requests from 13 customers. All customers have 8-day FOC target with no SLA.',
        'start_time': '2024-01-15T09:00:00-05:00',
        'routing_config': {
            'pilot_program_enabled': True
        },
        'agents': generate_agents(),
        'requests': []
    }
    
    # Generate requests for all customers (all with foc_target=8.0, has_sla=False)
    start_offset = 1
    
    # SLA customer (but not SLA yet in baseline)
    for customer_id, num_requests in SLA_CUSTOMER.items():
        requests = generate_requests(customer_id, num_requests, foc_target=8.0, has_sla=False, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} requests for {customer_id}")
    
    # Non-SLA customers
    for customer_id, num_requests in NON_SLA_CUSTOMERS.items():
        requests = generate_requests(customer_id, num_requests, foc_target=8.0, has_sla=False, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} requests for {customer_id}")
    
    print(f"Total requests: {len(scenario['requests'])}")
    return scenario


def generate_proposed_scenario() -> Dict:
    """Generate proposed scenario - 1 customer with SLA, 12 without"""
    print("\nGenerating proposed scenario...")
    
    scenario = {
        'name': 'Proposed - Wholesale Team with Single SLA Customer',
        'description': 'Proposed state with 1 SLA customer (CUST_A: foc_target=1.0 day, has_sla=True) and 12 non-SLA customers (foc_target=8.0 days, has_sla=False).',
        'start_time': '2024-01-15T09:00:00-05:00',
        'routing_config': {
            'pilot_program_enabled': True
        },
        'agents': generate_agents(),
        'requests': []
    }
    
    # Generate requests for all customers
    start_offset = 1
    
    # Single SLA customer (foc_target=1.0, has_sla=True)
    for customer_id, num_requests in SLA_CUSTOMER.items():
        requests = generate_requests(customer_id, num_requests, foc_target=1.0, has_sla=True, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} SLA requests for {customer_id}")
    
    # Non-SLA customers (foc_target=8.0, has_sla=False)
    for customer_id, num_requests in NON_SLA_CUSTOMERS.items():
        requests = generate_requests(customer_id, num_requests, foc_target=8.0, has_sla=False, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} non-SLA requests for {customer_id}")
    
    print(f"Total requests: {len(scenario['requests'])}")
    return scenario


def save_scenario(scenario: Dict, filename: str):
    """Save scenario to YAML file"""
    with open(filename, 'w') as f:
        yaml.dump(scenario, f, default_flow_style=False, sort_keys=False, width=120)
    print(f"Saved: {filename}")


def main():
    print("=" * 80)
    print("Wholesale SLA Impact Scenario Generator")
    print("=" * 80)
    print()
    print("Configuration:")
    print("  Total requests: 500")
    print("  SLA customer: 1 (CUST_A) - 30 requests (6%)")
    print("  Non-SLA customers: 12 (CUST_B-M) - 470 requests (94%)")
    print("  Agents: 56 (Wholesale team)")
    print()
    
    # Generate baseline
    baseline = generate_baseline_scenario()
    save_scenario(baseline, 'demo/demo_wholesale_sla_impact/scenarios/baseline_scenario.yaml')
    
    # Generate proposed
    proposed = generate_proposed_scenario()
    save_scenario(proposed, 'demo/demo_wholesale_sla_impact/scenarios/proposed_scenario.yaml')
    
    print()
    print("=" * 80)
    print("Scenario generation complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review the generated scenario files in scenarios/")
    print("  2. Run quick analysis: python compare_foc_impact.py")
    print("  3. Run full simulation: python run_full_simulation.py")


if __name__ == '__main__':
    main()