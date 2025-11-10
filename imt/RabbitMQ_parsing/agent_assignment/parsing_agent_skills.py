import json
import argparse
import pyodbc
import traceback
import logging
import ldap
import certifi
import sys
from datetime import datetime
sys.path.append('..')  # Adding the parent directory to the Python path for imports

from shared.db import DB  # Importing database utility module
from shared.all_envs import PROD_LDAP_HOST, PROD_LDAP_USER, PROD_LDAP_PASS, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

# Setting up logging for tracking the script execution
logger = logging.getLogger("Agent skills log")

def extract_name(string):
    # Extract first and last name from a string formatted as "LastName, FirstName"
    list_name = string.split(',')
    first_name = list_name[1].split(' ')[1]
    last_name = list_name[0]
    full_name = first_name + ' ' + last_name
    return full_name

def get_fullName_and_permissions_from_ldap(emp_id):
    """
    Fetches the full name and permissions of an employee from an LDAP server.
    """
    try:
        # Configure LDAP connection and authentication
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "/etc/ssl/cacerts/custom/ca_bundle.pem")

        # Initialize LDAP connection
        l = ldap.initialize(PROD_LDAP_HOST)
        logger.info(f"LDAP connection initialized to {PROD_LDAP_HOST}.")

        # Set protocol version
        l.protocol_version = ldap.VERSION3
        logger.info("LDAP protocol version set to LDAP v3.")

        # Bind with credentials
        l.simple_bind_s(PROD_LDAP_USER, PROD_LDAP_PASS)
        logger.info("Successfully connected and bound to LDAP server.")

        # Search the LDAP directory for the employee details
        basedn = "ou=Business Units,dc=bell,dc=corp,dc=bce,dc=ca"
        searchFilter = "CN=" + emp_id
        searchScope = ldap.SCOPE_SUBTREE

        full_name = ""
        permissions = []
        ldap_result_id = l.search(basedn, searchScope, searchFilter)
        result_type, result_data = l.result(ldap_result_id, 0)

        if result_data == []:
            # Log and return empty if no matching employee is found
            logger.info(f"Agent not found in LDAP")
        else:
            # Parse permissions and extract full name from LDAP data
            memberOf = [result_data[0][1]['memberOf'][i].decode("utf-8").split('CN=')[1].split(',')[0] for i in range(len(result_data[0][1]['memberOf']))]
            OC_perms = [memberOf[i] for i in range(len(memberOf)) if 'OC-SmartPath-' in memberOf[i]]
            full_name = extract_name(result_data[0][1]['displayName'][0].decode("utf-8"))
            if len(OC_perms) == 0:
                logger.info(f" No permissions found for the agent")
            else:
                permissions = []
                for i in range(len(OC_perms)):
                    permissions.append(str(OC_perms[i]))
                logger.info(f" Found permissions for the agent")
            return full_name, permissions
        
    # Handle specific LDAP errors
    except ldap.INVALID_CREDENTIALS:
        logger.error("LDAP username or password is incorrect.")
        sys.exit(1)  # Exit the script if credentials are invalid
    except ldap.SERVER_DOWN:
        logger.error("LDAP server is not responding.")
        sys.exit(1)  # Exit the script if server is down
    except ldap.LDAPError as e:
        # General LDAP error handling with traceback logging
        logger.info(f"There is another error")
        error_message = traceback.format_exc()
        logger.exception(f"ERROR - {error_message}")
        if type(e.message) == dict and e.message.has_key('desc'):
            logger.error(e.message['desc'])
        else:
            logger.error(e)
        sys.exit(1)  # Exit for any other LDAP-related errors
    except Exception as e:
        # Generic exception handling
        error_message = traceback.format_exc()
        logger.exception(f"ERROR - {error_message}")
        logger.error(e)

