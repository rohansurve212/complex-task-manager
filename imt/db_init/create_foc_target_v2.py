import sys
sys.path.append('../..')
from logging import Logger
import sqlite3
import teradatasql
import pandas as pd
from os.path import join
from dotenv import load_dotenv, find_dotenv
import os
import pyodbc
from shared.db import DB
from shared.all_envs import ENVIRONMENT, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS
import numpy as np

load_dotenv()  # Load variables from .env file
dotenv_path = join(find_dotenv())
load_dotenv(dotenv_path)
pd.set_option('display.max_columns', None)

print("ENV IS -------->", ENVIRONMENT)

df1 = pd.read_csv("ttpu_targets_20240528.csv")
print(df1.head(), df1.columns)
df=df1.replace(np.nan,'', regex=True)
print(f"LENGTH BEFORE {len(df)}")
print(df.head(), df.columns)
# Identify and remove duplicates
duplicates = df[df.duplicated(subset=['request_source', 'product', 'service_region', 'request_type', 'time_to_pickup_target_days'], keep=False)]
print(f"THE DUPLICATES ARE : {duplicates.shape[0]}")

# Remove the duplicate rows from the original DataFrame, keeping the last occurrence
df = df.drop_duplicates(subset=['request_source', 'product', 'service_region', 'request_type', 'time_to_pickup_target_days'], keep='last')

# Now, df contains only the unique rows, keeping the last occurrence
print(f"LENGTH NOW {len(df)}")

'''
This File reads a CSV And converts it into a DF and then loops over every row and either updates it or inserts the new values and injects it into
the SQL table dim_flow.
'''

print("values -------->", SQL_PASS, SQL_SERVER, SQL_USER, DATABASE)

mssql_con = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
cursor = mssql_con.cursor()
'''
Here we set up the connection
'''
chunk_size = 10000

for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i+chunk_size]
    new_df = chunk.drop('foc_id', axis=1)
    new_df.rename(columns={'time_to_pickup_target_days': 'foc_target'}, inplace=True)
    # print(new_df)
    print("NEW DF COLUMNS---------------------->",new_df.columns)
    qry = f"""
    MERGE INTO {DB.foc_targets()} AS target
    USING (VALUES (?, ?, ?, ?, ?)) AS source (request_source, product, service_region, request_type, foc_target)
    ON (target.request_source = source.request_source AND target.product = source.product AND target.service_region = source.service_region AND target.request_type = source.request_type)
    WHEN MATCHED THEN 
        UPDATE SET foc_target = source.foc_target
    WHEN NOT MATCHED THEN 
        INSERT (request_source, product, service_region, request_type, foc_target) 
        VALUES (source.request_source, source.product, source.service_region, source.request_type, source.foc_target);
    """
    cursor.fast_executemany = True
    cursor.executemany(qry, new_df.values.tolist())
    print(f'{chunk_size} rows inserted to the {DB.foc_targets()} table with location {i} to {i+chunk_size} <------------------------------')
    mssql_con.commit()
mssql_con.close()