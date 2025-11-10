#!/usr/local/bin/python

import traceback
import ldap
# LDAP requires installing the wheel from http://www.lfd.uci.edu/~gohlke/pythonlibs/#python-ldap
# Choose the file which corresponds to your python version
import certifi
import pyodbc 
import sys 
sys.path.append('..')
import pandas as pd
from os.path import join
from dotenv import load_dotenv, find_dotenv
from shared.db import DB
from shared.all_envs import PROD_LDAP_HOST, PROD_LDAP_USER, PROD_LDAP_PASS, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("LDAP log")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler('/var/log/ldap.log',when="midnight",interval=1,backupCount=7)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def extract_name(string):
    """
    Extracts the full name (first and last name) from a string formatted as 'last_name, first_name'.
    """
    list_name = string.split(',')
    first_name = list_name[1].split(' ')[1]
    last_name = list_name[0]
    full_name = first_name + ' ' + last_name
    return full_name

def get_permissions(emp_nt_id):
    """
    Retrieves permissions for a list of employee NT IDs by querying the LDAP server.
    Returns a dictionary with employee details and permissions.
    """
    emp_dict = {}

    for emp_id in emp_nt_id:
        logger.info(f"emp_id {emp_id} successfully found")  
        basedn = "ou=Business Units,dc=bell,dc=corp,dc=bce,dc=ca"
        searchFilter = "CN=" + emp_id
        searchScope = ldap.SCOPE_SUBTREE
        try:
            ldap_result_id = l.search(basedn, searchScope, searchFilter)
            result_type, result_data = l.result(ldap_result_id, 0)
            if result_data == []:
                emp_dict[emp_id] = {"agent_id": emp_id, "full_name": full_name, "permissions":[]}
                logger.info(f" Agent without permissions : {emp_dict[emp_id]}")
            else:
                memberOf = [result_data[0][1]['memberOf'][i].decode("utf-8").split('CN=')[1].split(',')[0] for i in range(len(result_data[0][1]['memberOf']))]
                OC_perms = [memberOf[i] for i in range(len(memberOf)) if 'OC-SmartPath-' in memberOf[i]]
                full_name = extract_name(result_data[0][1]['displayName'][0].decode("utf-8"))
                if len(OC_perms) == 0:
                    emp_dict[emp_id] = {"agent_id": emp_id, "full_name": full_name, "permissions":[]}
                    logger.info(f" Agent without permissions 2 : {emp_dict[emp_id]}")
                else:
                    permissions = []
                    for i in range(len(OC_perms)):
                        permissions.append(str(OC_perms[i]))
                    emp_dict[emp_id] = {"agent_id": emp_id, "full_name": full_name, "permissions": permissions}
                    logger.info(f" Agent with permissions : {emp_dict[emp_id]}")
        except Exception as e:
            error_message = traceback.format_exc()
            logger.exception(f"ERROR - {error_message}")
            logger.error(e)
    
    return emp_dict

def insert_into(conn, qry, values):
    """
    Executes an SQL query to insert or update records in the database.
    Logs success or failure of the operation.
    """
    c = conn.cursor()
    try:
        c.execute(qry, values)
        conn.commit()
        #print("record updated successfully")
        logger.info(f"Record with query={qry} and values={values} updated successfully")
    except Exception as e:
        #print("error in operation")
        logger.error(f"Record with query={qry} and values={values} did NOT update. Error message: {e}")
        conn.rollback() 

def delete_update_perm(conn,agent_id, all_permission):
    """
    Deletes existing permissions for an agent and inserts updated permissions.
    Handles cases with no permissions separately.
    """
    c = conn.cursor()
    if len(all_permission) == 0:
        logger.info(f"No permission found for agent {agent_id}.")
        try: 
            c.execute(f"DELETE FROM {DB.permission_agent()} WHERE agent_id=?;", (agent_id,))
            c.execute(f"INSERT INTO {DB.permission_agent()} (agent_id, permission) VALUES (?,?);",(agent_id, "''"))
            conn.commit()
            logger.info(f"Permissions successfully updated for agent {agent_id}")
        except Exception as e: 
            logger.error(f"Permissions NOT successfully updated for agent {agent_id}. Error message: {e}")
    else: 
        logger.info(f"Found permissions for agent {agent_id}.")
        try: 
            c.execute(f"DELETE FROM {DB.permission_agent()} WHERE agent_id=?;", (agent_id,))
            for perm in all_permission: 
                qry_ins = f"INSERT INTO {DB.permission_agent()} (agent_id, permission) VALUES (?,?);"
                val = (agent_id,perm)
                c.execute(qry_ins, val)
            conn.commit()
            logger.info(f"Permissions successfully updated for agent {agent_id}")
        except Exception as e:
            logger.error(f"Permissions NOT successfully updated for agent {agent_id}. Error message: {e}")

