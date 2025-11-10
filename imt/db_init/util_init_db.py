import pandas as pd
import json
import pyodbc 
from shared.db import DB

def insert_into(conn, qry, values, table_name):

    c = conn.cursor()
    try:
        c.execute(qry, values)
        conn.commit()
        print(f"successfully inserted into table {table_name}, with query {qry}")
    except pyodbc.Error as e:
        print(f"Error occurred in {table_name}: ", e)
        conn.rollback()

def delete_by_skill_id(conn,qry_del, s_id):
    c = conn.cursor()
    try:
        c.execute(qry_del,s_id)
        conn.commit()
    except:
        print("error in deleting old values operation")
        conn.rollback()

def update_record(conn, qry_up, val):
    c = conn.cursor()
    try:
        c.execute(qry_up,val)
        conn.commit()
    except:
        print("error in updating old values operation")
        conn.rollback()


def get_skill_config_and_update_db(input_file,conn):
    '''
    This will return a dataframe containing all fields we need to fill up our database
    '''
    with open(input_file,'r') as f:
        data = json.loads(f.read())
    df_nested_list = pd.json_normalize(data, record_path =['content'])
    for index, row in df_nested_list.iterrows():
        skill_id = None 
        skill_name = None 
        skill_dist = None
        skill_status = None
        skill_tag =None
        skill_req_source =None
        skill_control_desk = None
        skill_service_region = None
        skill_pref_lang =None
        skill_supp_model = None
        skill_service_name = None 
        skill_golden_cust = None
        skill_market_segment = None
        skill_action_category = None 


        skill_id = row.id
        skill_name = row['name']
        skill_dist = row.distributionMode
        skill_status = row.queueStatus
        tmp = row['searchDetails.filter']
        df_level2 = pd.json_normalize(tmp, record_path =['filter'])
        
        for index, row1 in df_level2.iterrows():
            if row1.field == 'tag':
                if row1.value[0].startswith('SMARTPATH_DISTRIBUTION_MODE_'):
                    skill_tag = row1.value
            elif row1.field == 'characteristic.request-source':
                skill_req_source= row1.value
            elif row1.field == 'characteristic.controlDesk':
                skill_control_desk = row1.value
            elif row1.field == 'characteristic.service-region':
                skill_service_region = row1.value
            elif row1.field == 'characteristic.preferred-language':
                skill_pref_lang = row1.value
            elif row1.field == 'characteristic.support-model':
                skill_supp_model = row1.value 
            elif row1.field == 'orderItem.service.name':
                skill_service_name = row1.value
            elif row1.field == 'relatedParty.goldenCustomer.id':
                skill_golden_cust = row1.value
            elif row1.field == 'characteristic.marketSegment':
                skill_market_segment = row1.value
            elif row1.field == 'orderItem.actionCategory':
                skill_action_category = row1.value

        '''        
        # put it in a dataframe: 
        df_ = pd.DataFrame(columns= ['skill_id', 'skill_name', 'skill_dist', 'skill_status', 'skill_tag', 'skill_req_source', 'skill_control_desk', 'skill_service_region','skill_pref_lang', 'skill_supp_model','skill_service_item','skill_golden_cust','skill_market_segment','skill_action_category'] )
        df_tmp= {'skill_id': skill_id , 
                'skill_name': skill_name,
                'skill_dist':skill_dist, 
                'skill_status': skill_status,
                'skill_tag':skill_tag,
                'skill_req_source':skill_req_source,
                'skill_control_desk': skill_control_desk,
                'skill_service_region': skill_service_region,
                'skill_pref_lang': skill_pref_lang,
                'skill_supp_model':skill_supp_model,
                'skill_service_item': skill_service_item,
                'skill_golden_cust':skill_golden_cust,
                'skill_market_segment': skill_market_segment,
                'skill_action_category':skill_action_category }
        df_ = df_.append(df_tmp,ignore_index=True)
    return df_
        #return [skill_id,skill_name,skill_dist,skill_status,skill_tag,skill_req_source,skill_control_desk,skill_control_desk,skill_service_region,
        #skill_pref_lang,skill_supp_model,skill_service_item,skill_golden_cust,skill_market_segment,skill_action_category]
        '''
        # Sanity check, eventhough it is a create let us check if the skill_id already exist
        c = conn.cursor()  
        c.execute(f"SELECT skill_id FROM {DB.skill_config()} WHERE skill_id= ?", (skill_id,))
        data = c.fetchall()
        data=[]
        if len(data) != 0:
            print('There is already a component named  %s' %skill_id)
            continue
        else:
            # step0: update sklls_config table with the corresponding attributes and vlues
            qry = f"MERGE INTO {DB.skill_config()} AS target USING (VALUES (?,?,?,?)) AS source (skill_id, skill_name, skill_distribution, skill_status) ON target.skill_id = source.skill_id WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.skill_name = source.skill_name, target.skill_distribution = source.skill_distribution, target.skill_status = source.skill_status WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, skill_name, skill_distribution, skill_status) VALUES (?,?,?,?);"
            values = (skill_id, skill_name, skill_dist, skill_status, skill_id, skill_name, skill_dist, skill_status)
            insert_into(conn, qry, values, 'skill config')

            # Step1: CONTROL DESK
            if skill_control_desk!= None:
                for cdesk in skill_control_desk:
                    qry=f"MERGE INTO {DB.skill_control_desk()} AS target USING (VALUES (?,?)) AS source (skill_id, c_desk) ON (target.skill_id = source.skill_id AND target.c_desk = source.c_desk) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.c_desk = source.c_desk WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, c_desk) VALUES (?,?);"
                    values = (skill_id, cdesk, skill_id, cdesk)
                    insert_into(conn,qry,values, 'control desk')

            else:
                qry = f"INSERT INTO {DB.skill_control_desk()} (skill_id, c_desk) VALUES (?,?)"
                values = (skill_id,skill_control_desk)
                insert_into(conn,qry,values, 'control desk')
                
            # Step2: MARKET SEGMENT
            if skill_market_segment!= None:
                for msegment in skill_market_segment:
                    qry=f"MERGE INTO {DB.skill_market_segment()} AS target USING (VALUES (?,?)) AS source (skill_id, m_segment) ON (target.skill_id = source.skill_id AND target.m_segment = source.m_segment) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.m_segment = source.m_segment WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, m_segment) VALUES (?,?);"
                    values = (skill_id, msegment, skill_id, msegment)
                    insert_into(conn, qry,values, 'market segment')
                    
            else:
                qry=f"INSERT INTO {DB.skill_market_segment()} (skill_id, m_segment) VALUES (?,?)"
                values = (skill_id,skill_market_segment)
                insert_into(conn, qry, values, 'market segment')

            # Step3: PREFERRED LANGUAGES
            if skill_pref_lang!= None:
                for preflang in skill_pref_lang:
                    qry=f"MERGE INTO {DB.skill_pref_languages()} AS target USING (VALUES (?,?)) AS source (skill_id, p_language) ON (target.skill_id = source.skill_id AND target.p_language = source.p_language) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.p_language = source.p_language WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, p_language) VALUES (?,?);"
                    values = (skill_id, preflang, skill_id, preflang)
                    insert_into(conn, qry, values, 'pref languages')
                    
            else:
                qry=f"INSERT INTO {DB.skill_pref_languages()} (skill_id, p_language) VALUES (?,?)"
                values = (skill_id, skill_pref_lang)
                insert_into(conn, qry,values, 'pref languages')


            # Step4: REQUEST SOURCE
            if skill_req_source!= None:
                for reqsource in skill_req_source:
                    qry=f"MERGE INTO {DB.skill_request_source()} AS target USING (VALUES (?,?)) AS source (skill_id, r_source) ON (target.skill_id = source.skill_id AND target.r_source = source.r_source) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.r_source = source.r_source WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, r_source) VALUES (?,?);"
                    values = (skill_id, reqsource, skill_id, reqsource)
                    insert_into(conn, qry, values, 'request source')

            else:
                qry=f"INSERT INTO {DB.skill_request_source()} (skill_id, r_source) VALUES (?,?)"
                values = (skill_id, skill_req_source)
                insert_into(conn, qry, values, 'request source')

            # Step5: SERVICE NAME
            if skill_service_name!= None:
                for sname in skill_service_name:
                    qry=f"MERGE INTO {DB.skill_service_name()} AS target USING (VALUES (?,?)) AS source (skill_id, s_name) ON (target.skill_id = source.skill_id AND target.s_name = source.s_name) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.s_name = source.s_name WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, s_name) VALUES (?,?);"
                    values = (skill_id, sname, skill_id, sname)
                    insert_into(conn, qry, values, 'service name')

            else:
                qry=f"INSERT INTO {DB.skill_service_name()} (skill_id, s_name) VALUES (?,?)"
                values = (skill_id,skill_service_name)
                insert_into(conn,qry,values, 'service name')
                
            # Step6: SERVICE REGION 
            if skill_service_region!= None:
                for sregion in skill_service_region:
                    qry=f"MERGE INTO {DB.skill_service_region()} AS target USING (VALUES (?,?)) AS source (skill_id, s_region) ON (target.skill_id = source.skill_id AND target.s_region = source.s_region) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.s_region = source.s_region WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, s_region) VALUES (?,?);"
                    values = (skill_id, sregion, skill_id, sregion)
                    insert_into(conn,qry,values, 'service region')

            else:
                qry=f"INSERT INTO {DB.skill_service_region()} (skill_id, s_region) VALUES (?,?)"
                values = (skill_id,skill_service_region)
                insert_into(conn, qry, values, 'service region')
                
            # Step7: SUPPORT MODEL 
            if skill_supp_model!= None:
                for smodel in skill_supp_model:
                    qry=f"MERGE INTO {DB.skill_support_model()} AS target USING (VALUES (?,?)) AS source (skill_id, s_model) ON (target.skill_id = source.skill_id AND target.s_model = source.s_model) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.s_model = source.s_model WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, s_model) VALUES (?,?);"
                    values = (skill_id, smodel, skill_id, smodel)
                    insert_into(conn, qry,values, 'support model')

            else:
                qry=f"INSERT INTO {DB.skill_support_model()} (skill_id, s_model) VALUES (?,?)"
                values = (skill_id,skill_supp_model)
                insert_into(conn, qry,values, 'support model')

            # STP8: GOLDEN CUSTOMER ID 
            if skill_golden_cust!= None:
                for gcust in skill_golden_cust:
                    qry=f"MERGE INTO {DB.skill_gold_customer()} AS target USING (VALUES (?,?)) AS source (skill_id, g_customer) ON (target.skill_id = source.skill_id AND target.g_customer = source.g_customer) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.g_customer = source.g_customer WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, g_customer) VALUES (?,?);"
                    values =  (skill_id, gcust, skill_id, gcust)
                    insert_into(conn,qry,values, 'gold customer')
                    
            else:
                qry=f"INSERT INTO {DB.skill_gold_customer()} (skill_id, g_customer) VALUES (?,?)"
                values = (skill_id,skill_golden_cust)
                insert_into(conn, qry, values, 'gold customer')

            # STEP 9: TAG
            if skill_tag!= None:
                for stag in skill_tag:
                    qry=f"MERGE INTO {DB.skill_tag()} AS target USING (VALUES (?,?)) AS source (skill_id, s_tag) ON (target.skill_id = source.skill_id AND target.s_tag = source.s_tag) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.s_tag = source.s_tag WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, s_tag) VALUES (?,?);"
                    values =  (skill_id, stag, skill_id, stag)
                    insert_into(conn,qry,values, 'tag')
                    
            else:
                qry=f"INSERT INTO {DB.skill_tag()} (skill_id, s_tag) VALUES (?,?)"
                values = (skill_id, skill_tag)
                insert_into(conn, qry, values, 'tag')

            # STEP 10: ACTION CATEGORY
            if skill_action_category!= None:
                for s_act in skill_action_category:
                    qry=f"MERGE INTO {DB.skill_action_category()} AS target USING (VALUES (?,?)) AS source (skill_id, a_category) ON (target.skill_id = source.skill_id AND target.a_category = source.a_category) WHEN MATCHED THEN UPDATE SET target.skill_id = source.skill_id, target.a_category = source.a_category WHEN NOT MATCHED BY TARGET THEN INSERT (skill_id, a_category) VALUES (?,?);"
                    values =  (skill_id, s_act, skill_id, s_act)
                    insert_into(conn,qry,values, 'action category')
                    
            else:
                qry=f"INSERT INTO {DB.skill_action_category()} (skill_id, a_category) VALUES (?,?)"
                values = (skill_id, skill_action_category)
                insert_into(conn, qry, values, 'action category')


