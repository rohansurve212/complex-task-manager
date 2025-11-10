import sys
sys.path.append('..')
from STM.models import Escalation
from STM.documents import *
from datetime import datetime
import pandas as pd
from django.utils import timezone
import logging
import requests
import pyodbc
from shared.all_envs import SQL_SERVER, DATABASE, SQL_USER, SQL_PASS
from shared.db import DB

# Set up logger for the script
logger = logging.getLogger("Escalation_Django log")

from shared.all_envs import SMARTPATH_ENV, sp_vars

# Disable SSL warnings for insecure requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

accessToken = ''

# Get Token
def get_token():
    """Post request to generate authentication token"""

    logging.info("Getting new token")
    # Determine URL based on the environment (qa, uat, prod)
    if SMARTPATH_ENV.lower() in ['qa', 'uat', 'prod']:
        url = f"{sp_vars.base_url}/login/oauth"
    else:
        url = f"{sp_vars.base_url}/auth/realms/oc/protocol/openid-connect/token"

    payload = f"grant_type=password&client_id=oc-backend&client_secret={sp_vars.client_secret}&username={sp_vars.user}&password={sp_vars.pw}"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 's_fid=58721E86E26E77E4-333FBE8EFDDF0106; s_vi=[CS]v1|32365FED0A8D54B4-600006F320DD0574[CE]; BBMUID=SegmentMode=enterprise&VisitorID=1ea58976-83b6-4b68-a91f-0a37ab0ce780; gemini=region=ON|language=en|province=ON|LarSegmentType=; _fbp=fb.1.1687448725416.419022717; _ga_RHH5313TEK=GS1.1.1687456148.2.0.1687456148.60.0.0; lanAkamaPro=AwccyOOIAQAADyyvlaPpPB3hJ5E-G_80EPjQP8AC3hEVi8OOoeeSLeqYjzH0Ac4v-f6uchRAwH8AAEB3AAAAAA|1|0|6860dd40df50ce0a5bdcde8180209c8a7a734759; TLTUID=A3CB92DEB8AEE242E3689C4F5ECDFAA1; AMCV_48B034FA53CF9FD10A490D44%40AdobeOrg=359503849%7CMCAID%7C32365FED0A8D54B4-600006F320DD0574%7CMCIDTS%7C19538%7CMCMID%7C06075730019815422410473480349897117208%7CMCAAMLH-1688607936%7C7%7CMCAAMB-1688607936%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1688010336s%7CNONE%7CvVersion%7C5.0.1; _scid=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _tt_enable_cookie=1; _ttp=_Tv5AkV0165AYbf_3iAbh7Emi-X; _clck=15juquh|2|fcv|0|1268; _sctr=1%7C1687924800000; _ga=GA1.1.261313119.1687448724; mbox=PC#23b4832a551440a3b7046de8ae2d1a17.34_0#1750693525|session#e0646a19b7b84e2a80cb0cd0492f5fdb#1688005007; coveo_visitorId=d6814970-47a9-46ec-e571-f71c19475d29; da_lid=9189AD439A73EA13C3A2BB99FF50E1D537|0|0|0; _uetvid=ce188cb0111311ee95e49935519933ad; nmstat=1b5c442c-eb6a-5d56-1c80-c87712f28163; _scid_r=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _ga_MK50H7QB2L=GS1.1.1688003136.4.1.1688003156.40.0.0; _ga_MTKGWZ28E4=GS1.1.1688003139.1.1.1688003156.43.0.0; _pk_id.5.ecd4=291887ad27d2b0f1.1690296106.; rxVisitor=1684848599996B0QJR243N77UR4O8TPRV35E06H5A2OE4; bportal_idp={"lang":"en_CA"}; dtCookie=v_4_srv_10_sn_EFE556BC52013C84752C418672B05DEA_perc_100000_ol_0_mul_1_app-3A46f1a806c667dad3_1_rcs-3Acss_0; s_cc=true; db4fdfa0d404bc10acda4670ccb15825=ae7fcf030e5768885ef7f6d977792d24; dtLatC=2; OC_LANDING_PAGE=/smartpath; BEPSESSION=kU9NJQL5wjVEi30zbeIey8NpGb4Mxni19DGasnLsJ+515qSLCj8TddknUBVYeG5qyBJpgVKJCpoAtvlE2MJ+705r9G7dD4F2bHcD2vt0gKxoWqLjvgCHWzi2SXxE0/XT3ce/mLr7KbMdErrW+9kng7q0b45rL5/mbkiBC2D/vk73cSzzEu/3ZtYrUIE36MHh3ySxr5aUykz+BfsXh8Drls5gU+YNjY2L1xJkX9pMKXp2FlsR5pOEqSUk7djWofmJK2RyZoNcbYI7m03zLikxittMktVoNcHARW9mt3/rqQd87sItbZ++bwqcE47zLu2zsKOZ4AwRVK/GKI1l9HFjqDUbpmW6brQYbLTdYKPhuyEm0xSGdrmlDVoDRF6EDjEMTzsPztNIOXluHkaoV+FH9q/+yOEEkq6mBT8wXkhyROhKJzpMllOiJ0QxTLF0o42o2qAE+a0DLEkyl4/r8tFaeYyiXnCbx6MWKrqs9WTymjqCBBX6KenpExTCwpGIdjuzk3NfCGFvPCmw6SlEY41tEIOTBB5WJLogBqSkIAGN6On8MsXTcE93jPmPhpDIKFCWTySl3CMAZfZPtpqNBT12FuQHAzLeSfHbHTsQC/Rzs6nO0ooaa93JozMVMqgNcp7gXNbpiS4AfB2Pdio8ERvrATRsacmN9FN1sRLzqFC8JTPKuojw1sPatdSAbL6e+p8i1WpuKQZeIj0ezalriCnj7Up/uaL22s+EniobP0wICzdIWHrU8HdbokTgYxSR0bjKZSN6iv44DpfhTX2kM5fcltYfSvkQ26e0J0Fy1+Q5q/nnG4OSDGGoz1bFF8egdy2Roqq6OF+B7toDOQWnnYfslDxU6UpjOmH60fFzgO0rWY6zUVU6SnDqpORvnTYbGivg3pH6bzSqSOPR0kH7U6Afv3tdZxc1Y85LWLZO1dFAJIbOlUw0kp8PUxojaA0lnB9UNT05lZ9PnhYbnDzhe+wHPZCVm2611sBb8fTf8EvzN+A/Kt7fDtpQbh3BlhoraFK8yFJ/Gq/tLbjsgZEc6u9ul3MCLYQDGa+JH+KTel6sjw37XbtXqVSHr7Pz7bHqLPJWYmG+QdNYh5+vbjaL4znBEYkC0rnm/Fn2dq0x2RCZfvGd93datOjeQ7orO5P8ne+q1OcRQDvZQGOdHzbyQ62Un2QfUyGYQRX/6NlAR1b1UlPpoNiSsibxrtm6DT8NH9YU; TLP02cf917d=028702b9c911061a52c6537f5a87d8725222b3b5683ccab826ae08dddb71cd0a2d842da2260eea176cb7bec3fcae9645896ed4d3abd382d2c362c501ab6763ad764342332efc04d6b21c8328afa1e3b305d9687d5c9464ffa00b26b97355f9ac39391a1376; 769825ffaec97adc91f8e9803cedd989=fb29a90fe5d229d94cf8584ad8c2460a; rxvt=1695308553252|1695306752165; dtPC=10$306752161_486h-vEFQTJRUMMBJIDMFLQOCUFARFPAOGMPUE-0e0; s_tp=2205; s_ppve=Our%2520company%253ANews%2520and%2520events%253ABellnet%2520news%253AArticle%2520page%2C60%2C33%2C1323; dtSa=true%7CS%7C-1%7C-%7C-%7C1695306756108%7C306752161_486%7Chttps%3A%2F%2Fbellnet.int.bell.ca%2Fabout-bell%2Fnews%2F20230920-healing-session-on-thursday-for-2slgbtqia-team-members%7C%7C%7C%7C; _pk_ref.5.ecd4=%5B%22%22%2C%22%22%2C1695327883%2C%22%2Fsmartpath%2Fdetails%2Fbsd_REQQA-1031585%22%5D; _pk_ses.5.ecd4=1; OCWEBSESSIONID=573b5a51-a7f6-41d6-839c-a60fdd8445df'
    }

    proxies = {
            "http": None,
            "https": None
        }

    # Make a POST request to get the service token from the API
    service_token = requests.request("POST", url, headers=headers, data=payload, proxies=proxies, verify=False)
    token = json.loads(service_token.text)['access_token']
    logging.info("Token updated")
    return token

