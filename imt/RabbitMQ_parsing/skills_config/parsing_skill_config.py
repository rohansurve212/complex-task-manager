import json
import argparse
import pyodbc
import logging

import sys
sys.path.append('..')

from shared.db import DB
from shared.all_envs import SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

logger = logging.getLogger("Skillset configuration log")

def insert_into(conn, query, values):
    try:
        c = conn.cursor()
        c.execute(query, values)
        conn.commit()
        logger.info(f"Successfully inserted record for {values}")
    except Exception as e:
        logger.error(f"Error inserting record for {values}. Error message: {e}")
        conn.rollback()

def delete_by_skill_id(conn, query, s_id):
    try:
        c = conn.cursor()
        c.execute(query, s_id)
        conn.commit()
        logger.info(f"Successfully deleted record for {s_id}")
    except Exception as e:
        logger.error(f"Error deleting record for {s_id}. Error message: {e}")
        conn.rollback()

def update_record(conn, query, values):
    try:
        c = conn.cursor()
        c.execute(query, values)
        conn.commit()
        logger.info(f"Successfully updated record for {values}")
    except Exception as e:
        logger.error(f"Error updating record for {values}. Erorr message: {e}")
        conn.rollback()

def event_create(conn, skillsDict):
    """This function inserts information related to a routing filter"""

    source_id = skillsDict["sourceId"]

    try: 
        skill_id = skillsDict['event']['event']['newValue']['id']
    except: 
        logger.error(f"Primary Key error, no skill id found for SourceId={source_id}")
        return 

    try: 
        skill_name = skillsDict['event']['event']['newValue']['name']
    except:  
        skill_name = None
        logger.error(f"No skill name found for creation with SourceId={source_id}")

    try:
        skill_dist = skillsDict['event']['event']['newValue']['distributionMode']
    except: 
        skill_dist = None
        logger.error(f"No skill distribution mode found for creation with SourceId={source_id}")

    try:
        skill_status = skillsDict['event']['event']['newValue']['queueStatus']
    except: 
        skill_status = None
        logger.error(f"No skill status found for creation with SourceId={source_id}")

    logger.info(f"Starting creation of routing filter for SourceId={source_id}")

    # 1 - First check if the skill_id already exists in skills_config table - if not add the skill_id to skills_config table
    logger.info(f"Verifying if the routing filter already exists in {DB.skill_config()} before configuration creation: SourceId={source_id}")
    select_skill_query = f"""
    SELECT skill_id 
    FROM {DB.skill_config()} 
    WHERE skill_id= ?;
    """
    val = (skill_id,)

    try:
        c = conn.cursor()  
        c.execute(select_skill_query, val)
        data = c.fetchall()
        if len(data) != 0:
            logger.info(f"Routing filter with id {skill_id} already exists in {DB.skill_config()}: SourceId={source_id}")
            return 
        else:
            # Insert the new routing filter in the skills_config table
            insert_query = f"INSERT INTO {DB.skill_config()} (skill_id, skill_name, skill_distribution, skill_status) VALUES (?,?,?,?)"
            values = (skill_id, skill_name, skill_dist, skill_status)
            insert_into(conn, insert_query, values)
        
    except Exception as e:
        logger.exception(f"Error in adding routing filter id {skill_id} to {DB.skill_config()}. Error message: {e}")
        conn.rollback()
        
