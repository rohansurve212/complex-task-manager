import json
import argparse
import pyodbc
import logging
from datetime import datetime

import sys
sys.path.append('..')

from shared.db import DB
from shared.all_envs import SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

logger = logging.getLogger("Disposition codes log")

def update_is_absent(conn, agent_id, value):
    """Update is_absent column in agent table when agent status is changed to/from absent"""

    agent_update = f"""
    UPDATE {DB.agent()}
    SET is_absent = ?
    WHERE agent_id = ?
    """
    val = (value, agent_id)

    try:
        c = conn.cursor()
        c.execute(agent_update, val)
        conn.commit()
    except Exception as e:
        logger.exception(f"Error in updating is_absent to {value} for agent_id={agent_id}. Error message: {e}")
        conn.rollback()

def event_change(conn, skillsDict):
    agent_id = skillsDict['sourceId']
    new_status = skillsDict['event']['event']['params']['newStatus']
    old_status = skillsDict['event']['event']['params']['oldStatus']
    eventTime = skillsDict['event']['eventTime']
    eventTime_short = eventTime.split(".")[0]
    eventTime_dt = datetime.strptime(eventTime_short, "%Y-%m-%dT%H:%M:%S")
    last_updated = eventTime_dt.strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Changing disposition status for agent {agent_id} from {old_status} to {new_status} at timestamp {last_updated}")

    # Update Agent Table if newStatus = Absent
    if new_status == "absent":
        logger.info(f"Changing disposition status for agent {agent_id} to ABSENT")
        update_is_absent(conn, agent_id, "True")

    # Update Agent Table if oldStatus = Absent
    if old_status == "absent":
        update_is_absent(conn, agent_id, "False")

    # SQL UPDATE statement
    qry_update = f"""
    UPDATE {DB.disposition_status()}
    SET status = ?,
        last_updated = ?
    WHERE agent_id = ?
    """
    val = (new_status, last_updated, agent_id)

    # Executing the MERGE statement
    try:
        c = conn.cursor()
        c.execute(qry_update, val)
        conn.commit()
    except Exception as e:
        logger.exception(f"Error in changing disposition status for agent_id={agent_id}. Error message: {e}")
        conn.rollback()


def rmp_parsing(message_body, conn): 
    # Parse the message body as JSON
    skillsDict = json.loads(message_body)
    eventType = skillsDict['event']['eventType']

    if eventType == 'Change':
        # Call the function change that will update the db
        event_change(conn, skillsDict)            

# In order to test if the rmp_parsing() function is working as expected 
# uncomment the argument passed to that function below and test with 
# different values for old status and new status and check if it changes 
# accordingly in the uat_disposition_status table in the database.

if __name__ == "__main__":
    rmp_parsing(
    #     json.dumps({
    #         "sourceId":"eq42183",
    #         "dataDomain":"agent",
    #         "event":{
    #             "@type":"Event",
    #             "eventTime":"2024-09-04T13:00:00.927071264Z",
    #             "eventType":"Change",
    #             "correlationId":"generated-120af293-a0a1-483a-917d-1885ace3cbea",
    #             "domain":"agentDispositionCode",
    #             "title":"Change disposition status code",
    #             "description":"Test User has changed disposition status of eq42183 from logout to available",
    #             "relatedParty":[
    #                 {
    #                     "@type":"BellRelatedPartyRef",
    #                     "id":"eq42183",
    #                     "href":"$.relatedParty[?(@.id=='eq42183')]",
    #                     "name":"Rohan Surve",
    #                     "role":"Originator",
    #                     "@baseType":"RelatedPartyRef",
    #                     "@type":"BellRelatedPartyRef",
    #                     "@referredType":"Individual",
    #                     "externalId":"T00006",
    #                     "emailAddress":"rohan.surve@bell.ca"
    #                 }
    #             ],
    #             "event":{
    #                 "@type":"ActionParamsEventPayload",
    #                 "actionKey":"changeDispositionStatus",
    #                 "params":{
    #                     "agent":"Rohan Surve",
    #                     "newStatus":"logout",
    #                     "oldStatus":"available",
    #                     "tenant":"BBM"
    #                 }
    #             }
    #         }
    #     })
    )