def update_full_name(conn, agent_id, full_name):

    c = conn.cursor()
    # First checking if the agent exists in our tables 
    logger.info(f"Updating the full name {full_name} for agent {agent_id} in {DB.agent()}. Checking if agent exists.")
    c.execute(f"SELECT agent_id FROM {DB.agent()} WHERE agent_id=?;", (agent_id,))
    data = c.fetchall()
    if len(data) == 0: 
        logger.info(f"Agent {agent_id} does not exists in {DB.agent()}. Adding them.")
        qry_ins = f"INSERT INTO {DB.agent()} (agent_id, pein, full_name) VALUES (?, ?, ?)"
        val = (agent_id, None, full_name)
        insert_into(conn,qry_ins, val) 
    else: 
        logger.info(f"Agent {agent_id} exists in {DB.agent()}. Checking if we have the full name.")
        c.execute(f"SELECT agent_id FROM {DB.agent()} WHERE agent_id=? AND full_name IS NOT NULL;", (agent_id,))
        data = c.fetchall()
        if len(data) == 0: 
            logger.info(f"Full name for agent {agent_id} does not exist. Adding it.")
            qry_update = f"UPDATE {DB.agent()} SET full_name=? WHERE agent_id=?;"
            val = (full_name, agent_id)
            insert_into(conn,qry_update, val)
        else: 
            logger.info(f"Full name {full_name} already in table agent.")

def get_emp_nt_id (con):

    sql=f"SELECT * FROM {DB.agent()}"  
    df = pd.read_sql(sql,con)

    if len(df) == 0:
        logger.info(f"Not record found in DB.agent()")
    else: 
        logger.info(f"found record in DB.agent()")
        try: 
            emp_nt_id = df['agent_id']
            logger.info(f"successfully get emp_nt_id")
        except Exception as e:
            logger.error(f"NOT successfully get emp_nt_id. Error message: {e}")

    return emp_nt_id

if __name__ == "__main__":

    try:
        logger.info(f"Connecting to LDAP server {PROD_LDAP_HOST}...")

        # SSL/TLS setup
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "/etc/ssl/cacerts/custom/ca_bundle.pem")
        logger.info(f"Using cert file: {certifi.where()}")

        # For testing, optionally disable certificate validation (not recommended for production)
        # ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        # logger.info("Certificate validation disabled for testing.")

        # Initialize LDAP connection
        l = ldap.initialize(PROD_LDAP_HOST)
        logger.info(f"LDAP connection initialized to {PROD_LDAP_HOST}.")

        # Set protocol version
        l.protocol_version = ldap.VERSION3
        logger.info("LDAP protocol version set to LDAP v3.")

        # Bind with credentials
        l.simple_bind_s(PROD_LDAP_USER, PROD_LDAP_PASS)
        logger.info("Successfully connected and bound to LDAP server.")

    except ldap.INVALID_CREDENTIALS:
        logger.error("LDAP username or password is incorrect.")
        sys.exit(1) # Exit the script if credentials are invalid
    except ldap.SERVER_DOWN:
        logger.error("LDAP server is not responding.")
        sys.exit(1)  # Exit the script if server is down
    except ldap.LDAPError as e:
        logger.info(f"There is another error")
        error_message = traceback.format_exc()
        logger.exception(f"ERROR - {error_message}")
        if type(e.message) == dict and e.message.has_key('desc'):
            logger.error(e.message['desc'])
        else:
            logger.error(e)
        sys.exit(1)  # Exit for any other LDAP-related errors

    conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes'
    )
    logger.info(f"Successfully connected to SQL Server")
    emp_nt_id=get_emp_nt_id (conn)
    emp_permissions = get_permissions(emp_nt_id)
            
    logger.info("Started reading the permissions dictionnary")
    
    for key, emp in emp_permissions.items():
        agent_id = emp['agent_id']
        full_name = emp['full_name']
        all_permission = emp['permissions']
        logger.info(f"Found agent id is {agent_id} with name {full_name} whose Permissions are {all_permission}")
        # Updating the database table 1- check if the combination exist in the table parse each value of the permission
        delete_update_perm(conn, agent_id, all_permission)

        # Updating the agent table to fillup up the full name column by agent ID.
        update_full_name(conn, agent_id, full_name)
    try:
        l.unbind_s()
        logger.info("Successfully disconnected and unbound from LDAP server.")
    except ldap.LDAPError as e:
        logger.error(f"Error unbinding from LDAP server: {e}") 
