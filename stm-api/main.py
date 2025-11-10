import sys
sys.path.append('..')
import json
from datetime import datetime, timedelta, time
import pyodbc
import httpx
import pandas as pd
from shared.db import DB
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
import asyncio
from fastapi import FastAPI
import requests
from fastapi_versioning import VersionedFastAPI
from starlette.responses import RedirectResponse
from contextlib import closing
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from app import api
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning # type: ignore
from shared.all_envs import sp_vars, SMARTPATH_ENV, LOGGER_LEVEL, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS, TD_HOST, TD_USER, TD_PASS, ENABLE_PUSH_MODEL

# Custom TimedRotatingFileHandler to flush after each log entry
class FlushingTimedRotatingFileHandler(TimedRotatingFileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Logger setup
level_debug = LOGGER_LEVEL
if level_debug:
    logging.getLogger().setLevel(level_debug)
    print("Logging LEVEL IS {}".format(level_debug))
else:
    logging.getLogger().setLevel('INFO')
    print("Logging LEVEL IS INFO ")
logger = logging.getLogger("API log")

# File Handler
handler = FlushingTimedRotatingFileHandler('log/api.log',when="midnight",interval=1,backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = FastAPI(title="STM API")
app.include_router(api.router_v1)
app = VersionedFastAPI(app, version_format="{major}", prefix_format="/v{major}")
logger.info(f"smartpath env is ------> {SMARTPATH_ENV}")
eastern = ZoneInfo('America/New_York')
scheduler = AsyncIOScheduler(timezone=eastern)

# This must be after VersionedFastAPI to avoid being include in the /v1 path
@app.get(
    "/",
    tags=["Redirect"],
    summary="Redirect to version 1",
    description="Redirect to version 1 to avoid new user being confused",
    status_code=200,
    response_model_exclude_unset=True,
)
def redirect():
    """
    Redirect to the version 1 API endpoint.

    Returns:
        RedirectResponse: Redirects the user to /v1 endpoint.
    """
    return RedirectResponse(url='/v1')

@api.router_v1.get("/refresh-token")
def get_refresh_token():
    """
    Trigger the process to refresh the authentication token.

    Returns:
        str: A message indicating that the refresh process is in progress.
    """
    refresh_token()
    return "in-progress"

async def get_token():
    """
    Generate a new authentication token.

    This function sends an HTTP POST request to the appropriate OAuth endpoint
    to retrieve a new authentication token based on the current environment.

    Returns:
        str: The new access token.
    """
    logging.info("Getting new token")
    if SMARTPATH_ENV.lower() == 'qa' or SMARTPATH_ENV.lower() == 'prod':
        url = f"{sp_vars.base_url}/login/oauth"
    else:
        url = f"{sp_vars.base_url}/auth/realms/oc/protocol/openid-connect/token"

    payload=f"grant_type=password&client_id=oc-backend&client_secret={sp_vars.client_secret}&username={sp_vars.user}&password={sp_vars.pw}"
            
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 's_fid=58721E86E26E77E4-333FBE8EFDDF0106; s_vi=[CS]v1|32365FED0A8D54B4-600006F320DD0574[CE]; showprovinceselector=true; BBMUID=SegmentMode=enterprise&VisitorID=1ea58976-83b6-4b68-a91f-0a37ab0ce780; gemini=region=ON|language=en|province=ON|LarSegmentType=; _gcl_au=1.1.447402542.1687448725; _fbp=fb.1.1687448725416.419022717; _ga_RHH5313TEK=GS1.1.1687456148.2.0.1687456148.60.0.0; lanAkamaPro=AwccyOOIAQAADyyvlaPpPB3hJ5E-G_80EPjQP8AC3hEVi8OOoeeSLeqYjzH0Ac4v-f6uchRAwH8AAEB3AAAAAA|1|0|6860dd40df50ce0a5bdcde8180209c8a7a734759; TLTUID=A3CB92DEB8AEE242E3689C4F5ECDFAA1; AMCV_48B034FA53CF9FD10A490D44%40AdobeOrg=359503849%7CMCAID%7C32365FED0A8D54B4-600006F320DD0574%7CMCIDTS%7C19538%7CMCMID%7C06075730019815422410473480349897117208%7CMCAAMLH-1688607936%7C7%7CMCAAMB-1688607936%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1688010336s%7CNONE%7CvVersion%7C5.0.1; _scid=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _tt_enable_cookie=1; _ttp=_Tv5AkV0165AYbf_3iAbh7Emi-X; _clck=15juquh|2|fcv|0|1268; _sctr=1%7C1687924800000; _ga=GA1.1.261313119.1687448724; mbox=PC#23b4832a551440a3b7046de8ae2d1a17.34_0#1750693525|session#e0646a19b7b84e2a80cb0cd0492f5fdb#1688005007; coveo_visitorId=d6814970-47a9-46ec-e571-f71c19475d29; da_lid=9189AD439A73EA13C3A2BB99FF50E1D537|0|0|0; _uetvid=ce188cb0111311ee95e49935519933ad; nmstat=1b5c442c-eb6a-5d56-1c80-c87712f28163; _scid_r=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _ga_MK50H7QB2L=GS1.1.1688003136.4.1.1688003156.40.0.0; _ga_MTKGWZ28E4=GS1.1.1688003139.1.1.1688003156.43.0.0; _pk_id.5.ecd4=291887ad27d2b0f1.1690296106.; rxVisitor=1684848599996B0QJR243N77UR4O8TPRV35E06H5A2OE4; bportal_idp={"lang":"en_CA"}; dtCookie=v_4_srv_10_sn_EFE556BC52013C84752C418672B05DEA_perc_100000_ol_0_mul_1_app-3A46f1a806c667dad3_1_rcs-3Acss_0; s_cc=true; db4fdfa0d404bc10acda4670ccb15825=ae7fcf030e5768885ef7f6d977792d24; BEPSESSION=Hj9sxRCX3xUMh5fr5C/MZfjYs1KsKfA95BWMb8vxSF58Qyx+WlYhKlajfXHQ2Iwrj8q9I82MKUT80snQoIqCywrGco+qZ759VH0VuiwZl+ENm0b/ac6KBRDaY70oOEWozIqhUNJkEghy5NQWFOQmWDVe/kYNm1tlEBS2+lvLL5pn39jNiLfxII5G+aWRA5vNe8vanArvK9U+OWiVbpFOYAogp3DQFbae9C143oBG+fN4BHaSkKn2xQV7wfXod/2urWJq2hqaswXiLy16baTOBqS2PfT56jK+GUkIN5m4FZetcMHPK4SBumKHvDhuIe4N29qR2YiLkB0pJm71O3ZoFymkvFPRFISLoToccQYIIX1dZ5rU4p867ef3CWZ8mGnhi5Aucgo+bohVSFu8Wd8CQe+1sXtuTki7DjPjWtkta5cZl1IpI3V8ppTPKF9cPc9a8Vd0eG8b7yKwPfiKwfJNXFQJ0Eq745ARSDNdUQPQOSQ6JyinOUufkXsBcjYOzG3R+aqPxfBMQ0uA406TsJBwOYqlRTL0sW06W0+1o0WhdDsYWCHL/aF0XmJdp1xNFrD7G9OwWd25aeZOBNohgk5NRMuDK6hq1e80MzVe6dTFp8VBw8hfRMdu9aer0wXiLI9/IrK6L/fILjSi1EKOAsWd8+M9oTSIdYVTqKj+20vV1Z/WLbGQYQquFfY1SrgwUSoVBLFF6Np2tSCJ/cE3lXwUwHEQF9ks+xCXBhnIujsgPIH64VEskJi0eYUwGkEfTA+vhImkz65+hYDfnXNIK9qewGenpeNorLeMo3HfAAXLutBwXUWCM27kzVCElsdNK1NOop34Szbihtk/2A29qV7MN2JDYdXRqKJAnowT3ui6s+7WZw8Ay0EKjF3FlHaBr6ZWTlILxIAPOhEsFF86qoQwutK7fGw+XkCJqHCeWGCL4Usugjb1xNroHRHBr8OOWz6nOGkCvcrS5adbRrqFpbH39rlVzC2KBp1tnjgoC1BnDJqN8AF1pLN8yXc/eC/dqJuLH5GSPu4pn2h6exIZFwwFSzmOiXUImQ3YpKXuUOqJL4uECFlAbpQ4TMBepCBi/WgRzUr6kIYcvzApTJoLrSYzPs7EhWNc61tj/lGGmJvVBaBM/+u5nRFG2zAHvsr+M4/VxH6M24fR6FshWi8TkME5BEgOoMFcR1H7AOQE/O7htbwnJiCrjpTzNgSdGMrnY82g; TLP02cf917d=028702b9c998ef57c8c76da9b6ed3547e6d98aa0a43ccab826ae08dddb71cd0a2d842da2260eea176cb7bec3fcae9645896ed4d3abd382d2c362c501ab6763ad764342332efc04d6b21c8328afa1e3b305d9687d5c7b09eac6b98e47297972ea85b3c1fae7; dtSa=-; s_tp=2091; dtLatC=2; s_ppve=Home%253AEmployee%2520directory%2C78%2C35%2C1623; dtPC=10$139104432_495h-vUMBRNBCDJDVRCIBRPDHOUNQARBCERTMM-0e0; rxvt=1694544668475|1694542868475; OC_LANDING_PAGE=/smartpath; 769825ffaec97adc91f8e9803cedd989=3c463ca99ef037c713222b995f8a4f12; _pk_ref.5.ecd4=%5B%22%22%2C%22%22%2C1695064287%2C%22%2Fsmartpath%2Fconfirm%22%5D; _pk_ses.5.ecd4=1; OCWEBSESSIONID=2f297798-d5f0-49cd-abca-73091d48a37f'
    }

    proxies = {
            "http://": None,
            "https://": None
        }
    
    # Use httpx.AsyncClient for asynchronous http requests
    async with httpx.AsyncClient(proxies=proxies, verify=False) as client:
        service_token = await client.post(url, headers=headers, content=payload)

    token = json.loads(service_token.text)['access_token']
    logging.info("Token updated")
    return token

async def refresh_token():
    """
    Periodically refresh the authentication token.

    Retries the token generation process every 2 seconds until a valid token is retrieved.
    """
    token_refreshed = False
    
    # Loop each 2 seconds until the auth_token is refreshed
    while not token_refreshed:
        try:    
            logger.info("refresh_token")
            api.auth_token = await get_token()
            token_refreshed = True
        except Exception:
            logger.exception('refresh_request_cache crash')
        
        if not token_refreshed:
            await asyncio.sleep(2)

async def load_foc_targets():
    """
    Load the FOC (Time to Pickup) targets from the JARVIS database.

    Retrieves SLA data from the database and updates the global dataframe df_foc_targets.
    """
    with closing(
        pyodbc.connect('DRIVER=Teradata Database ODBC Driver 17.20; DBCNAME='+TD_HOST+'; UID='+TD_USER+'; PWD='+TD_PASS+';')
        ) as conn:
        sql_foc_targets = f"""SELECT product AS workOrder_product,  
                                     request_type AS source_requestType, 
                                     time_to_pickup_target_days AS source_focTarget_new,
                                     contract_sla AS has_sla_new,
                                     gk_id AS source_goldenCustomer_id,
                                     control_desk AS workOrder_controlDesk
                              FROM {DB.sla()};"""
        df = pd.read_sql(sql_foc_targets, conn)
        # Fill missing gk_ids with 0, then convert them to integers followed by converting to strings
        df['source_goldenCustomer_id'] = df['source_goldenCustomer_id'].astype(str)
        df.replace('NA', 'nan', inplace=True)
        api.df_foc_targets = df
    logger.info("FOC-TARGET TABLE LOADED")

@app.on_event("startup")
async def init_request_cache():
    """
    Initialize the request cache and load necessary data.

    This function generates the initial authentication token, loads the SLA table, 
    and initializes the request cache for the API.
    """
    logger.info("init_token")
    api.auth_token = await get_token()
    await load_foc_targets()

    logger.info("e_requests.init_cache()")
    await api.e_requests.init_cache()

async def refresh_request_cache():
    """
    Refresh the request cache.

    This updates the in-memory request cache to ensure it stays up-to-date.
    """
    try:
        # logger.info("e_requests.update_cache()")
        await api.e_requests.update_cache()
    except Exception:
        logger.exception('refresh_request_cache crash')

async def export_request_cache():
    """
    Export the request cache.

    Exports the current state of the request cache for logging or persistence purposes.
    """
    try:
        await api.e_requests.export_cache()
    except Exception:
        logger.exception('export_request_cache crash')

async def repeater(func, interval, first_run_time=None):
    """
    Run a given function repeatedly at a specified interval.

    Args:
        func (function): The function to be executed repeatedly.
        interval (int): Time interval (in seconds) between function executions.
        first_run_time (datetime.time, optional): Optional specific time for the first run.

    The function ensures the first execution occurs at the specified time, and 
    subsequent executions run at regular intervals.
    """
    while True:
        if first_run_time:
            # Calculate the delay until the next occurrence of first_run_time
            now = datetime.now()
            target_time = now.replace(hour=first_run_time.hour, minute=first_run_time.minute, second=0, microsecond=0)
            
            if now > target_time:  # If the target time has passed today, schedule for tomorrow
                target_time += timedelta(days=1)

            delay_until_first_run = (target_time - now).total_seconds()
            await asyncio.sleep(delay_until_first_run)

            # Run the function for the first time at the target time
            await func()

            # Then reset the first_run_time to None to switch to regular interval execution
            first_run_time = None
        else:
            await func()

        # Wait for the interval duration
        await asyncio.sleep(interval)

def add_cron_job_to_scheduler():
    """
    Schedule the push_model function to run periodically.

    The scheduler triggers the job on weekdays (Monday to Friday) every 3 minutes,
    between 7 AM and 5 PM (Eastern Time).
    """
    cron_trigger = CronTrigger(
        day_of_week='mon-fri', 
        hour='7-17', 
        minute='*/3',
        timezone=eastern
    )
    scheduler.add_job(
        api.push_model, 
        trigger=cron_trigger,
        misfire_grace_time=300,
        coalesce=True,
        max_instances=1
    )
    logger.info("Scheduled push_model to run on weekdays from 7 AM to 6 PM, every 3 minutes")

async def start_scheduler():
    """
    Start the job scheduler.

    This function initializes and starts the scheduler that manages the periodic 
    execution of background jobs like push_model.
    """
    add_cron_job_to_scheduler()
    scheduler.start()
    logger.info("Scheduler started successfully")

@app.on_event("startup")
async def startup_event():
    """
    Define startup events for the FastAPI application.

    Schedules the following tasks to run periodically:
    - refresh_request_cache: Every 3 seconds.
    - refresh_token: Every 55 minutes.
    - load_foc_targets: Once every 24 hours.
    - export_request_cache: Daily at 12:00 UTC (8:00 AM EST).

    If push model is enabled, the scheduler starts to handle push-based assignments.
    """
    if ENABLE_PUSH_MODEL == 'True':
        asyncio.create_task(start_scheduler()) # start the push model scheduler
    asyncio.create_task(repeater(refresh_request_cache, 3)) # sleep for 3 seconds
    asyncio.create_task(repeater(refresh_token, 60 * 55)) # each 55 min as the token expired after 60 min
    asyncio.create_task(repeater(load_foc_targets, 3600 * 24)) # load the slas table once every 24 hours
    asyncio.create_task(repeater(export_request_cache, 3600 * 24, first_run_time=time(12, 0))) # run once every day at 12:00 HRS UTC OR 8:00 HRS EST

# application runs on port 8000 (see Dockerfile)
# port 8886 can be used from within VS code for debugging
if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.exception(f"Error occurred on starting the application: {e}")
    finally:
        logger.info("Flushing all the logger handlers")
        for handler in logger.handlers:
            handler.flush()