def event_change(conn, skillsDict):
    """This functions updates information related to a routing filter"""

    source_id = skillsDict["sourceId"]
     
    try: 
        skill_id = skillsDict['event']['event']['newValue']['id']
        skill_id_old = skillsDict['event']['event']['oldValue']['id']
        if skill_id != skill_id_old:
            logger.error(f"Discrepancy in skill_id information between old and new value for sourceId={source_id}")
    except: 
        logger.error(f"Primary Key error, no skill id found (old or new) for SourceId={source_id}")
        return

    try:
        skill_name = skillsDict['event']['event']['newValue']['name']
    except:
        skill_name = None
        logger.error(f"No skill name found for creation with SourceId={source_id}")

    try: 
        skill_dist = skillsDict['event']['event']['newValue']['distributionMode']
    except: 
        skill_dist = None
        logger.error(f"No skill distribution mode found for creation with SourceId={source_id}")
    
    try: 
        skill_status = skillsDict['event']['event']['newValue']['queueStatus']
    except:
        skill_status = None
        logger.error(f"No skill status found for creation with SourceId={source_id}")

    logger.info(f"Starting update of routing filter for SourceId={source_id}") 

    skill_tag = None
    skill_action_category = None
    skill_request_source = None
    skill_control_desk = None
    skill_service_region = None
    skill_pref_language = None
    skill_support_model = None
    skill_orderit_service_name = None
    skill_golden_customer_id = None
    skill_market_segment = None 

    if 'searchDetails' in skillsDict['event']['event']['newValue'].keys():
        if 'filter' in skillsDict['event']['event']['newValue']['searchDetails']['filter'][0].keys():
            if skillsDict['event']['event']['newValue']['searchDetails']['filter'][0]['filter'][0]['@type'] == 'FilterGroup':
                for data in skillsDict['event']['event']['newValue']['searchDetails']['filter'][0]['filter']:
                    for filter_iter in data['filter']:
                        field = filter_iter['field']
                        value = filter_iter['value']
                        if field == "tag":
                            skill_tag = value
                        elif field == "orderItem.actionCategory":
                            skill_action_category = value
                        elif field == "characteristic.request-source":
                            skill_request_source = value
                        elif field == "characteristic.controlDesk":
                            skill_control_desk = value    
                        elif field == "characteristic.service-region":
                            skill_service_region = value
                        elif field == "characteristic.preferred-language":
                            skill_pref_language = value 
                        elif field == "characteristic.support-model":
                            skill_support_model = value                   
                        elif field == "relatedParty.goldenCustomer.id":
                            skill_golden_customer_id = value                    
                        elif field == "orderItem.service.name":
                            skill_orderit_service_name = value                    
                        elif field == "characteristic.marketSegment":
                            skill_market_segment = value
            if skillsDict['event']['event']['newValue']['searchDetails']['filter'][0]['filter'][0]['@type'] == 'AttributeFilter':
                for data in skillsDict['event']['event']['newValue']['searchDetails']['filter']:
                    for filter_iter in data['filter']:
                        field = filter_iter['field']
                        value = filter_iter['value']
                        if field == "tag":
                            skill_tag = value
                        elif field == "orderItem.actionCategory":
                            skill_action_category = value
                        elif field == "characteristic.request-source":
                            skill_request_source = value
                        elif field == "characteristic.controlDesk":
                            skill_control_desk = value    
                        elif field == "characteristic.service-region":
                            skill_service_region = value
                        elif field == "characteristic.preferred-language":
                            skill_pref_language = value 
                        elif field == "characteristic.support-model":
                            skill_support_model = value                   
                        elif field == "relatedParty.goldenCustomer.id":
                            skill_golden_customer_id = value                    
                        elif field == "orderItem.service.name":
                            skill_orderit_service_name = value                    
                        elif field == "characteristic.marketSegment":
                            skill_market_segment = value

    # 1 - Check if the skill_id already exists in skills_config table  
    logger.info(f"Verifying if the routing filter already exists in {DB.skill_config()} before updating: SourceId={source_id}")
    select_skill_query = f"""
    SELECT skill_id 
    FROM {DB.skill_config()} 
    WHERE skill_id= ?;
    """
    val = (skill_id,)

    try:
        c = conn.cursor()
        c.execute(select_skill_query, val)
        data = c.fetchall()
        if len(data) == 0:
            logger.error(f"Routing filter with id {skill_id} does not exist in {DB.skill_config()}, so create a new entry for this routing filter. SourceId={source_id}")
            event_create(conn, skillsDict) 
        else:
            # Update the routing filter in the skills_config table
            update_query = f"UPDATE {DB.skill_config()} SET skill_distribution=?, skill_name=?, skill_status=? WHERE skill_id = ?"
            values = (skill_dist, skill_name, skill_status, skill_id)
            update_record(conn, update_query, values)

            columns = [
                "c_desk", "g_customer", "m_segment", 
                "p_language", "r_source", "s_name", 
                "s_region", "s_model",
                "s_tag", "a_category"
            ]

            tables = [
                DB.skill_control_desk(), DB.skill_gold_customer(), DB.skill_market_segment(), 
                DB.skill_pref_languages(), DB.skill_request_source(), DB.skill_service_name(), 
                DB.skill_service_region(), DB.skill_support_model(),
                DB.skill_tag(), DB.skill_action_category()
            ]

            attributes = [
                skill_control_desk, skill_golden_customer_id, skill_market_segment,
                skill_pref_language, skill_request_source, skill_orderit_service_name,
                skill_service_region, skill_support_model,
                skill_tag, skill_action_category
            ]

            # Update the routing filter in the all the individual skill tables
            for column, table, attribute in zip(columns, tables, attributes):
                delete_query = f"DELETE from {table} where skill_id = ?"
                delete_by_skill_id(conn, delete_query, (skill_id,))
                if attribute != None:
                    for value in attribute:
                        insert_query = f"INSERT INTO {table} (skill_id, {column}) VALUES (?,?)"
                        insert_into(conn, insert_query, (skill_id, value))

        # Update the routing filter in the skill_attributes table 
        controlDesk = ';'.join(skill_control_desk) if skill_control_desk is not None else None
        goldenCustomer = ';'.join(skill_golden_customer_id) if skill_golden_customer_id is not None else None
        customerMarketSegment = ';'.join(skill_market_segment) if skill_market_segment is not None else None
        preferredlanguage = ';'.join(skill_pref_language) if skill_pref_language is not None else None
        requestSource = ';'.join(skill_request_source) if skill_request_source is not None else None
        product = ';'.join(skill_orderit_service_name) if skill_orderit_service_name is not None else None
        serviceRegion = ';'.join(skill_service_region) if skill_service_region is not None else None
        customerSupportModel = ';'.join(skill_support_model) if skill_support_model is not None else None
        requestType = ';'.join(skill_action_category) if skill_action_category is not None else None
        tag = ';'.join(skill_tag) if skill_tag is not None else None

        skill_attributes_query = f"""
        MERGE INTO {DB.skill_attributes()} AS target
        USING (SELECT ? AS skill_id, ? AS skill_name, ? AS controlDesk, ? AS goldenCustomer, ? AS customerMarketSegment, ? AS preferredlanguage, 
                    ? AS requestSource, ? AS product, ? AS serviceRegion, ? AS customerSupportModel, ? AS requestType, ? AS tag) AS source
        ON target.skill_id = source.skill_id
        WHEN MATCHED THEN
            UPDATE SET skill_name = source.skill_name, 
                    controlDesk = source.controlDesk, 
                    goldenCustomer = source.goldenCustomer, 
                    customerMarketSegment = source.customerMarketSegment, 
                    preferredlanguage = source.preferredlanguage, 
                    requestSource = source.requestSource, 
                    product = source.product, 
                    serviceRegion = source.serviceRegion, 
                    customerSupportModel = source.customerSupportModel, 
                    requestType = source.requestType,
                    tag = source.tag
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (skill_id, skill_name, controlDesk, goldenCustomer, customerMarketSegment, preferredlanguage, requestSource, 
                    product, serviceRegion, customerSupportModel, requestType, tag) 
            VALUES (skill_id, skill_name, controlDesk, goldenCustomer, customerMarketSegment, preferredlanguage,
                    requestSource, product, serviceRegion, customerSupportModel, requestType, tag);
        """
        skill_attributes_values = (skill_id, skill_name, controlDesk, goldenCustomer, customerMarketSegment, preferredlanguage,
                    requestSource, product, serviceRegion, customerSupportModel, requestType, tag)
        insert_into(conn, skill_attributes_query, skill_attributes_values)    
    
    except Exception as e:
        logger.exception(f"Error in updating routing filter id {skill_id} in {DB.skill_config()}. Error message: {e}")
        conn.rollback()