def get_all_requests(all_requests, accessToken):
    all_request_ids=[]
    
    # If no requests are available, log and return
    if ((all_requests is None) or (len(all_requests) == 0)):
        logger.debug(f"No escalation requests, requestall is none")
        return
    
    # Extract request IDs from all requests
    for item in all_requests:
        all_request_ids.append(item.request_id)

    # Fetch all requests from the Smartpath API
    all_request_response = get_all_requests_from_smtpth_elastic(all_request_ids, accessToken)
    all_request_response_text = json.loads(all_request_response.text)
    all_request_objects = all_request_response_text['results']

    return all_request_objects

def get_assigned_date(conn, externalIds):
    # Prepare a query to get the max assignment date for each externalId
    placeholders = ', '.join(['?'] * len(externalIds))
    qry = f"""
        SELECT external_id, MAX(assign_date) as assign_date
        FROM {DB.getwork_results()}
        WHERE external_id IN ({placeholders})
        GROUP BY external_id
    """
    c = conn.cursor()
    try:
        result = c.execute(qry, externalIds).fetchall()
        assigned_dates = {row[0]: row[1] for row in result}
        logger.info(f"Successfully fetched assigned_date.")
    except pyodbc.Error as e:
        logger.info(f"Error occurred when fetching assigned_date: ", e)
        assigned_dates = {}

    return assigned_dates

