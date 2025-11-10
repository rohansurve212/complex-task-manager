import glob
import os
import sys
sys.path.append('..')
from contextlib import closing
from humps import camelize
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
import pyodbc
import logging
import asyncio
from shared.db import DB
from shared.all_envs import DEFAULT_CACHE_HISTORY, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS
from app.GetWorkFlow.search_requests import updated_elastic_to_df
from app.GetWorkFlow.search_requests_utils import (
    elastic_response_to_df,
    get_requests_from_smartpath_elastic
)
from app.Elastic.elastic_settings import query_fields

logger = logging.getLogger("API log")

query_fields = [
    "request_id", "source.externalId", "lastUpdated", "accessPolicyTag", "workOrder.status", "workOrder.product", "workOrder.followUpDate", "workOrder.controlDesk", "workOrder.group", "workOrder.assignee.id", "workOrder.tags", "source.orderDate", "source.requestedStartDate", 
    "source.requestType", "source.requestSource", "source.customerSupportModel",
    "source.businessUnit", "source.status", "source.product", "source.serviceRegion", "source.goldenCustomer.id", "source.goldenCustomer.name",
    "source.customer", "source.customerMarketSegment", "source.preferredLanguage", "source.focTarget", "has_sla", "source.referredType", "source.originator.email", "workOrder.expectedCompletionDate"
    ]

class Base(BaseModel):
    """
    Base class for Pydantic models with camelCase aliasing.

    This class provides a configuration to convert field names from snake_case to camelCase
    when serializing data.

    Attributes:
        Config (class): Configuration for alias generation.
    """
    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True

class HomeDTO(Base):
    """
    Data model representing API version and environment details.

    Attributes:
        environment (str): The environment of the API (e.g., dev, prod).
        api_version (str): The current version of the API.
        ai_version (str): The version of the AI-related components of the API.
    """
    environment: str = Field(None, description="The environment of the API")
    api_version: str = Field(None, description="The current version of the API")
    ai_version: str = Field(None, description="The current version of the API")

class Work(Base):
    """
    Data model for agent work request response.

    Attributes:
        agentId (str): The ID of the agent requesting work.
        requestId (str): The unique ID of the assigned request.
        correlationId (str): A unique correlation ID for tracking the request.
        status (str): The status of the request (e.g., WORK, NO_WORK).
        tenant (str): The tenant information for the agent.
    """
    agentId: str = Field(None, description="The agent's id to get a new request.")
    requestId: str = Field(None, description="The request's id. This field will be null if status is NO_WORK or NO_ASSIGNMENT.")
    correlationId: str = Field(None, description="The id used to track a user request from Smartpath.")
    status: str = Field(None, description="The status of the requestId")
    tenant: str = Field(None, description="The tenant of the agent.")

