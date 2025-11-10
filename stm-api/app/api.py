import asyncio
import sys
sys.path.append('..')
import time
import pandas as pd
import pyodbc
import logging
import asyncio
import uuid
from asyncio import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Header, Query
from fastapi_versioning import versioned_api_route
import urllib3
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.Elastic.elastic_settings import INDEX_NAME
from app.GetWorkFlow.service import RoutingService, SmartpathAPI
from contextlib import closing
from datetime import datetime, timezone
from shared.db import DB

from app.models import (
    HomeDTO,
    Work,
    WorkLog,
    ElasticRequests
)
from shared.all_envs import ENVIRONMENT, API_VERSION, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS, TD_HOST, TD_USER, TD_PASS

logger = logging.getLogger("API log")



router_v1 = APIRouter(route_class=versioned_api_route(1, 0))
auth_token = ""
df_foc_targets = pd.DataFrame()

QualtricsNotRechabled = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Failed to reach the Qualtrics API",
)

# Initialize Cache
e_requests = ElasticRequests()

# Initialize a Global Lock for Push Model
work_lock = Lock()

@router_v1.get(
    "/",
    tags=["Version"],
    summary="Version",
    description="This endpoint will details version and environment of STM API.",
    response_model=HomeDTO,
    status_code=200,
    response_model_exclude_unset=True,
)
def home():
    """
    Returns API version and environment details.

    This endpoint is used for checking the current version and environment 
    configuration of the STM API.

    Returns:
        HomeDTO: A response object containing environment and API version details.
    """
    response = HomeDTO()
    response.environment = ENVIRONMENT
    response.api_version = API_VERSION
    #response.ai_version = f"Only to show how to use it {DB.agent()}"
    return response

