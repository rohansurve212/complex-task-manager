import teradatasql
import pandas as pd
import os 
from os.path import join
from dotenv import load_dotenv, find_dotenv
from business_duration import businessDuration
import holidays
from datetime import time
import pyodbc
from shared.db import DB
from shared.all_envs import TD_HOST, TD_USER, TD_PASS, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("Agent proficiency log")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler('/var/log/agent_proficiency.log',when="midnight",interval=1,backupCount=7)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

dotenv_path = join(find_dotenv())
load_dotenv(dotenv_path)
pd.set_option('display.max_columns', None)

## To get the dataframe based on needs
def get_df(td_host,td_user,td_pass,sql):
    print("STARTING THE FUNCTION --------------------------------------------------------")
    con = teradatasql.connect(host = td_host, user = td_user, password = td_pass)
    print("CONNECTED TO TERADATA --------------------------------------------------------")
    df = pd.read_sql(sql, con)
    logger.info(f"Get dataframe_df")
    print("GOT THE DF USING READ_SQL -------------------------------------------")
    return df

## To process the dataframe to get the proficiency table
def get_proficiency(df):
    starttime = time(8, 0, 0)
    endtime = time(17, 0, 0)
    unit = "min"
    holidaylist = holidays.CA(years=[2021, 2022])
    df["proficiency"] = [
        businessDuration(
            df.smtpth_req_start_dt[i],
            df.smtpth_req_comp_dt[i],
            starttime=starttime,
            endtime=endtime,
            holidaylist=holidaylist,
            unit=unit,
        )
        if pd.isna(df.smtpth_req_foc_actl_dt[i])
        else businessDuration(
            df.smtpth_req_start_dt[i],
            df.smtpth_req_foc_actl_dt[i],
            starttime=starttime,
            endtime=endtime,
            holidaylist=holidaylist,
            unit=unit,
        )
        for i in range(len(df))
    ]
    df = df[~df.proficiency.isnull()].reset_index(drop=True)
    temp_flow = (
        df[["flow_id", "proficiency"]].groupby(["flow_id"], as_index=False).mean()
    )
    flow = dict(zip(temp_flow.flow_id, temp_flow.proficiency))
    temp_proficiency = (
        df[["agent_id", "flow_id", "proficiency"]]
        .groupby(["agent_id", "flow_id"], as_index=False)
        .agg({"proficiency": ["mean", "count"]})
    )
    temp_proficiency.columns = temp_proficiency.columns.map("_".join)
    temp_proficiency["flow_average"] = temp_proficiency["flow_id_"].map(flow)
    temp_proficiency["rel_proficiency"] = (
        temp_proficiency["flow_average"] / temp_proficiency["proficiency_mean"]
    )
    temp_proficiency["rel_proficiency"] = [
        temp_proficiency["rel_proficiency"][i]
        if temp_proficiency["rel_proficiency"][i] <= 100
        else 100
        for i in range(len(temp_proficiency["rel_proficiency"]))
    ]
    proficiency = temp_proficiency.rename(
        columns={"flow_id_": "flow_id", "agent_id_": "agent_id"}
    )
    logger.info(f"Get dataframe_proficiency")
    return proficiency

## To update dim table in SQL server studio with dim_flow dataframe
def To_execute_dim_flow(dim_flow,cursor,mssql_con):
    for _, row in dim_flow.iterrows():
        flow_id = row.flow_id
        requestSource = row.requestSource
        customerSupportModel = row.customerSupportModel
        requestType = row.requestType
        focTarget = row.focTarget    

        logger.info(f"Found status={flow_id} Found focTarget={focTarget} for agent {flow_id}")
        qry = f"INSERT INTO {DB.dim_flow()} (flow_id,request_source,customer_support_model,request_type,foc_target) VALUES (?,?,?,?,?)"
        val = (flow_id, requestSource, customerSupportModel, requestType, focTarget)
        cursor.execute(qry, val)

        logger.info(f"Record with query={qry} and values={val} inserted successfully")

        mssql_con.commit()

    return 