def event_delete(conn, skillsDict):
    """This functions deletes information related to a routing filter"""
    
    source_id = skillsDict["sourceId"]

    try:
        skill_id = skillsDict['event']['event']['oldValue']['id']
    except: 
        logger.error(f"Primary Key error, no skill id found for SourceId={source_id}")
        return

    try:
        # Delete the routing filter from all tables
        tables = [
            DB.skill_config(), DB.skill_agent_priority(), DB.skill_control_desk(), DB.skill_gold_customer(),
            DB.skill_market_segment(), DB.skill_pref_languages(), DB.skill_request_source(), DB.skill_service_name(),
            DB.skill_service_region(), DB.skill_support_model(), DB.skill_tag(), DB.skill_action_category(),
            DB.skill_attributes()
        ]

        for table in tables:
            delete_query = f"DELETE from {table} where skill_id = ?"
            delete_by_skill_id(conn, delete_query, (skill_id,))

    except Exception as e:
        logger.exception(f"Error in updating routing filter id {skill_id} in the database. Error message: {e}")
        conn.rollback()

def rmp_parsing(message_body, conn):
    # Parse the message body as JSON
    skillsDict = json.loads(message_body)
    source_id = skillsDict["sourceId"]
    eventType = skillsDict['event']['eventType']

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
        #         "sourceId":"62632d2f47f89a0001rohane",
        #         "dataDomain":"queue",
        #         "event":{
        #             "@type":"Event",
        #             "eventTime":"2022-04-21T19:49:04.826926057Z",
        #             "eventType":"Change",
        #             "correlationId":"f72edbf9-0ddd-4d8c-b1f6-39a5cc98a503",
        #             "domain":"queue",
        #             "title":"Queue created/updated/deleted",
        #             "source":{
        #                 "@type":"EntityRef",
        #                 "id":"62632d2f47f89a0001rohane",
        #                 "href":"/queue/62632d2f47f89a0001rohane",
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
        #                     "id":"rohan.surve",
        #                     "href":"$.relatedParty[?(@.id=='rohan.surve')]",
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
        #                     "id":"62632d2f47f89a0001rohane",
        #                     "name":"Rohan Routing Filter",
        #                     "distributionMode":"FILTER",
        #                     "searchDetails":{
        #                         "@type":"SearchDetails",
        #                         "@baseType":"SearchDetails",
        #                         "@type":"SearchDetails",
        #                         "@schemaLocation":"",
        #                         "name":"Rohan Routing Filter",
        #                         "filter":[
        #                             {
        #                                 "@type":"FilterGroup",
        #                                 "@baseType":"FilterGroup",
        #                                 "@type":"FilterGroup",
        #                                 "@schemaLocation":"",
        #                                 "filter":[
        #                                     {
        #                                         "@type":"AttributeFilter",
        #                                         "@baseType":"AttributeFilter",
        #                                         "@type":"AttributeFilter",
        #                                         "@schemaLocation":"",
        #                                         "field":"tag",
        #                                         "value":["SMARTPATH_DISTRIBUTION_MODE_FILTER"],
        #                                         "operator":"eq",
        #                                         "caseInsensitive":"true"
        #                                     }
        #                                 ],
        #                                 "groupOperator":"AND"
        #                             }
        #                         ],
        #                         "sort":[
        #                             {
        #                                 "field":"orderDate",
        #                                 "direction":"ASC"
        #                             }
        #                         ]
        #                     },
        #                     "queueStatus":"ACTIVE"
        #                 },
        #                 "newValue":{
        #                     "id":"62632d2f47f89a0001rohane",
        #                     "name":"Rohan Routing Filter",
        #                     "distributionMode":"FILTER",
        #                     "searchDetails":{
        #                         "@type":"SearchDetails",
        #                         "@baseType":"SearchDetails",
        #                         "@type":"SearchDetails",
        #                         "@schemaLocation":"",
        #                         "name":"Rohan Routing Filter",
        #                         "filter":[
        #                             {
        #                                 "@type":"FilterGroup",
        #                                 "@baseType":"FilterGroup",
        #                                 "@type":"FilterGroup",
        #                                 "@schemaLocation":"",
        #                                 "filter":[
        #                                     {
        #                                         "@type":"AttributeFilter",
        #                                         "@baseType":"AttributeFilter",
        #                                         "@type":"AttributeFilter",
        #                                         "@schemaLocation":"",
        #                                         "field":"characteristic.request-source",
        #                                         "value":["bcom","pwo"],
        #                                         "operator":"eq",
        #                                         "caseInsensitive":"true"
        #                                     },
        #                                     {
        #                                         "@type":"AttributeFilter",
        #                                         "@baseType":"AttributeFilter",
        #                                         "@type":"AttributeFilter",
        #                                         "@schemaLocation":"",
        #                                         "field":"characteristic.controlDesk",
        #                                         "value":["atlanticBtcSipt","bbmlarqc"],
        #                                         "operator":"eq",
        #                                         "caseInsensitive":"true"
        #                                     },
        #                                     {
        #                                         "@type":"AttributeFilter",
        #                                         "@baseType":"AttributeFilter",
        #                                         "@type":"AttributeFilter",
        #                                         "@schemaLocation":"",
        #                                         "field":"characteristic.service-region",
        #                                         "value":["EAST","NB"],
        #                                         "operator":"eq",
        #                                         "caseInsensitive":"true"
        #                                     },
        #                                     {
        #                                         "@type":"AttributeFilter",
        #                                         "@baseType":"AttributeFilter",
        #                                         "@type":"AttributeFilter",
        #                                         "@schemaLocation":"",
        #                                         "field":"tag",
        #                                         "value":["SMARTPATH_DISTRIBUTION_MODE_FILTER", "REASSIGNED"],
        #                                         "operator":"eq",
        #                                         "caseInsensitive":"true"
        #                                     }
        #                                 ],
        #                                 "groupOperator":"AND"
        #                             }
        #                         ],
        #                         "sort":[
        #                             {
        #                                 "field":"orderDate",
        #                                 "direction":"ASC"
        #                             }
        #                         ]
        #                     },
        #                     "queueStatus":"ACTIVE"
        #                 }
        #             }
        #         }
        #     }
        # ),
        # pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    )