@router_v1.get(
    "/work/agent/{agent_id}",
    tags=["Work"],
    summary="Get Agent Work",
    description="Get a new request for an agent.",
    response_model=Work,
    status_code=200,
    response_model_exclude_unset=True,
)
async def get_work(agent_id: str, background_tasks: BackgroundTasks, tenant: str = Query(''), x_correlation_id: str = Header(None), x_authorization_for: str = Header(auth_token), from_push_model: bool = False):
    """
    Assigns a new work request to an agent.

    This endpoint validates the agent, fetches a new request, integrates with 
    Smartpath APIs, and logs details in the database.

    Args:
        agent_id (str): The ID of the agent requesting work.
        background_tasks (BackgroundTasks): Background task manager for logging.
        tenant (str, optional): Tenant identifier. Defaults to an empty string.
        x_correlation_id (str, optional): Correlation ID for request tracking.
        x_authorization_for (str, optional): Authorization token.
        from_push_model (bool, optional): Indicates if the request comes from a push model.

    Returns:
        Work: The work object containing request details.

    Raises:
        HTTPException: If agent is not found or external API calls fail.
    """
    try:
        global e_requests
        start_get_work_time = time.time()
        logger.info(f"Get Work: [BellAD={agent_id}, tenant={tenant}, correlation_id={x_correlation_id}]")

        work = Work()
        work.agentId = agent_id
        work.correlationId = x_correlation_id
        work.status = "NO WORK"
        work.tenant = tenant
        workLog = WorkLog(
            agentId=work.agentId, 
            correlationId=work.correlationId, 
            status=work.status, 
            tenant=work.tenant
        )    
        con_mssql = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')

        # Create a service class
        service = RoutingService(
            con_mssql=con_mssql,
            agent_id=agent_id,
            db_agent=DB.agent(),
            db_escalation=DB.escalation(),
            tenant=tenant,
            x_correlation_id=x_correlation_id
        )
        
        # Check if agent exists, otherwise API response 404
        if not await service.agent_exists_async():
            logger.error(f"Agent {agent_id} not found, correlation_id={service.x_correlation_id}")
            raise HTTPException(404, "Agent not found")

        start_time = time.time()
        request, status = await service.run(e_requests)
        if request is not None:
            e_requests.assigne_request(request['requestId'])
        end_time = time.time()
        service_run_latency = end_time - start_time

        if status == "NO REQUEST RETURNED":
            work.status = "NO_WORK"
            logger.error(f"No request ID found, correlation_id={service.x_correlation_id}")
        elif status == "NO ASSIGNMENT":
            work.status = "NO_ASSIGNMENT"
        else:
            work.status = "WORK"
            work.requestId = request['requestId']
            # e_requests.assigne_request(work.requestId)
            workLog.externalId = request['externalId']
            workLog.fromAbsentAgent = str(request['fromAbsentAgent'])
            workLog.skillId = request['skillId']
            workLog.skillName = request['skillName']
            workLog.followUpDate = request['followUpDate'] if not pd.isnull(request['followUpDate']) else None
            workLog.requestSource = request['requestSource']
            workLog.product = request['product']
            workLog.serviceRegion = request['serviceRegion']
            workLog.requestType = request['requestType']
            workLog.customerSupportModel = request['customerSupportModel']
            workLog.controlDesk = request['controlDesk']
            workLog.goldenCustomerName = request['goldenCustomerName'] if request['goldenCustomerName'] != 'nan' else None
            workLog.customerMarketSegment = request['customerMarketSegment']
            workLog.preferredLanguage = request['preferredLanguage']
            workLog.referredType = request['referredType']
            workLog.orderDate = request['requestOrderDate']
            workLog.ttpu = request['focTarget']
            workLog.priorityScore = request['score']
            workLog.requestStatus = request['requestStatus']
            workLog.requestAssignee = request['requestAssignee'] if request['requestAssignee'] != 'nan' else None
            workLog.isEscalated = request['is_escalated']
            workLog.hasSla = request['has_sla']
            workLog.skillPriority = request['skillPriority']
            logger.info(f"Request id {work.requestId} ready for assignment, skill_id={workLog.skillId}, skill_priority={workLog.skillPriority}, from_absent_agent={workLog.fromAbsentAgent}, correlation_id={workLog.correlationId}")

        get_agent_name_latency = 0
        post_event_latency = 0
        assign_request_latency = 0
        workLog.smartpathLatency = 0
        workLog.status = work.status
        workLog.requestId = work.requestId

        # Update info on Smartpath APIs
        if work.status == "WORK":

            start_time = time.time()
            # Get Agent full name, necessary for the event API
            full_name = await service.get_agent_name_async()
            end_time = time.time()
            get_agent_name_latency = end_time - start_time

            smtpth_api = SmartpathAPI(
                agent_id=workLog.agentId, 
                full_name=full_name,
                request_id=workLog.requestId,
                skill_id=workLog.skillId,
                auth_token=auth_token,
                correlation_id=workLog.correlationId,
                from_absent_agent=workLog.fromAbsentAgent,
                referredType=workLog.referredType,
                x_authorization_for=x_authorization_for
            )   

            if from_push_model:
                event_start_time = time.time()
                response_api = await smtpth_api.assign_push_model_request()
                event_end_time = time.time()
                response_api_latency = event_end_time - event_start_time
                logger.info(f"Time taken for smtpth_api.assign_push_model_request(): {response_api_latency} seconds")

                if response_api.status_code not in (200,201): 
                    logger.error(f"Smartpath change_assignee_and_order_status event failed, Status Code: {response_api.status_code}, Response: {response_api.text}, correlation_id={smtpth_api.correlation_id}")
                    raise HTTPException(500, "Smartpath change_assignee_and_order_status event failed")
                else:
                    workLog.smartpathLatency = response_api_latency
                    logger.info(f"Smartpath change_assignee_and_order_status event successful, correlation_id={smtpth_api.correlation_id}")
            else:
                # Post on Smartpath APIs for change assignee and event creation
                date = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('Z', '+00:00')
                post_event_start_time = time.time()
                response_event = await smtpth_api.post_event(date)
                post_event_end_time = time.time()
                post_event_latency = post_event_end_time - post_event_start_time
                logger.info(f"Time taken for smtpth_api.post_event(date): {post_event_latency} seconds")
                
                if response_event.status_code not in (200,201): 
                    logger.error(f"Smartpath request status change failed, Status Code: {response_event.status_code}, Response: {response_event.text}, correlation_id={smtpth_api.correlation_id}")
                    raise HTTPException(500, "Smartpath request status change failed")
                else:
                    logger.info(f"Post event successful, correlation_id={smtpth_api.correlation_id}")
                    assign_request_start_time = time.time()
                    response_assign = await smtpth_api.assign_request()
                    assign_request_end_time = time.time()
                    assign_request_latency = assign_request_end_time - assign_request_start_time
                    logger.info(f"Time taken for smtpth_api.assign_request(): {assign_request_latency} seconds")  

                    if response_assign.status_code not in (200,201):
                        logger.error(f"Smartpath request change assignee failed, Status Code: {response_assign.status_code}, Response: {response_assign.text}, correlation_id={smtpth_api.correlation_id}")
                        raise HTTPException(500, "Smartpath request assign to agent failed")
                    else:
                        workLog.smartpathLatency = post_event_latency + assign_request_latency 
                        logger.info(f"Change assignee successful, correlation_id={smtpth_api.correlation_id}")

        end_get_work_time = time.time()
        workLog.globalLatency = end_get_work_time - start_get_work_time
        workLog.stmLatency = workLog.globalLatency - workLog.smartpathLatency
        workLog.assignDate = datetime.now(timezone.utc)
        logger.info(f"Work Status: {workLog.status}, Time taken for get_work(): {round(workLog.globalLatency, 2)}s, service_run: {round(service_run_latency, 2)}s, get_agent_name: {round(get_agent_name_latency, 2)}s, post_event: {round(post_event_latency, 2)}s, assign_request: {round(assign_request_latency, 2)}s")

        # Background task to run work.add_work_to_database()
        if workLog.correlationId.endswith("_push_model"):
            asyncio.create_task(workLog.add_work_to_database())
        else:
            background_tasks.add_task(workLog.add_work_to_database)

        # Close the MS SQL connection
        con_mssql.close()
        
        return work
    except HTTPException as e:
        logger.exception(f"Get Work - Smartpath API Response Error: status_code - {e.status_code} and message - {e.detail}")