## To update proficiency table in SQL server studio with df_proficiency dataframe
def To_execute_proficiency (SQL_SERVER,DATABASE,SQL_USER,SQL_PASS,proficiency): 

    mssql_con = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    cursor = mssql_con.cursor()

    for _, row in proficiency.iterrows():
        agent_id = row.agent_id
        flow_id = row.flow_id
        proficiency_mean = row.proficiency_mean
        proficiency_count = row.proficiency_count
        flow_average = row.flow_average
        rel_proficiency = row.rel_proficiency

        #Check if agent exists in dbo.agent, otherwise add it
        qry_check = f"SELECT * FROM {DB.agent()} WHERE agent_id='{agent_id}'"
        cursor.execute(qry_check)
        logger.info(f"Found status={rel_proficiency} for agent {agent_id} and Record with query={qry_check} selected successfully")
        #mssql_con.commit()
        data = cursor.fetchall()
        if len(data) == 0:
            qry_add = f"INSERT INTO {DB.agent()} (agent_id) VALUES ('{agent_id}')"
            cursor.execute(qry_add)
            logger.info(f"Agent={agent_id} does not exist in {DB.agent()}. Creation...  Record with query={qry_add} Inserted successfully")
            mssql_con.commit()
        
        qry = f"INSERT INTO {DB.proficiency()} (agent_id,flow_id,proficiency_mean,proficiency_count,flow_average,rel_proficiency) VALUES (?,?,?,?,?,?)"
        val = (agent_id, flow_id, proficiency_mean, proficiency_count, flow_average, rel_proficiency)
        cursor.execute(qry, val)
        logger.info(f"Record with query={qry} and values={val} inserted successfully")
        mssql_con.commit()
    mssql_con.close()

    return 

##To delete the proficiency table in SQL server studio before updating
def To_delete_proficiency(cursor,mssql_con):
	qry=f"Delete FROM {DB.proficiency()}"
	cursor.execute(qry)
	logger.info(f"Record with query={qry} Deleted successfully")
	mssql_con.commit()
	return 

##To delete the dim table in SQL server studio before updating
def To_delete_dim_flow(cursor,mssql_con):
	qry=f"Delete FROM {DB.dim_flow()}"
	cursor.execute(qry)
	logger.info(f"Record with query={qry} deleted successfully")
	mssql_con.commit()
	return 
    

