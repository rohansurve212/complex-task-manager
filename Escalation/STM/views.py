# Import necessary modules from Django
from django.shortcuts import render

# Import Django HTTP response and template loader
from django.http import HttpResponse
from django.template import loader
from STM.models import Escalation

# Import pandas, json, pyodbc, logging, and Django translation utilities
import pandas as pd
import json
import pyodbc
import logging
from django.utils.translation import gettext_lazy as _

# Set up logging for the escalation API
logger = logging.getLogger("Escalation API log")

# Import datetime and pendulum for time zone handling
from datetime import datetime
import pendulum

# Import environment settings from shared module
from shared.all_envs import ENVIRONMENT

# Set the backend URL based on the environment (QA/UAT or other)
if ENVIRONMENT.lower() == 'qa' or ENVIRONMENT.lower() == 'uat':
    BACK_URL = "http://dc6cgx:8002/admin/"
else:
    BACK_URL = "http://dc6cgv:8002/admin/"

# Import Django render and redirect functions
from django.shortcuts import render, redirect
from .models import *
from django.http import JsonResponse

# Function to convert datetime to local timezone (US/Eastern)
def to_local_tz(date_to_convert: datetime) -> datetime:
    # Check if date_to_convert is a valid datetime object
    if pd.isnull(date_to_convert):
        return None
    try:
        local_tz = pendulum.timezone("US/Eastern")  # Set the timezone to US Eastern
        # Ensure date_to_convert is a pendulum datetime instance
        if not isinstance(date_to_convert, pendulum.DateTime):
            date_to_convert = pendulum.instance(date_to_convert)
        # Convert the datetime to the local timezone
        converted_pendulum_date = date_to_convert.in_tz(local_tz)
        return converted_pendulum_date.strftime("%Y-%m-%d %H:%M:%S")  # Return the formatted datetime
    except Exception as e:
        print(f"Error converting date: {e}")
        return None  # Return None if error occurs

# View function for table1 page
def table1(request):
    # Query all escalation records and convert to DataFrame
    df = pd.DataFrame(list(Escalation.objects.all()
    .values('escalation_id','request_id','escalation_ticket_no','request_reason', 'priority', 'submission_dt','status', 'assigned_dt','submission_person_name'))) #,'note'

    if df.shape[0] != 0:  # Check if DataFrame is not empty
        # Convert submission and assigned dates to local timezone
        df['submission_dt'] = pd.to_datetime(df['submission_dt'], errors='coerce')
        df['submission_dt'] = df['submission_dt'].apply(to_local_tz)
        df['assigned_dt'] = pd.to_datetime(df['assigned_dt'], errors='coerce')
        df['assigned_dt'] = df['assigned_dt'].apply(to_local_tz)

    # parsing the DataFrame in json format.
    json_records = df.reset_index().to_json(orient ='records',date_format='iso')
    data = []
    data = json.loads(json_records)
    back_url=BACK_URL
    context = {'d': data,
               'back_url': back_url
               }
    return render(request, 'forescalation/table1.html',context)

def home(request):
    
    context = {
                }
    return render(request, 'forescalation/home.html',context)

# Function to return a JSON response
def footballclubs(request):
    # Query all escalation records and return as JSON
    result_list = list(Escalation.objects.all()\
                .values('escalation_id','request_id','escalation_ticket_no','request_reason', 'priority', 'submission_dt','status', 'assigned_dt','submission_person_name'))

    print('result_list',result_list)
    return JsonResponse(result_list, safe=False)

# Function to export escalation records to CSV
import csv
def export_csv(request):
    # Get all escalation records
    employees = Escalation.objects.all()
    
    # Set up HTTP response for CSV download
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')  
    response['Content-Disposition'] = 'attachment; filename="file.csv"' 
    
    # Format submission and assigned dates for CSV export
    for employee in employees:
        employee.submission_dt = pd.to_datetime(employee.submission_dt).strftime('%d/%m/%Y %H:%M:%S') if pd.notna(employee.submission_dt) else ''
        employee.assigned_dt = pd.to_datetime(employee.assigned_dt).strftime('%d/%m/%Y %H:%M:%S') if pd.notna(employee.assigned_dt) else ''
    
    # Write the CSV header and data rows
    writer = csv.writer(response)
    writer.writerow(['escalation_id', 'request_id', 'escalation_ticket_no', 'request_reason', 'priority', 'submission_dt', 'status', 'assigned_dt', 'submission_person_name'])
    
    # Write each employee record to the CSV
    for employee in employees:
        writer.writerow([employee.escalation_id, employee.request_id, employee.escalation_ticket_no, employee.request_reason, employee.priority,
                         employee.submission_dt, employee.status, employee.assigned_dt, employee.submission_person_name])
    
    return response  # Return the CSV file as the response