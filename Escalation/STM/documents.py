# Importing necessary libraries
import json
import requests
import logging

# Importing shared environment variables
from shared.all_envs import sp_vars

# Set up logger for the "Escalation_Django log"
logger = logging.getLogger("Escalation_Django log")

# Function to find a request by its ID in a given request list
def find_request_by_id(request_id, request_list):
    # Iterate through the list to find a matching request ID
    for obj in request_list:
        if obj['source']['externalId'] == request_id:
                return [obj]  # Return the matching request as a list
    return None  # Return None if no match is found

# Function to get all requests from the SmartPath elastic service using a list of request IDs
def get_all_requests_from_smtpth_elastic(request_id_list, access_token) -> dict:
    try:
        # Define the URL for the API request
        url = f"{sp_vars.base_url}/smartpath/smarttask/order/_startScroll?offset=0&limit=10000&fields="

        # Create the request payload as JSON, including the list of request IDs to filter by
        payload = json.dumps({
            "@type": "SearchDetails",
            "@baseType": "SearchDetails",
            "@schemaLocation": "",
            "name": "smarttask",
            "filter": [
                {
                    "@type": "AttributeFilter",
                    "@baseType": "AttributeFilter",
                    "@schemaLocation": "",
                    "field": "source.externalId",
                    "value": request_id_list,
                    "operator": "eq",
                    "caseInsensitive": "true"
                }
            ] 
        })

        # Set the headers, including the authorization token
        auth_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        # Set proxies for the request (currently set to None)
        proxies = {
            "http": None,
            "https": None
        }

        # Make the POST request and return the response
        return requests.request("POST", url, headers=auth_headers, data=payload, proxies=proxies, verify=False)
    
    except Exception as e:
        # Log any errors encountered during the request
        logger.error(f"Error in executing get_all_requests_from_smtpth_elastic(): {e}")

# Function to get a specific request from SmartPath elastic service using a single request ID
def get_request_from_smtpth_elastic(request_id, access_token) -> dict:
    try:
        # Define the URL for the API request
        url = f"{sp_vars.base_url}/smartpath/smarttask/order/_startScroll?offset=0&limit=1&fields="

        # Create the request payload as JSON, filtering by a single request ID
        payload = json.dumps({
            "@type": "SearchDetails",
            "@baseType": "SearchDetails",
            "@schemaLocation": "",
            "name": "smarttask",
            "filter": [
                {
                    "@type": "AttributeFilter",
                    "@baseType": "AttributeFilter",
                    "@schemaLocation": "",
                    "field": "source.externalId",
                    "value": [
                        request_id
                    ],
                    "operator": "eq",
                    "caseInsensitive": "true"
                }
            ] 
        })

        # Set the headers, including the authorization token
        auth_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        # Set proxies for the request (currently set to None)
        proxies = {
            "http": None,
            "https": None
        }

        # Make the POST request and return the response
        return requests.request("POST", url, headers=auth_headers, data=payload, proxies=proxies, verify=False)
    
    except Exception as e:
        # Log any errors encountered during the request
        logger.error(f"Error in executing get_request_from_smtpth_elastic(): {e}")

# Function to check if a request exists in a given list by its ID
def request_exists(request_id, request_list) -> bool:
    try:
        # Use find_request_by_id to search for the request ID in the list
        results = find_request_by_id(request_id, request_list)

        # Return True if the request exists, False otherwise
        if results is not None:
            return True
        return False
    
    except Exception as e:
        # Log any errors encountered during the check
        logger.error(f"Error in executing request_exists(): {e}")

# Function to check if a request is assigned by its ID in the request list
def request_is_assigned(request_id, request_list) -> bool:
    try:
        # Use find_request_by_id to search for the request ID in the list
        results = find_request_by_id(request_id, request_list)

        # Check if the request is assigned by looking for the 'assignee' key
        if results is not None:
            request = results[0]
            if 'assignee' in request['workOrder'].keys():
                return True  # Return True if assigned
            return False  # Return False if not assigned
        
    except Exception as e:
        # Log any errors encountered during the check
        logger.error(f"Error in executing is_status_assigned(): {e}")

# Function to check if a request has been completed by its ID in the request list
def request_is_completed(request_id, request_list):
    try:
        # Use find_request_by_id to search for the request ID in the list
        results = find_request_by_id(request_id, request_list)

        # Check if the request is completed by comparing the status
        if results is not None:
            request = results[0]
            if request['workOrder']['status'] == 'completed':
                return True  # Return True if completed
            return False  # Return False if not completed
        
    except Exception as e:
        # Log any errors encountered during the check
        print("Error", e)
        logger.error(f"Error in executing is_completed(): {e}")

# Function to check if a request has been cancelled by its ID in the request list
def request_is_cancelled(request_id, request_list):
    try:
        # Use find_request_by_id to search for the request ID in the list
        results = find_request_by_id(request_id, request_list)

        # Check if the request is cancelled by comparing the status
        if results is not None:
            request = results[0]
            if request['workOrder']['status'] == 'cancelled':
                return True  # Return True if cancelled
            return False  # Return False if not cancelled
        
    except Exception as e:
        # Log any errors encountered during the check
        print("Error", e)
        logger.error(f"Error in executing is_cancelled(): {e}")

# Function to check the control desk before escalation for a request ID
def check_control_desk_before_escalation(request_id, request_list):
    try:
        # Use find_request_by_id to search for the request ID in the list
        results = find_request_by_id(request_id, request_list)

        # Check if the request's control desk is either retailEscalation or wholesaleEscalation
        if results is not None:
            request = results[0]
            if (request['workOrder']['controlDesk'] == 'retailEscalation') or (request['workOrder']['controlDesk'] == 'wholesaleEscalation'):
                return True  # Return True if it's for escalation
            return False  # Return False if not for escalation
        
    except Exception as e:
        # Log any errors encountered during the check
        print("Error", e)
        logger.error(f"Error in executing check_control_desk_before_escalation(): {e}")