def get_agent_assignment_and_update_db(input_file,conn):
    with open(input_file,'r') as f:
        data = json.loads(f.read())

    df_nested_list = pd.json_normalize(data, record_path =['content'])
    print("the count is ", df_nested_list.count())
    for index, row in df_nested_list.iterrows():
        assigned_skill_id = row.queueId	
        agent_id = row.userId
        agent_pein =row.individualId
        skill_priority = row.priority

        # updating the tables in the SQLite database
        # STEP 1: Agent table
        qry_ins = f"MERGE INTO {DB.agent()} AS target USING (VALUES (?,?)) AS source (agent_id, pein) ON (target.agent_id = source.agent_id AND target.pein = source.pein) WHEN MATCHED THEN UPDATE SET target.agent_id = source.agent_id, target.pein = source.pein WHEN NOT MATCHED BY TARGET THEN INSERT (agent_id, pein) VALUES (?,?);"
        val = (agent_id, agent_pein, agent_id, agent_pein)
        print(qry_ins)
        insert_into(conn, qry_ins, val, 'agent')

        # STEP 2: Agent Priority table
        qry_ins = f"MERGE INTO {DB.skill_agent_priority()} AS target USING (VALUES (?,?,?)) AS source (agent_id, skill_id, skill_priority) ON (target.agent_id = source.agent_id AND target.skill_id = source.skill_id AND target.skill_priority = source.skill_priority) WHEN MATCHED THEN UPDATE SET target.agent_id = source.agent_id, target.skill_id = source.skill_id, target.skill_priority = source.skill_priority WHEN NOT MATCHED BY TARGET THEN INSERT (agent_id, skill_id, skill_priority) VALUES (?,?,?);"
        print(qry_ins)
        val = (agent_id, assigned_skill_id, skill_priority, agent_id, assigned_skill_id, skill_priority)
        insert_into(conn, qry_ins, val, 'agent priority')
