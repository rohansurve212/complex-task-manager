# Path - /app/GetWorkFlow/service.py

import sys
sys.path.append('..')
import time
import pandas as pd
import asyncio
import pyodbc
import httpx
from contextlib import contextmanager
from app import api
from app.GetWorkFlow.search_requests import (
    agent_permissions_async,
    agent_skillsets_async,
    agent_skills_config_async,
    skills_filtering,
    get_p1_escalation_async,
)
from app.GetWorkFlow.search_requests_utils import absent_agents_async
from app.GetWorkFlow.routing import routing
from datetime import datetime
from typing import Optional, List
import requests
import json
import logging

from shared.all_envs import sp_vars

logger = logging.getLogger("API log")

DF_TITLES = {
    0: "Escalated Winback",
    1: "Winback",
    2: "Escalated SLA",
    3: "SLA",
    4: "Escalated Non-SLA",
    5: "Commons"
}

class RoutingService:
    """
    Service class to manage agent work routing.

    This class handles the routing logic for agents by interacting with a database, 
    fetching requests, applying filtering logic, and selecting eligible requests 
    based on prioritization.

    Attributes:
        con_mssql (object): SQL Server connection object.
        agent_id (str): The ID of the agent for which the routing logic is performed.
        db_agent (str): Name of the database table containing agent details.
        db_escalation (str): Name of the database table containing escalation details.
        tenant (Optional[str]): Tenant identifier (default is an empty string).
        x_correlation_id (Optional[str]): Correlation ID for logging and tracking requests.
    """
    def __init__(
            self,
            con_mssql: object,
            agent_id: str,
            db_agent: str,
            db_escalation: str,
            tenant: Optional[str] = '',
            x_correlation_id:Optional[str]='') -> None:
        """
        Initialize the RoutingService object.

        Args:
            con_mssql (object): SQL Server connection object.
            agent_id (str): The ID of the agent.
            db_agent (str): Database table name for agent details.
            db_escalation (str): Database table name for escalation details.
            tenant (Optional[str], optional): Tenant identifier. Defaults to ''.
            x_correlation_id (Optional[str], optional): Correlation ID for logging. Defaults to ''.
        """
        self.con_mssql = con_mssql
        self.agent_id = agent_id
        self.tenant = tenant
        self.db_agent = db_agent
        self.db_escalation = db_escalation
        self.x_correlation_id = x_correlation_id

    @contextmanager
    def mssql_connection(self):
        """
        Context manager for the MSSQL database connection.

        Yields:
            object: The MSSQL database connection object.
        """
        yield self.con_mssql

    async def run(self, e_requests):
        """
        Execute the routing service logic for an agent.

        This method performs the following steps:
        1. Fetch agent skillsets, permissions, and configurations.
        2. Retrieve requests from the request cache.
        3. Apply filtering based on skills, escalations, and tenant details.
        4. Split requests into prioritized categories.
        5. Identify eligible requests and prioritize them.
        6. Return the most appropriate request for the agent.

        Args:
            e_requests (object): The ElasticRequests object containing the cached requests.

        Returns:
            Tuple[Optional[object], str]: A tuple containing the selected request (if any)
                                        and a status message.
        """
        logger.info(f"Starting service.run")

        # Fetch agent skillsets, permissions and skillset configurations
        skillsets = await agent_skillsets_async(self.mssql_connection, self.agent_id)
        permissions = await agent_permissions_async(self.mssql_connection, self.agent_id)
        configurations = await agent_skills_config_async(self.mssql_connection, skillsets)

        if len(skillsets) == 0:
            logger.error(f"No skillset found for agent {self.agent_id}, correlation_id={self.x_correlation_id}")
            return None, "NO ASSIGNMENT"

        if len(permissions) == 0: 
            logger.info(f"No permission found for agent {self.agent_id}, correlation_id={self.x_correlation_id}")
            return None, "NO ASSIGNMENT" 

        if len(configurations)==0: 
            logger.error(f"Skillset configuration failed, correlation_id={self.x_correlation_id}")
            return None, "NO ASSIGNMENT"
 
        # Gather all requests in a dataframe using the e_requests.get_requests() method
        df_requests = e_requests.get_requests()
 
        # Fetch absent agents, escalated requestIDs and sla customers
        all_absent_agent_ids = await absent_agents_async(self.mssql_connection)
        escalated_ids = await get_p1_escalation_async(self.mssql_connection, self.db_escalation)

        df_requests['is_escalated'] = df_requests['source_externalId'].isin(escalated_ids)
        df_requests['is_winback'] = df_requests['source_requestType'] == 'winback'

        atlantic_govt_customer_ids = ['1005108494', '1005110630', '1005055190']
        atlantic_control_desks = ['atlanticpns', 'atlanticwholesalewinback']
        df_requests['is_exclusive_atlantic_routingFilter'] = (
            df_requests['source_goldenCustomer_id'].isin(atlantic_govt_customer_ids) | 
            df_requests['workOrder_controlDesk'].isin(atlantic_control_desks)
        )

        # Skill filter on the whole dataset of requests to keep only the ones that are related to the agent's skillsets
        skills_filtering_start_time = time.time()
        df_filtered = skills_filtering(df_requests, configurations, permissions, self.tenant, all_absent_agent_ids, self.agent_id)
        skills_filtering_end_time = time.time()
        logger.info(f"Time taken for requests skills_filtering(): {skills_filtering_end_time - skills_filtering_start_time} seconds")

        # If there are no filtered requests
        if df_filtered.empty:
            logger.info(f"service.run ended with no request returned")
            return None, "NO REQUEST RETURNED"

        df_filtered['has_sla'] = df_filtered['has_sla'].astype('bool')
        
        # Split the requests into 6 dataframes based on the flags
        df_escalated_winback_excl_atl_rfs = df_filtered[((df_filtered['is_winback']) | (df_filtered['is_exclusive_atlantic_routingFilter'])) & (df_filtered['is_escalated'])]
        df_winback_excl_atl_rfs = df_filtered[((df_filtered['is_winback']) | (df_filtered['is_exclusive_atlantic_routingFilter'])) & (~df_filtered['is_escalated'])]
        df_escalated_sla = df_filtered[(df_filtered['has_sla']) & (df_filtered['is_escalated'])]
        df_escalated_non_sla = df_filtered[(~df_filtered['has_sla']) & (df_filtered['is_escalated'])]
        # df_sla = df_filtered[(df_filtered['has_sla']) & (~df_filtered['is_escalated'])]
        df_commons = df_filtered[~df_filtered['is_escalated']]

        logger.info(f"Amount of escalated winback requests or atl. RF requests: {len(df_escalated_winback_excl_atl_rfs)}")
        logger.info(f"Amount of non-escalated winback requests or atl. RF requests: {len(df_winback_excl_atl_rfs)}")
        logger.info(f"Amount of escalated SLA requests: {len(df_escalated_sla)}")
        logger.info(f"Amount of escalated non-SLA requests: {len(df_escalated_non_sla)}")
        logger.info(f"Amount of all other non-escalated requests: {len(df_commons)}")

        # Order the dataframes in a list
        dfs = [
                df_escalated_winback_excl_atl_rfs, 
                df_winback_excl_atl_rfs, 
                df_escalated_sla, 
                df_escalated_non_sla, 
                df_commons
              ]

        df_eligible = pd.DataFrame()

        # Iterate over the dataframes to find the first one that contains eligible requests
        for index, df in enumerate(dfs):
            if df.empty:
                continue
            else :
                df_eligible = df
                logger.info(f"Eligible requests found in the {DF_TITLES[index]} dataframe.")
                break
        # Convert is_escalated and has_sla to integers
        if not df_eligible.empty:
            df_eligible['is_escalated'] = df_eligible['is_escalated'].apply(lambda x: int(x))
            df_eligible['has_sla'] = df_eligible['has_sla'].apply(lambda x: int(x))

        # If P1 requests, only send them to prioritization, else send all P2 requests to prioritization
        if not df_eligible.empty:
            len_p1 = len(df_eligible.loc[df_eligible['skillPriority'] == 1])
            if len_p1 > 0:
                df_eligible = df_eligible.loc[df_eligible['skillPriority'] == 1]

        # Perform priorisation algorithm
        request = routing(df_eligible)
        if request is None:
            logger.info(f"service.run ended with no request returned")
            return None, "NO REQUEST RETURNED"

        logger.info(f"Completed service.run with request_id: {request.requestId} and skill_id: {request.skillId} and skill_priority: {request.skillPriority}")
        return request, "REQUEST RETURNED"

    async def agent_exists_async(self) -> bool:
        """
        Asynchronously check if the agent exists in the database.

        This method offloads synchronous database operations to a thread pool.

        Returns:
            bool: True if the agent exists, otherwise False.
        """
        loop = asyncio.get_running_loop()
        # Run the synchronous DB operation in a thread pool
        count = await loop.run_in_executor(None, self._check_agent_sync)
        return count > 0

    def _check_agent_sync(self):
        """
        Synchronous helper method to check for agent existence.

        Executes an SQL query to count the records matching the agent_id.

        Returns:
            int: The count of records matching the agent_id.
        """
        with self.mssql_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {self.db_agent} WHERE agent_id ='{self.agent_id}';")
            count = cur.fetchone()[0]
            return count

    async def get_agent_name_async(self) -> str:
        """
        Asynchronously retrieve the agent's full name from the database.

        This method uses a thread pool to offload synchronous database operations.

        Returns:
            str: The agent's full name, or the agent_id if the name is not found.
        """
        loop = asyncio.get_running_loop()
        # Run the synchronous DB operation in a thread pool
        name = await loop.run_in_executor(None, self._get_agent_name_sync)
        return name

    def _get_agent_name_sync(self) -> str:
        """
        Synchronous helper method to fetch the agent's full name.

        Executes an SQL query to retrieve the agent's full name based on agent_id.

        Returns:
            str: The agent's full name, or the agent_id if the name is not found.
        """
        with self.mssql_connection() as conn:
            cur = conn.cursor()
            sql_name = f"SELECT full_name FROM {self.db_agent} WHERE agent_id ='{self.agent_id}';"
            value = cur.execute(sql_name).fetchone()
            if value:
                return value[0]
            else:
                return self.agent_id
        