class BackgroundClass:

    @staticmethod
    def update_escalation():
        
        accessToken = get_token()

        Time_threshold = timezone.now()-timezone.timedelta(hours=2)
        
        assigned_requests=[]
        unassigned_requests=[]
        completed_requests = []
        cancelled_requests = []

        # Fetch all active (not completed or cancelled) escalation requests
        all_requests = Escalation.objects.exclude(status='completed').exclude(status='cancelled')
        all_request_objects = get_all_requests(all_requests, accessToken)

        # Categorize requests based on their status in Smartpath
        for item in all_requests:
            if request_is_completed(item.request_id, all_request_objects)==True:
                completed_requests.append(item.request_id)
            if request_is_cancelled(item.request_id, all_request_objects)==True:
                cancelled_requests.append(item.request_id)
            else:
                if request_is_assigned(item.request_id, all_request_objects)==True:
                    assigned_requests.append(item.request_id)
                else:
                    unassigned_requests.append(item.request_id)

        try: 
            # Filter for priority 2 requests that are open and older than 2 hours
            priority_submissionfilter=Escalation.objects.all().filter(priority=2,status ='open', submission_dt__lt=Time_threshold)
            for item in priority_submissionfilter:
                # Update priority to 1 for these requests
                item.priority = 1
                item.update()
                logger.debug(f"{item.request_id} priority is now updated to - {item.priority}. Its submission date is {item.submission_dt}")
        except Exception as e:
            logger.error(f"Error in updating priority - {e}")  

        try: 
            # Filter for requests that are assigned and update their status to 'assigned'
            status_requestfilter=Escalation.objects.filter(request_id__in=assigned_requests).filter(status = 'open')
            for item in status_requestfilter:
                item.status = 'assigned'
                item.update()
                logger.debug(f'{item.request_id}  had status - open and is now updated to - assigned')
        except Exception as e:
            logger.error(f"Error in updating status to assigned - {e}")

        try: 
            # Filter for unassigned requests and update their status to 'open'
            status_requestfilter=Escalation.objects.filter(request_id__in=unassigned_requests).filter(status = 'assigned')
            for item in status_requestfilter:
                item.status = 'open'
                item.update()
                logger.debug(f'{item.request_id} had status - assigned and is now updated to - open')
        except Exception as e:
            logger.error(f"Error in updating status to open - {e}")

        try:
            # Filter for requests that need to be marked as 'completed'
            completed_requestfilter=Escalation.objects.filter(request_id__in=completed_requests).exclude(status='completed')
            for item in completed_requestfilter:
                before_update_status = item.status
                item.status = 'completed'
                item.update()
                logger.debug(f'{item.request_id} had status - {before_update_status} is now updated to - completed')
        except Exception as e:
            logger.error(f"Error in updating status to completed - {e}")

        try:
            # Filter for requests that need to be marked as 'cancelled'
            cancelled_requestfilter=Escalation.objects.filter(request_id__in=cancelled_requests).exclude(status='cancelled')
            for item in cancelled_requestfilter:
                before_update_status = item.status
                item.status = 'cancelled'
                item.update()
                logger.debug(f'{item.request_id} had status - {before_update_status} is now updated to - cancelled')
        except Exception as e:
            logger.error(f"Error in updating status to cancelled - {e}")

    
    @staticmethod
    def fetch_assigned_date():
        try:
            conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
            accessToken = get_token()
            all_requests = Escalation.objects.exclude(status='completed').exclude(status='cancelled')
            all_request_objects = get_all_requests(all_requests, accessToken)
            ids = []
            for obj in all_request_objects:
                ids.append(obj['source']['externalId'])
            # Fetch assigned dates for the requests
            assigned_dates = get_assigned_date(conn, ids)
            if len(assigned_dates) > 0:
                # Update the assigned date for each request in the Escalation table
                for requestId, assigned_date in assigned_dates.items():
                    if assigned_date:
                        Escalation.objects.filter(request_id=requestId).update(assigned_dt=assigned_date)
        except Exception as e:
            logger.error(f"Error in fetching assigned dates - {e}")