def insert_into(conn, qry, values):
    """
    Inserts a record into the database and commits the transaction.
    """
    try:
        c = conn.cursor()
        c.execute(qry, values)
        conn.commit()
        logger.info(f"Successfully inserted record for {values}")
    except Exception as e:
        # Rollback in case of any error during the insertion
        logger.error(f"Error inserting record for {values}. Error message: {e}")
        conn.rollback()

def delete_record(conn, qry_del, val):
    """
    Deletes a record from the database based on the query and values provided.
    """
    try:
        c = conn.cursor()
        c.execute(qry_del, val)
        conn.commit()
        logger.info(f"Successfully deleted record for {val}")
    except Exception as e:
        # Rollback in case of any error during deletion
        logger.error(f"Error deleting record for {val}. Error message: {e}")
        conn.rollback()

def extract_skills_data(skillsDict, value_type='newValue'):
    """
    Extracts data from the skillsDict based on the provided value type ('newValue' or 'oldValue').
    """
    source_id = skillsDict.get("sourceId")
    skill_data = skillsDict['event']['event'].get(value_type, {})
    eventTime = skillsDict['event']['eventTime']
    eventTime_short = eventTime.split(".")[0]
    eventTime_dt = datetime.strptime(eventTime_short, "%Y-%m-%dT%H:%M:%S")
    last_updated = eventTime_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    skill_id = skill_data.get('queueId')
    agent_id = skill_data.get('userId')
    agent_pein = skill_data.get('individualId')
    skill_priority = skill_data.get('priority')

    return source_id, skill_id, agent_id, agent_pein, skill_priority, last_updated

def event_create(conn, skillsDict):
    """This function is called when an agent is assigned a new routing filter"""

    source_id, assigned_skill_id, agent_id, agent_pein, skill_priority, last_updated = extract_skills_data(skillsDict, 'newValue')

    logger.info(f"Verifying if the agent already exists in {DB.agent()} before assignment creation: SourceId={source_id}")
    select_agent_query = f"""
    SELECT agent_id 
    FROM {DB.agent()} 
    WHERE agent_id=?;
    """
    val = (agent_id)

    try:
        c = conn.cursor()
        c.execute(select_agent_query, val)
        agent_data = c.fetchall()

        if len(agent_data) != 0:
            # If the agent already exists in the agent table
            logger.info(f"Agent {agent_id} with pein {agent_pein} already exists in {DB.agent()}: SourceId={source_id}")
        else:
            # If the agent does not exist in the agent table - get agent full_name and permissions from LDAP
            agent_fullName, agent_permissions = get_fullName_and_permissions_from_ldap(agent_id)

            # 1 - ADD THE AGENT TO AGENT TABLE
            insert_query = f"INSERT INTO {DB.agent()} (agent_id, pein, full_name, is_absent) VALUES (?,?,?,?)"
            val = (agent_id, agent_pein, agent_fullName, "False")
            insert_into(conn, insert_query, val)

            # 2 - ADD THE AGENT TO DISPOSITION_STATUS TABLE
            insert_query = f"INSERT INTO {DB.disposition_status()} (agent_id, status, last_updated) VALUES (?,?,?)"
            val = (agent_id, "logout", last_updated)
            insert_into(conn, insert_query, val)

            # 3 - ADD THE AGENT TO PERMISSIONS_AGENT TABLE
            try:
                if len(agent_permissions) == 0:
                    c.execute(f"INSERT INTO {DB.permission_agent()} (agent_id, permission) VALUES (?,?);",(agent_id, "''"))
                    conn.commit()
                    logger.info(f"Permissions successfully updated for agent {agent_id}") 
                else:
                    for perm in agent_permissions: 
                        c.execute(f"INSERT INTO {DB.permission_agent()} (agent_id, permission) VALUES (?,?);",(agent_id, perm))
                    conn.commit()
                    logger.info(f"Permissions successfully updated for agent {agent_id}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Permissions NOT successfully updated for agent {agent_id}. Error message: {e}")
                
        # Create an entry for that agent with the routing filter and priority in skill_agent_priority table
        logger.info(f"Verifying if the skillset assignment already exists in {DB.skill_agent_priority()} before assignment creation: SourceId={source_id}")
        select_agent_skill_query = f"""
        SELECT agent_id 
        FROM {DB.skill_agent_priority()} 
        WHERE agent_id=? and skill_id=? and skill_priority=?;
        """
        val = (agent_id, assigned_skill_id, skill_priority)

        try:
            c = conn.cursor()
            c.execute(select_agent_skill_query, val)
            agent_skill_priority_data = c.fetchall()
            if len(agent_skill_priority_data) != 0:
                logger.info(f"Agent {agent_id} with skill id {assigned_skill_id} and skill priority {str(skill_priority)} already exists in {DB.skill_agent_priority()}: SourceId={source_id}")
            else:
                logger.info(f"Upserting record, sourceId={source_id}")
                merge_query = f"""
                MERGE INTO {DB.skill_agent_priority()} AS target
                USING (VALUES (?, ?, ?)) AS source (agent_id, skill_id, skill_priority)
                ON target.agent_id = source.agent_id AND target.skill_id = source.skill_id
                WHEN MATCHED THEN 
                    UPDATE SET skill_priority = source.skill_priority
                WHEN NOT MATCHED THEN
                    INSERT (agent_id, skill_id, skill_priority)
                    VALUES (source.agent_id, source.skill_id, source.skill_priority);
                """
                val = (agent_id, assigned_skill_id, skill_priority)
                c.execute(merge_query, val)
                conn.commit()
        except Exception as e:
            logger.exception(f"Error in adding routing filter id {assigned_skill_id} for agent {agent_id}. Error message: {e}")
            conn.rollback()

    except Exception as e:
        logger.exception(f"Error in adding agent {agent_id}. Error message: {e}")
        conn.rollback()

