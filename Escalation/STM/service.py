import logging

logger = logging.getLogger("Escalation API log")

# class UpdateDb:

#     def __init__(self,
#     con,
#     request_id,
#     priority,
#     agent_id,
#     requestor_name,
#     submission_person_name,
#     sql_table, 
#     agent_table
#     ) -> None:
#         self.con = con
#         self.request_id = request_id
#         self.priority = priority
#         self.agent_id = agent_id
#         self.requestor_name = requestor_name
#         self.submission_person_name = submission_person_name
#         self.sql_table = sql_table
#         self.agent_table = agent_table

#     def agent_exists(self) -> bool:
        
#         cur = self.con.cursor()

#         sql_exist = f"SELECT COUNT(*) FROM {self.agent_table} WHERE agent_id ='{self.agent_id}';"
#         count = cur.execute(sql_exist).fetchall()[0][0]

#         if count > 0:
#             cur.close() 
#             return True
        
#         cur.close()
#         return False 
        
#     def run(self):

#         cur = self.con.cursor()
        
#         sql = (
#             f"MERGE INTO {self.sql_table} WITH (HOLDLOCK) AS target"
#             f" USING (SELECT"
#             f" '{self.request_id}' AS request_id,"
#             f" {self.priority} AS priority,"
#             f" '{self.agent_id}' AS agent_id,"
#             f" '{self.requestor_name}' AS requestor_name,"
#             f" '{self.submission_person_name}' AS submission_person_name,"
#             f" 'open' AS status)"
#             f" AS source"
#             f" (request_id, priority, agent_id,requestor_name, submission_person_name, status)"
#             f" ON (target.request_id = source.request_id)"
#             f" WHEN MATCHED THEN UPDATE SET"
#             f" priority = {self.priority},"
#             f" agent_id = '{self.agent_id}',"
#             f" requestor_name = '{self.requestor_name}',"
#             f" submission_person_name = '{self.submission_person_name}',"
#             f" status = 'open'"
#             f" WHEN NOT MATCHED THEN INSERT (request_id, priority, agent_id, status,requestor_name,submission_person_name)"
#             f" VALUES ('{self.request_id}', {self.priority}, '{self.agent_id}', 'open','{self.requestor_name}','{self.submission_person_name}');"
#         )

#         try: 
#             cur.execute(sql)
#             self.con.commit()
#             logger.info(f"Record with query={sql} updated successfully")
#             cur.close()
#             return "SUCCESS"
        
#         except Exception as e:
#             logger.error(f"Record with query={sql} did NOT update. Error message: {e}")
#             self.con.rollback()
#             cur.close()
#             return "DB_ERROR"

        