class WorkLog(Work):
    """
    Extended data model for detailed work log tracking.

    This class extends the Work class and includes additional attributes for logging work 
    details and metrics such as latency, skill information, and SLA.

    Attributes:
        externalId (str): The external ID of the request.
        assignDate (datetime): The timestamp when the request was assigned.
        followUpDate (datetime): Date for follow-up actions.
        fromAbsentAgent (str): Flag indicating if the request was reassigned from an absent agent.
        skillId (str): The ID of the routing filter skill.
        skillName (str): The name of the routing filter skill.
        requestSource (str): Source of the request.
        product (str): Product associated with the request.
        serviceRegion (str): Service region of the request.
        requestType (str): Type/category of the request.
        customerSupportModel (str): Customer support model.
        controlDesk (str): Control desk associated with the request.
        goldenCustomerName (str): Name of the golden customer.
        customerMarketSegment (str): Market segment of the customer.
        preferredLanguage (str): Preferred language of communication.
        referredType (str): Type of referral.
        orderDate (datetime): Timestamp when the order was created.
        ttpu (float): Time-to-pickup target in days.
        priorityScore (float): Priority score assigned to the request.
        requestStatus (str): Current status of the request.
        requestAssignee (str): Current assignee of the request.
        globalLatency (float): Total latency of the getWork API.
        smartpathLatency (float): Latency of Smartpath-related API calls.
        stmLatency (float): Latency excluding Smartpath API calls.
        isEscalated (int): Flag indicating if the request is escalated.
        hasSla (int): Flag indicating if the request has SLA compliance.
        skillPriority (int): Priority of the skill.

    Methods:
        add_work_to_database():
            Inserts work log details into the getwork_results SQL table.
    """
    externalId: str = Field(None, description="The externalId of the request")
    assignDate: datetime = Field(None, description="The timestamp when request was picked up by SAIRA.")
    followUpDate : datetime = Field(None, description="The date when a follow-up will be done on the request.")
    fromAbsentAgent: str = Field(None, description="Flag to determine if this request is currently assigned to an absent agent")
    skillId: str = Field(None, description="The routing filter id on which the request was matched with the agent")
    skillName: str = Field(None, description="The routing filter name on which the request was matched with the agent")
    requestSource: str = Field(None, description="The requestSource field on the request")
    product: str = Field(None, description="The product field on the request")
    serviceRegion: str = Field(None, description="The serviceRegion field on the request")
    requestType: str = Field(None, description="The requestType field on the request")
    customerSupportModel: str = Field(None, description="The customerSupportModel field on the request")
    controlDesk: str = Field(None, description="The controlDesk field on the request")
    goldenCustomerName: str = Field(None, description="The goldenCustomer field on the request")
    customerMarketSegment: str = Field(None, description="The customerMarketSegment field on the request")
    preferredLanguage: str = Field(None, description="The preferredLanguage field on the request")
    referredType: str = Field(None, description="The referredType field on the request")
    orderDate: datetime = Field(None, description="The timestamp when the request was created.")
    ttpu: float = Field(None, description="The ttpu value for the request.")
    priorityScore: float = Field(None, description="Priority score of the selected request")
    requestStatus: str = Field(None, description="The current status of the request")
    requestAssignee: str = Field(None, description="The current assignee on the request")
    globalLatency: float = Field(None, description="The overall latency of getWork API response.")
    smartpathLatency: float = Field(None, description="The total latency of the two SmartPath API responses within getWork.")
    stmLatency: float = Field(None, description="Global latency excluding SmartPath latency")
    isEscalated: int = Field(None, description="Flag to determine if this request is escalated")
    hasSla: int = Field(None, description="Flag to determine if this request has an SLA")
    skillPriority: int = Field(None, description="The priority of the skill")

    async def add_work_to_database(self):
        """
        Insert work log details into the SQL database.

        This function adds a row to the getwork_results table, ensuring data consistency 
        and handling database errors gracefully.

        Returns:
            None
        """
        def convert_to_python_type(value):
            """
            Convert NumPy data types to native Python types.

            Args:
                value (Any): A value that might contain a NumPy data type.

            Returns:
                Any: Converted value to native Python type.
            """
            if isinstance(value, np.generic):
                return value.item()
            return value
        
        with closing(
            pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
            ) as conn:
            qry = f"""
            INSERT INTO {DB.getwork_results()} (
                agent_id, request_id, work_status, orderdate, ttpu, priority_score, 
                assign_date, skill_id, skill_name, correlation_id, tenant, from_absent_agent, 
                request_source, product, service_region, request_type, customer_support_model, 
                control_desk, golden_customer, customer_market_segment, preferred_language, 
                referred_type,  request_status, request_assignee, global_latency, smartpath_latency, 
                stm_latency, external_id, followup_date, is_escalated, has_sla) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """
            values = (self.agentId, self.requestId, self.status, self.orderDate, self.ttpu, self.priorityScore, 
                    self.assignDate, self.skillId, self.skillName, self.correlationId, self.tenant, self.fromAbsentAgent, 
                    self.requestSource, self.product, self.serviceRegion, self.requestType, self.customerSupportModel, 
                    self.controlDesk, self.goldenCustomerName, self.customerMarketSegment, self.preferredLanguage, 
                    self.referredType, self.requestStatus, self.requestAssignee, self.globalLatency, self.smartpathLatency, 
                    self.stmLatency, self.externalId, self.followUpDate, self.isEscalated, self.hasSla)
                
            # Convert any NumPy types to native Python types
            values = tuple(convert_to_python_type(value) for value in values)

            try:
                c = conn.cursor()
                c.execute(qry, values)
                conn.commit()
                logger.debug(f"Successfully inserted into {DB.getwork_results()} table.")
            except pyodbc.Error as e:
                logger.debug(f"PyODBC Error occurred when inserting into {DB.getwork_results()}: ", e)
                conn.rollback()
            except Exception as e:
                logger.debug(f"General Error occurred when inserting into {DB.getwork_results()}: ", e)
                conn.rollback()