def fetch_idle_agents_data():
    """
    Fetches idle agent IDs from the database.

    Queries the database to find agents who are marked as 'available' 
    and have not been updated for at least 2.5 minutes.

    Returns:
        List[str]: A list of agent IDs who are idle.

    Raises:
        Exception: Logs an error if database queries fail.
    """
    with closing(
            pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
            ) as conn_stm:
        #Fetch unique agents from getwork_table
        query_agent= f"""
        SELECT distinct agent_id 
        FROM {DB.push_model_agents()}
        """
        stm_agent_ids = pd.read_sql(query_agent, conn_stm)
        agent_ids = stm_agent_ids['agent_id'].tolist()
        if not agent_ids:
            logger.info("No agents found in STM")
            return []
        agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
        agent_ids_str = f"({agent_ids_str})"
        #Fetch idle agents using status from disposition status table
        query_idle= f"""
        SELECT agent_id 
        FROM {DB.disposition_status()} 
        WHERE agent_id in {agent_ids_str} AND status = 'available'
        AND last_updated <= DATEADD(minute, -2.5, GETUTCDATE())
        """
        idle_agents = pd.read_sql(query_idle, conn_stm)
        idle_agents_ids = idle_agents['agent_id'].tolist()
        if not idle_agents_ids:
            logger.info('No idle agents available')
            return []
        return idle_agents_ids

async def get_idle_agents():
    """
    Retrieves a list of idle agent IDs asynchronously.

    Executes the fetch operation using fetch_idle_agents_data within an 
    executor to ensure non-blocking behavior.

    Returns:
        List[str]: A list of agent IDs who are idle.

    Raises:
        Exception: Logs an exception if the fetch operation fails.
    """
    loop = asyncio.get_running_loop()
    try:
        idle_agents = await loop.run_in_executor(None, fetch_idle_agents_data)
        if idle_agents:
            logger.info("Fetched Idle Agents from STM")
        return idle_agents
    except Exception as e:
        logger.exception(f"Error in get_idle_agents: {e}")
        return []
    
async def push_model():
    """
    Push model to assign work requests to idle agents.

    This function runs sequentially with a global lock to:
      - Fetch idle agents from the database.
      - Call get_work for each idle agent to assign a new request.
      - Log the assigned requests for auditing.

    Returns:
        None

    Raises:
        Exception: Logs errors if fetching idle agents or assigning work fails.
    """
    request_objects = {}
    background_tasks = BackgroundTasks()
    
    async with work_lock:
        await asyncio.sleep(3) 
        # Get the list of idle agents
        idle_agents = await get_idle_agents()

        # Generate a unique correlation ID for all calls in this loop
        correlation_prefix = str(uuid.uuid4())

        # Loop through the agents sequentially
        for agent_id in idle_agents:
            result = await get_work(agent_id, background_tasks, tenant='BBM', x_correlation_id=correlation_prefix+'_push_model', x_authorization_for='', from_push_model=True)
            request_objects[agent_id] = result

    logger.info(f"Here are the requests objects for idle agents: {request_objects}")