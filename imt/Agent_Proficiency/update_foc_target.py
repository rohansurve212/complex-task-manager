from logging import Logger
import sqlite3
import teradatasql
import pandas as pd
from os.path import join
from dotenv import load_dotenv, find_dotenv
import os
import pyodbc
from shared.db import DB
from shared.all_envs import SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

pd.set_option('display.max_columns', None)
conn = sqlite3.connect('bbm_stm_v1.db')

df = pd.read_csv("time_to_pickup_targets.csv")
'''
This File reads a CSV And converts it into a DF and then loops over every row and either updates it or inserts the new values and injects it into
the SQL table dim_flow.
'''

mssql_con = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
cursor = mssql_con.cursor()
'''
Here we set up the connection
'''
for _, row in df.iterrows():
    # print(row)
    flow_id = row.flow_id
    customer_support_model = row.customer_support_model
    request_type = row.request_type
    foc_target = row.foc_target
    print("FOC_TARGET-------->", foc_target)
    qry_check = f"SELECT * FROM {DB.dim_flow()} WHERE flow_id='{flow_id}'"
    cursor.execute(qry_check)
    data = cursor.fetchall()
    print("DATA LENGTH------------->", len(data))
    '''
    Here we are checking if the data already exists, if it does we will update the data, if not then we will insert new data and inject into the sql table
    '''
    if len(data) > 0:
        print("value did exist")
        qry = "UPDATE {} SET customer_support_model='{}',request_type='{}',foc_target={} WHERE flow_id = {}".format(DB.dim_flow(), customer_support_model, request_type, foc_target, flow_id)
        print("QUERYY----------->", qry)
        val = (flow_id, customer_support_model, request_type, foc_target)
        cursor.execute(qry)
        # Logger.info(f"Record with query={qry} and values={val} updated successfully")
        print(f"updated {DB.dim_flow()} successfully")
    else:
        qry = f"INSERT INTO {DB.dim_flow()} (flow_id,customer_support_model,request_type,foc_target) values(?,?,?,?)"
        print("QUERYY----------->", qry)
        val = (flow_id, customer_support_model, request_type, foc_target)
        cursor.execute(qry, val)
        # Logger.info(f"Record with query={qry} and values={val} updated successfully")
        print(f"inserted {DB.dim_flow()} successfully")
    mssql_con.commit()
mssql_con.close()