class ElasticRequests:
    """
    Class to manage Smartpath request caching.

    This class maintains an in-memory cache of Smartpath requests and tracks assigned requests.
    It provides methods to initialize, update, and export the cache.

    Attributes:
        elastic_df (pd.DataFrame): DataFrame holding the cached Smartpath requests.
        assigned_requests (pd.DataFrame): DataFrame tracking currently assigned requests.
        last_request_date (str): Timestamp of the last request cache update.

    Methods:
        init_cache():
            Initialize the request cache by fetching data from Smartpath ElasticSearch.
        update_cache():
            Update the request cache with new and updated requests.
        get_requests():
            Retrieve unassigned requests from the cache.
        assigne_request(request_id):
            Mark a request as assigned by updating the assigned_requests DataFrame.
        export_cache():
            Export the current cache to a CSV file and clean up old cache files.
        cleanup_old_files(directory, extension):
            Remove old files from a specified directory based on their age.
    """
    elastic_df: pd.DataFrame
    assigned_requests: pd.DataFrame
    
    def __init__(self):
        self.elastic_df = None  # Initialize elastic_df as None
    
    async def init_cache(self):
        """
        Initialize the Smartpath request cache.

        This method retrieves recent requests from Smartpath ElasticSearch, converts them into 
        a DataFrame, and initializes the assigned_requests DataFrame for tracking.

        Returns:
            None
        """
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Initializing ElasticRequests cache (attempt {attempt + 1}/{max_retries})")
                self.last_request_date = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
                
                # Reduced limit from 10000 to 8000 to prevent timeouts during initialization
                self.elastic_requests = await get_requests_from_smartpath_elastic(
                    (datetime.now(timezone.utc) - timedelta(days=DEFAULT_CACHE_HISTORY)).strftime('%Y-%m-%dT%H:%M:%S'), 
                    limit=8000, 
                    filter_comp=True
                )
                
                self.elastic_df = elastic_response_to_df(self.elastic_requests, query_fields)
                logger.info(f"Successfully initialized cache with {len(self.elastic_df)} requests")
                break
                
            except Exception as e:
                logger.error(f"Error initializing elastic requests cache (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying cache initialization in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Failed to initialize cache after all retries - initializing empty cache")
                    # Initialize with empty DataFrame to prevent None errors
                    self.elastic_df = pd.DataFrame()
                    self.elastic_requests = []
            
        self.assigned_requests = pd.DataFrame(columns=['request_id', 'assigned_date'])
        
    # Update Cache
    async def update_cache(self):
        """
        Update the Smartpath request cache with the latest data.

        Steps:
        1. Waits for initialization to complete with retry logic.
        2. Fetches requests updated since the last cache update.
        3. Merges the new data with the existing cache.
        4. Filters out unnecessary and completed/cancelled requests.
        5. Updates the last_request_date timestamp.
        6. Cleans up old entries from the assigned requests tracking.

        Returns:
            None
        """
        # Wait for initialization to complete with retry logic
        max_wait_attempts = 10
        wait_delay = 1  # seconds
        
        for attempt in range(max_wait_attempts):
            if self.elastic_df is not None:
                break
            logger.info(f'Waiting for initialization to complete (attempt {attempt + 1}/{max_wait_attempts})')
            await asyncio.sleep(wait_delay)
            wait_delay = min(wait_delay * 2, 10)  # Exponential backoff, max 10 seconds
        
        # Final check - if still not initialized, return
        if self.elastic_df is None:
            logger.warning('ElasticRequests.update_cache was called before initialization was completed - skipping update after waiting')
            return
        
        try:
            logger.info(f'Updating Smartpath request cache since: {self.last_request_date}')
            # Use smaller limit to reduce scroll size and prevent timeouts
            new_e_requests_df = await updated_elastic_to_df(self.last_request_date, filter_comp=False, query_fields=query_fields)
            
            if new_e_requests_df.empty:
                logger.info('No new requests to add to cache')
            else:
                e_requests_df = pd.concat([self.elastic_df, new_e_requests_df], axis=0)
                e_requests_df = e_requests_df.drop_duplicates(subset='request_id', keep='last').reset_index(drop=True)
                self.elastic_df = e_requests_df[~e_requests_df.workOrder_controlDesk.isin([
                    "conferencing", "conferencingbilling", "conferencinggoc", "directorylisting", 
                    "managedservices", "managedservicesspoa", "pcoebbm", "vnet", "datagovernance",
                    "project", "mtsmajors", "mtswholesalevoice", "mtsbusinessinfra", "mtswholesaledata",
                    "mtsretaildata", "mtsporting", "mtsbizinet", "mtsinternaltelecom", "mtstrunkside",
                    "mtsbusinesstriage", "mtswholesalepic", "mtsclerks", "mtsgom", "mtsbusinesstclt",
                    "mtsbroadcast", "mtsgoc", "mtswholesaleleadhand"
                    ])]
                self.elastic_df = self.elastic_df[(self.elastic_df.source_status != 'cancelled') & (self.elastic_df.source_status != 'completed')]
                logger.info(f"Added {len(new_e_requests_df)} new requests to cache")
            
            self.last_request_date = (datetime.now(timezone.utc) - timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%S')
            
            # Flush to old assigned request 
            time = (datetime.now(timezone.utc) - timedelta(minutes=2))
            self.assigned_requests = self.assigned_requests.query('assigned_date >= @time')
            logger.info(f"Remaining assigned_requests: {len(self.assigned_requests)}. Updated Smartpath request cache on {(datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            logger.exception("Cache update failed")
        
    def get_requests(self):
        """
        Retrieve unassigned requests from the cache.

        This method filters out requests that are already marked as assigned.

        Returns:
            pd.DataFrame: A DataFrame of unassigned requests.
        """
        ids = self.assigned_requests['request_id']
        tmp = self.elastic_df.query('request_id not in @ids')
        return tmp

    def assigne_request(self, request_id):
        """
        Mark a request as assigned.

        Args:
            request_id (str): The unique ID of the request to be marked as assigned.

        Updates:
            Adds the request to the assigned_requests DataFrame with the current timestamp.
        """
        tmp = {
            'request_id': request_id,
            'assigned_date': datetime.now(timezone.utc),
        }
        self.assigned_requests.loc[len(self.assigned_requests)] = tmp

    # Export Cache
    async def export_cache(self):
        """
        Export the request cache to a CSV file.

        This method saves the current cache to a CSV file with a date-stamped filename. It also
        cleans up old CSV files older than 7 days.

        Returns:
            None
        """
        try:
            # Add date to the filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            if DB._env in ["PROD"]:
                filename = f"/app/log/updated_cache_{date_str}.csv"
                directory = "/app/log/"
            else:
                filename = f"updated_cache_{date_str}.csv"
                directory = "."

            # Save the DataFrame to a CSV file with the date in the filename
            self.elastic_df.to_csv(filename, encoding="utf-8")
            
            # Auto-delete CSV files older than 7 days
            self.cleanup_old_files(directory=directory)

        except Exception as e:
            logger.exception("Got error when exporting cache!", e)

    def cleanup_old_files(self, directory=".", extension="csv"):
        """
        Clean up old files from the cache directory.

        Args:
            directory (str): Directory containing the files to be cleaned up.
            extension (str): File extension of the files to be deleted (default is 'csv').

        Deletes:
            Files older than 7 days from the specified directory.

        Returns:
            None
        """
        try:
            # Calculate the cutoff time for old files
            cutoff_date = datetime.now() - timedelta(days=7)
            
            # Find all CSV files in the specified directory
            files = glob.glob(os.path.join(directory, f"*.{extension}"))
            
            for file_path in files:
                # Get the modification time of the file
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Check if the file is older than the cutoff date
                if file_mtime < cutoff_date:
                    os.remove(file_path)
                    logger.info(f"Deleted old file: {file_path}")

        except Exception as e:
            logger.exception("Error occurred during cleanup of old files", e)