class SmartpathAPI:
    """
    SmartpathAPI class for interacting with Smartpath APIs.

    This class encapsulates API calls to Smartpath services, including assigning requests, 
    updating request statuses, and posting events. It supports both standard and push models 
    for request assignments.

    Attributes:
        agent_id (str): ID of the agent performing the action.
        full_name (str): Full name of the agent.
        request_id (str): ID of the request being assigned or updated.
        skill_id (str): ID of the skill/queue associated with the request.
        auth_token (str): Authentication token for API access.
        correlation_id (str): Correlation ID for tracking API calls.
        from_absent_agent (str): Indicates if the assignment is from an absent agent.
        referredType (str): Type of the referred request (e.g., ServiceOrder, ProductOrder).
        x_authorization_for (str): Authorization header value for event-related APIs.
    """
    def __init__(
            self,
            agent_id:str,
            full_name:str,
            request_id:str,
            skill_id:str,
            auth_token: str,
            correlation_id: str,
            from_absent_agent: str, 
            referredType: str,
            x_authorization_for: str) -> None:
        """
        Initialize the SmartpathAPI instance.

        Args:
            agent_id (str): ID of the agent.
            full_name (str): Full name of the agent.
            request_id (str): Request ID to be assigned or updated.
            skill_id (str): Skill/queue ID.
            auth_token (str): Authorization token for Smartpath API.
            correlation_id (str): Correlation ID for API tracking.
            from_absent_agent (str): Flag indicating assignment from absent agent ("True"/"False").
            referredType (str): Type of request being referred (e.g., ServiceOrder, ProductOrder).
            x_authorization_for (str): Header value for additional authorization.
        """
        self.agent_id = agent_id
        self.full_name = full_name
        self.request_id = request_id
        self.skill_id = skill_id
        self.auth_token = auth_token
        self.correlation_id = correlation_id
        self.from_absent_agent = from_absent_agent
        self.referredType = referredType
        self.x_authorization_for = x_authorization_for

    async def assign_request(self):
        """
        Assign a request to an agent using the Smartpath API.

        This method calls the /smarttask/assignee/_change endpoint to assign the specified 
        request to the given agent.

        Returns:
            response (httpx.Response): The response object from the Smartpath API.
        """
        url=f"{sp_vars.base_url}/smartpath/smarttask/assignee/_change?assigneeId={self.agent_id}&workOrderId={self.request_id}"
        payload = ""
        headers = self.get_auth_header_assign()
        proxies = {
            "http://": None,
            "https://": None
        }
        
        # Use httpx.AsyncClient for the asynchronous POST request
        async with httpx.AsyncClient(proxies = proxies, verify = False) as client:
            response = await client.post(url, headers=headers, data=payload)

        return response
    
    async def assign_push_model_request(self):
        """
        Assign a request to an agent using the push model in Smartpath.

        This method calls the /smarttask/order/_changeAssigneeAndOrderStatus endpoint to assign 
        a request and update its status for push model operations.

        Returns:
            response (httpx.Response): The response object from the Smartpath API.
        """
        url = f"{sp_vars.base_url}/smartpath/smarttask/order/_changeAssigneeAndOrderStatus?assigneeId={self.agent_id}&workOrderId={self.request_id}&queueId={self.skill_id}&followUpInAbsence={self.from_absent_agent}"
        payload = ""
        headers = self.get_auth_header_assigneeAndOrderStatus()
        proxies = {
            "http://": None,
            "https://": None
        }
        
        # Use httpx.AsyncClient for the asynchronous POST request
        async with httpx.AsyncClient(proxies = proxies, verify = False) as client:
            response = await client.post(url, headers=headers, data=payload)

        return response

    async def post_event(self, date):
        """
        Post an event to the Smartpath API.

        This method sends an event payload to the /smartpath/event endpoint, providing details 
        about the action, agent, and associated request.

        Args:
            date (str): The event timestamp in ISO format.

        Returns:
            response (httpx.Response): The response object from the Smartpath API.
        """
        url = f"{sp_vars.base_url}/smartpath/event"
        payload = json.dumps(self.make_request_body(
            agent_id = self.agent_id,
            correlation_id = self.correlation_id,
            date = date,
            request_id = self.request_id,
            full_name = self.full_name,
            skill_id = self.skill_id,
            from_absent_agent = self.from_absent_agent,
            referredType = self.referredType
            ))
        proxies = {
            "http://": None,
            "https://": None
        }
        headers = self.get_auth_header_event()

        # Use httpx.AsyncClient for the asynchronous POST request
        async with httpx.AsyncClient(proxies = proxies, verify = False) as client:
            response = await client.post(url, headers=headers, data=payload)

        return response

    def get_auth_header_assign(self):
        """
        Generate authorization headers for the request assignment API.

        Returns:
            dict: Authorization headers required for the /smarttask/assignee/_change endpoint.
        """
        return {
            'Content-Type': 'application/json',
            'x-correlation-id': self.correlation_id,
            'Authorization': f'Bearer {self.auth_token}',
            'x-authorization-for': self.x_authorization_for
        }
    
    def get_auth_header_assigneeAndOrderStatus(self):
        """
        Generate authorization headers for the push model API.

        Returns:
            dict: Authorization headers required for the /smarttask/order/_changeAssigneeAndOrderStatus endpoint.
        """
        return {
            'Content-Type': 'application/json',
            'x-correlation-id': self.correlation_id,
            'Authorization': f'Bearer {self.auth_token}'
        }

    def get_auth_header_event(self):
        """
        Generate authorization headers for the event posting API.

        Returns:
            dict: Authorization headers required for the /smartpath/event endpoint.
        """
        return {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Authorization': f'Bearer {self.auth_token}',
            'x-authorization-for': self.x_authorization_for
        }

    def make_request_body(self,
                          request_id,
                          date, 
                          correlation_id, 
                          agent_id, 
                          full_name, 
                          skill_id, 
                          from_absent_agent, 
                          referredType):
        """
        Create the request payload for the event API.

        Generates the payload body for the event endpoint based on the referred request type 
        (e.g., ServiceOrder or ProductOrder).

        Args:
            request_id (str): ID of the request.
            date (str): The event timestamp in ISO format.
            correlation_id (str): Correlation ID for tracking.
            agent_id (str): ID of the agent.
            full_name (str): Full name of the agent.
            skill_id (str): Queue/skill ID.
            from_absent_agent (str): Flag indicating assignment from an absent agent.
            referredType (str): Type of the referred request (e.g., ServiceOrder, ProductOrder).

        Returns:
            dict: The request body formatted for the Smartpath API.
        """
        if from_absent_agent == "True": 
            absence = "true"
        else:
            absence = "false"
        if referredType == "ServiceOrder":
            return {
                "dataDomain": "serviceOrder",
                "sourceId": f"{request_id}",
                "event": {
                    "@type": "Event",
                    "eventTime": f"{date}",
                    "eventType": "Action",
                    "correlationId": f"{correlation_id}",
                    "domain": "smartPathAction",
                    "title": "Service getWork",
                    "source": {
                        "@type": "EntityRef",
                        "id": f"{request_id}",
                        "href": f"/serviceOrder/{request_id}",
                        "@referredType": "BellServiceOrder"
                    },
                    "reportingSystem": {
                        "@type": "EntityRef",
                        "id": "STM",
                        "href": "/smarttask"
                    },
                    "relatedParty": [
                        {
                            "@type": "RelatedParty",
                            "id": f"{agent_id}",
                            "href": f"$.relatedParty[?(@.id=='{agent_id}')]",
                            "name": f"{full_name}",
                            "role": "Originator",
                            "@referredType": "Individual"
                        }
                    ],
                    "event": {
                        "@type": "ActionParamsEventPayload",
                        "actionKey": "serviceOrderWorkAssignment",
                        "params": {
                            "followUpInAbsence": f"{absence}",
                            "queueId": f"{skill_id}",
                            "order": f"{request_id}"
                        }
                    }
                }
            }
        elif referredType == "ProductOrder":
            return {
                "dataDomain": "productOrder",
                "sourceId": f"{request_id}",
                "event": {
                    "@type": "Event",
                    "eventTime": f"{date}",
                    "eventType": "Action",
                    "correlationId": f"{correlation_id}",
                    "domain": "smartPathAction",
                    "title": "Service getWork",
                    "source": {
                        "@type": "EntityRef",
                        "id": f"{request_id}",
                        "href": f"/serviceOrder/{request_id}",
                        "@referredType": "BellProductOrder"
                    },
                    "reportingSystem": {
                        "@type": "EntityRef",
                        "id": "STM",
                        "href": "/smarttask"
                    },
                    "relatedParty": [
                        {
                            "@type": "RelatedParty",
                            "id": f"{agent_id}",
                            "href": f"$.relatedParty[?(@.id=='{agent_id}')]",
                            "name": f"{full_name}",
                            "role": "Originator",
                            "@referredType": "Individual"
                        }
                    ],
                    "event": {
                        "@type": "ActionParamsEventPayload",
                        "actionKey": "serviceOrderWorkAssignment",
                        "params": {
                            "followUpInAbsence": f"{absence}",
                            "queueId": f"{skill_id}",
                            "order": f"{request_id}"
                        }
                    }
                }
            }
