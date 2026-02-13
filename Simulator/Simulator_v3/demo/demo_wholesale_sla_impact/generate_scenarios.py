#!/usr/bin/env python3
"""
Generate Baseline and Proposed Scenario Files for Wholesale SLA Impact Demo

This script generates FOUR scenario files:

EVEN DISTRIBUTION (all 15 agents serve all customers):
1. baseline_even_scenario.yaml - All 13 customers with foc_target=8.0, has_sla=False
2. proposed_even_scenario.yaml - 1 SLA customer (CUST_A) with foc_target=1.0, has_sla=True

DEDICATED AGENTS (2 agents for CUST_A, 13 agents for CUST_B-M):
3. baseline_dedicated_scenario.yaml - All 13 customers with foc_target=8.0, has_sla=False
4. proposed_dedicated_scenario.yaml - 1 SLA customer (CUST_A) with foc_target=1.0, has_sla=True

Total: 500 requests from 13 customers, 15 agents
- 1 SLA customer (CUST_A): 30 requests (6%)
- 12 Non-SLA customers (CUST_B-M): 470 requests (94%)
"""

import yaml
from typing import List, Dict


# Customer configuration
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


def generate_agents_even() -> List[Dict]:
    """Generate 15 wholesale team agents - ALL agents can serve ALL customers"""
    
    # Agent name pools for variety
    first_names = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie', 
                   'Drew', 'Avery', 'Quinn', 'Dakota', 'Skyler', 'Cameron', 'Peyton', 'Reese']
    
    last_names = ['Thompson', 'Martinez', 'Chen', 'Kim', 'Rodriguez', 'Patel', 
                  'Anderson', 'Williams', 'Johnson', 'Davis', 'Brown', 'Garcia', 
                  'Miller', 'Wilson', 'Moore']
    
    # Skillset distribution patterns
    skillset_patterns = [
        ['WholesaleBasic', 'WholesaleAdvanced'],           # 7 agents
        ['WholesaleBasic', 'WholesaleExpert'],             # 4 agents
        ['WholesaleBasic', 'WholesaleAdvanced', 'WholesaleExpert'],  # 4 agents
    ]
    
    agents = []
    for i in range(15):
        agent_id = f'AGENT{i+1:03d}'
        full_name = f'{first_names[i]} {last_names[i]}'
        
        # Distribute skillsets
        if i < 7:  # First 7 agents
            skillsets = skillset_patterns[0]
        elif i < 11:  # Next 4 agents
            skillsets = skillset_patterns[1]
        else:  # Last 4 agents
            skillsets = skillset_patterns[2]
        
        agents.append({
            'agent_id': agent_id,
            'full_name': full_name,
            'skillsets': skillsets,
            'team': 'wholesale_all'  # All agents serve all customers
        })
    
    return agents