if __name__ == "__main__":     

    td_host = TD_HOST
    td_user = TD_USER
    td_pass = TD_PASS
    print(f"HOSTS ARE TD_HOST {td_host}, TD_USER {td_user}, TD_PASS {td_pass} ------------------------------->")
	
    sql	 = """ 
	SELECT agent_id, flow_id,smtpth_req_start_dt,smtpth_req_foc_actl_dt, smtpth_req_comp_dt FROM
	(SELECT smtpth_req_id, smtpth_req_asgnee_name,smtpth_req_create_dt,smtpth_req_nativestatus,smtpth_req_foc_actl_dt,
		CASE 
			WHEN smtpth_req_source = 'bcom' THEN 'bcom'
			ELSE 'other'
			END AS requestSource,
		CASE 
			WHEN smtpth_req_sprt_model = 'Non-Standard' THEN 'non-standard'
			ELSE 'other'
			END AS customerSupportModel,
		CASE 
			WHEN smtpth_req_action_cat LIKE '%nquiry%' THEN 'inquiry'
			WHEN smtpth_req_action_cat = 'disconnect' THEN 'disconnect'
			WHEN smtpth_req_action_cat IN ('move', 'add', 'change', 'new') THEN 'nmac'
			ELSE 'other'
			END AS requestType,
		CASE 
			WHEN smtpth_req_foc_sla_days IS NULL THEN 0
			ELSE smtpth_req_foc_sla_days
			END as focTarget,
		smtpth_req_start_dt,
		smtpth_req_comp_dt,
		smtpth_awaitcust_dur
		FROM GRP_JARVIS_ANALYSIS.fact_smtpth_request_v2) AS C1
		LEFT JOIN (
		SELECT ROW_NUMBER() OVER(ORDER BY requestSource, customerSupportModel, requestType, focTarget) AS flow_id, requestSource, customerSupportModel, requestType, focTarget
	FROM 
		(SELECT DISTINCT
		CASE 
			WHEN smtpth_req_source = 'bcom' THEN 'bcom'
			ELSE 'other'
			END AS requestSource,
		CASE 
			WHEN smtpth_req_sprt_model = 'Non-Standard' THEN 'non-standard'
			ELSE 'other'
			END AS customerSupportModel,
		CASE 
			WHEN smtpth_req_action_cat LIKE '%nquiry%' THEN 'inquiry'
			WHEN smtpth_req_action_cat = 'disconnect' THEN 'disconnect'
			WHEN smtpth_req_action_cat IN ('move', 'add', 'change', 'new') THEN 'nmac'
			ELSE 'other'
			END AS requestType,
		CASE 
			WHEN smtpth_req_foc_sla_days IS NULL THEN 0
			ELSE smtpth_req_foc_sla_days
			END as focTarget
		FROM GRP_JARVIS_ANALYSIS.fact_smtpth_request_v2
		WHERE smtpth_req_create_dt > DATE '2021-01-01') AS T1
		) AS C2
		ON C1.requestSource = C2.requestSource AND C1.customerSupportModel = C2.customerSupportModel AND C1.requestType = C2.requestType AND C1.focTarget = C2.focTarget
		LEFT JOIN (
		SELECT	DISTINCT emp_nt_id AS agent_id, emp_full_name
	FROM	GRP_JARVIS_ANALYSIS.dim_ldap_emp
	WHERE emp_end_date > DATE '2023-01-01') AS C3
	ON C1.smtpth_req_asgnee_name = C3.emp_full_name 
	WHERE smtpth_req_create_dt > DATE '2021-01-01'
	AND smtpth_req_nativestatus = 'completed'
	AND smtpth_req_comp_dt IS NOT NULL 
	AND smtpth_req_start_dt IS NOT NULL
	"""

    df=get_df(td_host,td_user,td_pass,sql)
    df_proficiency=get_proficiency(df)

    sql_dim_flow = """ 
	SELECT ROW_NUMBER() OVER(ORDER BY requestSource, customerSupportModel, requestType, focTarget) AS flow_id, requestSource, customerSupportModel, requestType, focTarget
	FROM (
	SELECT DISTINCT
		CASE 
			WHEN smtpth_req_source = 'bcom' THEN 'bcom'
			ELSE 'other'
			END AS requestSource,
		CASE 
			WHEN smtpth_req_sprt_model = 'Non-Standard' THEN 'non-standard'
			ELSE 'other'
			END AS customerSupportModel,
		CASE 
			WHEN smtpth_req_action_cat LIKE '%nquiry%' THEN 'inquiry'
			WHEN smtpth_req_action_cat = 'disconnect' THEN 'disconnect'
			WHEN smtpth_req_action_cat IN ('move', 'add', 'change', 'new') THEN 'nmac'
			ELSE 'other'
			END AS requestType,
		CASE 
			WHEN smtpth_req_foc_sla_days IS NULL THEN 0
			ELSE smtpth_req_foc_sla_days
			END as focTarget
		FROM GRP_JARVIS_ANALYSIS.fact_smtpth_request_v2
		WHERE smtpth_req_create_dt > DATE '2021-01-01') AS T1
	"""
    dim_flow=get_df(td_host,td_user,td_pass,sql_dim_flow)
	
    mssql_con = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    cursor = mssql_con.cursor()
	
    To_delete_proficiency(cursor,mssql_con)
    To_delete_dim_flow(cursor,mssql_con)
    To_execute_dim_flow(dim_flow,cursor,mssql_con)
    mssql_con.close()

    ## Separate this step because Proficiency table is a bit big and takes longer time. 
    To_execute_proficiency (SQL_SERVER,DATABASE,SQL_USER,SQL_PASS,df_proficiency)