def event_change(conn, skillsDict):

    #Based on some previous examples the only field that is changing it is the priority. Hoever, to avoid future complications in future releases, then we collect both 
    # old values and new values. We ommit the old values from the table and replace it by the new values in the table skills_agent_priority
    
    source_id_old, skill_id_old, agent_id_old, _, skill_priority_old, last_updated_old = extract_skills_data(skillsDict, 'oldValue')
    source_id_new, skill_id_new, agent_id_new, _, skill_priority_new, last_updated_new = extract_skills_data(skillsDict, 'newValue')

    logger.info(f"Verifying if the record already exists in {DB.skill_agent_priority()} before assignment change: SourceId={source_id_old}")
    select_query = f"""
    SELECT agent_id 
    FROM {DB.skill_agent_priority()} 
    WHERE agent_id=? and skill_id=? and skill_priority=?;
    """
    val = (agent_id_old, skill_id_old, skill_priority_old)

    try:
        c = conn.cursor()
        c.execute(select_query, val)
        data = c.fetchall()
        if len(data) == 0:
            logger.error(f"The record does not exist, so create a new entry for this agent. SourceId={source_id_old}")
            event_create(conn, skillsDict)
        else:
            logger.info(f"Updating record, sourceId={source_id_old}")
            update_query = f"""
            UPDATE {DB.skill_agent_priority()}
            SET agent_id = ?, skill_id = ?, skill_priority = ?
            WHERE agent_id = ? AND skill_id = ? AND skill_priority = ?;
            """
            val = (agent_id_new, skill_id_new, skill_priority_new, agent_id_old, skill_id_old, skill_priority_old)
            c.execute(update_query, val)
            conn.commit()
            logger.info(f"Successfully updated priority for routing filter id {skill_id_new} for agent {agent_id_new}")
    except Exception as e:
        logger.exception(f"Error in updating priority for routing filter id {skill_id_new} for agent {agent_id_new}. Error message: {e}")
        conn.rollback()