def generate_agents_dedicated() -> List[Dict]:
    """
    Generate 15 wholesale team agents with DEDICATED assignments:
    - 2 agents DEDICATED to CUST_A (SLA customer)
    - 13 agents DEDICATED to CUST_B-M (Non-SLA customers)
    """
    
    first_names = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie', 
                   'Drew', 'Avery', 'Quinn', 'Dakota', 'Skyler', 'Cameron', 'Peyton', 'Reese']
    
    last_names = ['Thompson', 'Martinez', 'Chen', 'Kim', 'Rodriguez', 'Patel', 
                  'Anderson', 'Williams', 'Johnson', 'Davis', 'Brown', 'Garcia', 
                  'Miller', 'Wilson', 'Moore']
    
    skillset_patterns = [
        ['WholesaleBasic', 'WholesaleAdvanced'],
        ['WholesaleBasic', 'WholesaleExpert'],
        ['WholesaleBasic', 'WholesaleAdvanced', 'WholesaleExpert'],
    ]
    
    agents = []
    
    # First 2 agents: DEDICATED to CUST_A (SLA customer)
    for i in range(2):
        agent_id = f'AGENT{i+1:03d}'
        full_name = f'{first_names[i]} {last_names[i]}'
        skillsets = skillset_patterns[2]  # Best skillsets for SLA customer
        
        agents.append({
            'agent_id': agent_id,
            'full_name': full_name,
            'skillsets': skillsets,
            'team': 'wholesale_sla',
            'dedicated_customers': ['CUST_A']  # Only serve CUST_A
        })
    
    # Remaining 13 agents: DEDICATED to CUST_B-M (Non-SLA customers)
    non_sla_customers = list(NON_SLA_CUSTOMERS.keys())
    
    for i in range(2, 15):
        agent_id = f'AGENT{i+1:03d}'
        full_name = f'{first_names[i]} {last_names[i]}'
        
        # Distribute skillsets
        if i < 9:
            skillsets = skillset_patterns[0]
        elif i < 13:
            skillsets = skillset_patterns[1]
        else:
            skillsets = skillset_patterns[2]
        
        agents.append({
            'agent_id': agent_id,
            'full_name': full_name,
            'skillsets': skillsets,
            'team': 'wholesale_nonsla',
            'dedicated_customers': non_sla_customers  # Only serve CUST_B-M
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


def generate_baseline_even_scenario() -> Dict:
    """Generate baseline scenario - EVEN distribution - all customers without SLA"""
    print("Generating baseline (EVEN distribution) scenario...")
    
    scenario = {
        'name': 'Baseline - Even Distribution (No SLA)',
        'description': 'Current state with 500 requests from 13 customers. All 15 agents serve all customers evenly. All customers have 8-day FOC target with no SLA.',
        'start_time': '2024-01-15T09:00:00-05:00',
        'routing_config': {
            'pilot_program_enabled': True,
            'agent_distribution': 'even'
        },
        'agents': generate_agents_even(),
        'requests': []
    }
    
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


def generate_proposed_even_scenario() -> Dict:
    """Generate proposed scenario - EVEN distribution - 1 customer with SLA"""
    print("\nGenerating proposed (EVEN distribution) scenario...")
    
    scenario = {
        'name': 'Proposed - Even Distribution (1 SLA Customer)',
        'description': 'Proposed state with 1 SLA customer (CUST_A: foc_target=1.0 day, has_sla=True). All 15 agents serve all customers evenly.',
        'start_time': '2024-01-15T09:00:00-05:00',
        'routing_config': {
            'pilot_program_enabled': True,
            'agent_distribution': 'even'
        },
        'agents': generate_agents_even(),
        'requests': []
    }
    
    start_offset = 1
    
    # SLA customer (foc_target=1.0, has_sla=True)
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


def generate_baseline_dedicated_scenario() -> Dict:
    """Generate baseline scenario - DEDICATED agents - all customers without SLA"""
    print("\nGenerating baseline (DEDICATED agents) scenario...")
    
    scenario = {
        'name': 'Baseline - Dedicated Agents (No SLA)',
        'description': 'Current state with 500 requests from 13 customers. 2 agents dedicated to CUST_A, 13 agents dedicated to CUST_B-M. All customers have 8-day FOC target with no SLA.',
        'start_time': '2024-01-15T09:00:00-05:00',
        'routing_config': {
            'pilot_program_enabled': True,
            'agent_distribution': 'dedicated'
        },
        'agents': generate_agents_dedicated(),
        'requests': []
    }
    
    start_offset = 1
    
    # SLA customer (but not SLA yet in baseline)
    for customer_id, num_requests in SLA_CUSTOMER.items():
        requests = generate_requests(customer_id, num_requests, foc_target=8.0, has_sla=False, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} requests for {customer_id} (2 dedicated agents)")
    
    # Non-SLA customers
    for customer_id, num_requests in NON_SLA_CUSTOMERS.items():
        requests = generate_requests(customer_id, num_requests, foc_target=8.0, has_sla=False, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} requests for {customer_id}")
    
    print(f"Total requests: {len(scenario['requests'])}, 13 agents for CUST_B-M")
    return scenario


def generate_proposed_dedicated_scenario() -> Dict:
    """Generate proposed scenario - DEDICATED agents - 1 customer with SLA"""
    print("\nGenerating proposed (DEDICATED agents) scenario...")
    
    scenario = {
        'name': 'Proposed - Dedicated Agents (1 SLA Customer)',
        'description': 'Proposed state with 1 SLA customer (CUST_A: foc_target=1.0 day, has_sla=True). 2 agents dedicated to CUST_A, 13 agents dedicated to CUST_B-M.',
        'start_time': '2024-01-15T09:00:00-05:00',
        'routing_config': {
            'pilot_program_enabled': True,
            'agent_distribution': 'dedicated'
        },
        'agents': generate_agents_dedicated(),
        'requests': []
    }
    
    start_offset = 1
    
    # SLA customer (foc_target=1.0, has_sla=True)
    for customer_id, num_requests in SLA_CUSTOMER.items():
        requests = generate_requests(customer_id, num_requests, foc_target=1.0, has_sla=True, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} SLA requests for {customer_id} (2 dedicated agents)")
    
    # Non-SLA customers (foc_target=8.0, has_sla=False)
    for customer_id, num_requests in NON_SLA_CUSTOMERS.items():
        requests = generate_requests(customer_id, num_requests, foc_target=8.0, has_sla=False, start_offset=start_offset)
        scenario['requests'].extend(requests)
        start_offset += num_requests
        print(f"  Added {num_requests} non-SLA requests for {customer_id}")
    
    print(f"Total requests: {len(scenario['requests'])}, 13 agents for CUST_B-M")
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
    print("  Agents: 15 (Wholesale team)")
    print()
    print("Generating 4 scenarios:")
    print("  1. Baseline - Even distribution (all agents serve all customers)")
    print("  2. Proposed - Even distribution (1 SLA customer)")
    print("  3. Baseline - Dedicated agents (2 for CUST_A, 13 for others)")
    print("  4. Proposed - Dedicated agents (1 SLA customer)")
    print()
    
    # Generate baseline - even
    baseline_even = generate_baseline_even_scenario()
    save_scenario(baseline_even, 'demo/demo_wholesale_sla_impact/scenarios/baseline_even_scenario.yaml')
    
    # Generate proposed - even
    proposed_even = generate_proposed_even_scenario()
    save_scenario(proposed_even, 'demo/demo_wholesale_sla_impact/scenarios/proposed_even_scenario.yaml')
    
    # Generate baseline - dedicated
    baseline_dedicated = generate_baseline_dedicated_scenario()
    save_scenario(baseline_dedicated, 'demo/demo_wholesale_sla_impact/scenarios/baseline_dedicated_scenario.yaml')
    
    # Generate proposed - dedicated
    proposed_dedicated = generate_proposed_dedicated_scenario()
    save_scenario(proposed_dedicated, 'demo/demo_wholesale_sla_impact/scenarios/proposed_dedicated_scenario.yaml')
    
    print()
    print("=" * 80)
    print("Scenario generation complete!")
    print("=" * 80)
    print()
    print("Scenario files created:")
    print("  1. scenarios/baseline_even_scenario.yaml")
    print("  2. scenarios/proposed_even_scenario.yaml")
    print("  3. scenarios/baseline_dedicated_scenario.yaml")
    print("  4. scenarios/proposed_dedicated_scenario.yaml")
    print()
    print("Next steps:")
    print("  To compare EVEN distribution scenarios:")
    print("    python compare_foc_impact.py scenarios/baseline_even_scenario.yaml scenarios/proposed_even_scenario.yaml")
    print()
    print("  To compare DEDICATED agent scenarios:")
    print("    python compare_foc_impact.py scenarios/baseline_dedicated_scenario.yaml scenarios/proposed_dedicated_scenario.yaml")
    print()
    print("  To run full simulation for EVEN distribution:")
    print("    python run_full_simulation.py --baseline scenarios/baseline_even_scenario.yaml --proposed scenarios/proposed_even_scenario.yaml")
    print()
    print("  To run full simulation for DEDICATED agents:")
    print("    python run_full_simulation.py --baseline scenarios/baseline_dedicated_scenario.yaml --proposed scenarios/proposed_dedicated_scenario.yaml")


if __name__ == '__main__':
    main()