def event_delete(conn,skillsDict):
    '''
    The delete will mainly be related to the skillset assignment and not the agent. 

    '''
    source_id, skill_id, agent_id, _, skill_priority, last_updated = extract_skills_data(skillsDict, 'oldValue')
    
    logger.info(f"Verifying if the record already exists in {DB.skill_agent_priority()} before assignment delete: SourceId={source_id}")
    select_query = f"""
    SELECT agent_id 
    FROM {DB.skill_agent_priority()} 
    WHERE agent_id=? and skill_id=? and skill_priority=?;
    """
    val = (agent_id, skill_id, skill_priority)

    try:
        c = conn.cursor()
        c.execute(select_query, val)
        data = c.fetchall()
        if len(data) == 0:
            logger.error(f"The record does not exist, a delete cannot be made. SourceId={source_id}")
            return
        else:
            logger.info(f"Deleting record, SourceId={source_id}")
            qry_del = f"DELETE from {DB.skill_agent_priority()} where agent_id=? and skill_id=? and skill_priority=?"
            val = (agent_id, skill_id, skill_priority)
            delete_record(conn, qry_del, val)
    except Exception as e:
        logger.exception(f"Error in deleting priority for routing filter id {skill_id} for agent {agent_id}. Error message: {e}")
        conn.rollback()

def rmp_parsing(message_body, conn):
    # Parse the message body as JSON
    skillsDict = json.loads(message_body)
    source_id = skillsDict["sourceId"]
    eventType = skillsDict['event']['eventType']

    #print(eventType)
    logger.info(f"Starting event for sourceId {source_id}... The eventType is {eventType}.")
    if eventType == 'Create':
        event_create(conn, skillsDict)
    if eventType == 'Change':
        event_change(conn, skillsDict)
    if eventType == 'Delete':
        event_delete(conn, skillsDict)

# In order to test if the rmp_parsing() function is working as expected 
# uncomment the argument passed to that function below and test with 
# different values for old status and new status and check if it changes 
# accordingly in the uat_disposition_status table in the database.           

if __name__ == "__main__": 
    rmp_parsing(
        # json.dumps(
        #     {
        #         "sourceId":"6499d2a81764ed12edb7f31b",
        #         "dataDomain":"queue",
        #         "event":{
        #             "@type":"Event",
        #             "eventTime":"2023-11-28T11:46:33.208553704Z",
        #             "eventType":"Change",
        #             "correlationId":"67e04d3d-1b5c-49ce-8a82-4e69a3f7e170",
        #             "domain":"queueAssignment",
        #             "title":"Queue assignment created/updated/deleted",
        #             "source":{
        #                 "@type":"EntityRef",
        #                 "id":"6499d2a81764ed12edb7f31b",
        #                 "href":"/queue/6499d2a81764ed12edb7f31b",
        #                 "@referredType":"QueueEntity"
        #             },
        #             "reportingSystem":{
        #                 "@type":"EntityRef",
        #                 "id":"SmartPath",
        #                 "href":"/smartpath"
        #             },
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
        #                     "externalId":"6077312",
        #                     "emailAddress":"rohan.surve@bell.ca"
        #                 }
        #             ],
        #             "event":{
        #                 "@type":"ChangeEventPayload",
        #                 "oldValue":{
        #                     "id":"61fbf693df5c6300015d508e",
        #                     "individualId":"451758",
        #                     "userId":"eq42183",
        #                     "queueId":"6499d2a81764ed12edb7f31b",
        #                     "priority":1,
        #                     "createdDate":"2022-02-03T15:36:51.805648107Z",
        #                     "createdBy":"steve.audy",
        #                     "lastModifiedDate":"2022-02-03T15:36:51.805648107Z",
        #                     "lastModifiedBy":"eq42183"
        #                 },
        #                 "newValue":{
        #                     "id":"61fbf693df5c6300015d508e",
        #                     "individualId":"451758",
        #                     "userId":"eq42183",
        #                     "queueId":"6499d2a81764ed12edb7f31b",
        #                     "priority":1099,
        #                     "lastModifiedDate":"2023-11-28T11:46:33.208553704Z",
        #                     "lastModifiedBy":"eq42183"
        #                 }
        #             }
        #         }
        #     }
        # ),
        # pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    )