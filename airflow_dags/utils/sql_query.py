# Import necessary classes from custom utils
from utils.envs.env_variable import EnvVariable, EnvironmentType

# Class to manage SQL queries based on environment type
class DB:
    _env_var: EnvVariable
    
    # Initialize with environment variable instance
    def __init__(self, env_var: EnvVariable):
        self._env_var = env_var
    
    # Method to get SQL query for get work results
    def get_sql_query(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT * FROM dbo.getwork_results where work_status NOT IN ('NO_WORK','NO_ASSIGNMENT') AND assign_date >= DATEADD(day, -7, GETDATE())"""
        return f"""SELECT * FROM dbo.uat_getwork_results where work_status NOT IN ('NO_WORK','NO_ASSIGNMENT') AND assign_date >= DATEADD(day, -7, GETDATE())"""
    
    # Method to get SQL query for alerts
    def get_sql_query_alerts(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT agent_id, request_id, external_id, assign_date, global_latency, work_status FROM dbo.getwork_results where assign_date >= DATEADD(minute, -10, GETUTCDATE())"""
        return f"""SELECT agent_id, request_id, external_id, assign_date, global_latency, work_status FROM dbo.uat_getwork_results where assign_date >= DATEADD(minute, -10, GETUTCDATE())"""
    
    # Method to get SQL query for no request assigned
    def get_sql_query_no_req_assigned(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT agent_id, request_id, external_id, assign_date FROM dbo.getwork_results where assign_date >= DATEADD(hour, -2, GETUTCDATE())"""
        return f"""SELECT agent_id, request_id, external_id, assign_date FROM dbo.uat_getwork_results where assign_date >= DATEADD(hour, -2, GETUTCDATE())"""
    
    # Method to get Teradata query for FOC
    def get_teradata_query_foc(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT	smtpth_req_id, smtpth_req_create_dt, smtpth_req_start_dt, smtpth_req_action		
                    FROM	GRP_JARVIS_ANALYSIS.fact_smtpth_request_v2 where CAST(smtpth_req_start_dt AS DATE) >= CURRENT_DATE - INTERVAL '7' DAY"""
        return ''
    
    # Method to get SQL query for FOC
    def get_sql_query_foc(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT id, request_id, work_status, orderdate, ttpu, assign_date, request_type FROM dbo.getwork_results where assign_date >= DATEADD(day, -7, GETDATE())"""
        return ''
    
    # Method to get SQL query for escalation
    def get_sql_query_escalation(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT * FROM dbo.escalation"""
        return f"""SELECT * FROM dbo.uat_escalation"""
    
    # Method to get SQL query for agent
    def get_sql_query_agent(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT * FROM dbo.agent"""
        return f"""SELECT * FROM dbo.uat_agent"""
    
    # Method to get SQL query for STM agents
    def get_agents_stm(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT agent_id, full_name FROM dbo.agent where agent_id in (select distinct agent_id from dbo.getwork_results)"""
        return ''
    
    # Method to get SQL query for LDAP data
    def get_ldap_data(self, agent_ids) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT person_pein, person_login1, person_full_name, person_manager_name, person_manager_pein, person_hrchy_level4_name, person_hrchy_level4_pein, 
                person_hrchy_level4_tier, person_hrchy_level3_name, person_hrchy_level3_pein, person_hrchy_level3_tier 
                FROM GRP_JARVIS_ANALYSIS.dim_person WHERE person_login1 IN {agent_ids} AND person_scd_current_row = 1"""
        return ''
    
    # Method to get SQL query for CP emails
    def get_cp_emails(self, cp_peins) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return ''
            # return f"""SELECT person_email FROM GRP_JARVIS_ANALYSIS.dim_person WHERE person_pein IN {cp_peins} AND person_scd_current_row = 1"""
        return ''
    
    # Method to get SQL query for no work
    def get_nowork(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT id, agent_id, assign_date, work_status FROM dbo.getwork_results where work_status in ('NO_WORK', 'NO_ASSIGNMENT') and assign_date >= DATEADD(minute, -10, GETUTCDATE())"""
        return ''
    
    # Method to get SQL query for no work
    def get_nowork_backfill(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT id, agent_id, assign_date, work_status FROM dbo.getwork_results where work_status in ('NO_WORK', 'NO_ASSIGNMENT') and assign_date >= '2025-05-09 00:00:00.000' AND
assign_date <= '2025-07-04 00:00:00.000'"""
        return ''
    
    # Method to get SQL query for push model data
    def get_push_model_data(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT * FROM dbo.getwork_results WHERE agent_id IN (SELECT agent_id FROM dbo.push_model_agents) AND work_status NOT IN ('NO_WORK','NO_ASSIGNMENT') AND assign_date >= DATEADD(day, -1, GETDATE())"""
        return ''
    
    # Method to get SQL query for idle push agents
    def get_idle_push_agents(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f""" SELECT agent_id FROM dbo.disposition_status WHERE agent_id in (SELECT agent_id FROM dbo.push_model_agents) AND status = 'available' AND last_updated <= DATEADD(minute, -2.5, GETUTCDATE())"""
        return ''
    
    # Method to get SQL query for agents idle for 6 minutes or more
    def get_agents_push_model_6_minutes(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT agent_id, full_name FROM dbo.agent where agent_id in 
                        (SELECT distinct agent_id from dbo.getwork_results where agent_id in 
						(SELECT agent_id FROM dbo.disposition_status where status = 'available' and last_updated <= DATEADD(minute, -6, GETUTCDATE())))"""
        return ''
    
    # Method to get SQL query for idle time data
    def get_idle_time(self, agent_ids) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT  smtpth_disp_date, smtpth_disp_event_newStat, smtpth_disp_relParty_id,
		                    smtpth_disp_relParty_name, total_available_time, total_work_time 
                    FROM GRP_JARVIS_ANALYSIS.fact_smtpth_disptn_detail
                    where smtpth_disp_date = CURRENT_DATE - INTERVAL '1' DAY
                    AND smtpth_disp_event_newStat in ('available','busyNetNew','busyInProgress')
                    AND smtpth_disp_relParty_id in {agent_ids}"""
        return ''
        
    # Method to get SQL query for CP data
    def get_cp_data(self, agent_ids) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT person_login1, person_manager_name, person_hrchy_level4_name, 
                person_hrchy_level4_tier, person_hrchy_level3_name, person_hrchy_level3_tier 
                FROM GRP_JARVIS_ANALYSIS.dim_person WHERE person_login1 IN {agent_ids} AND person_scd_current_row = 1"""
        return ''
    
    # Method to get SQL query for STM agents
    def get_stm_agents(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT distinct agent_id from dbo.getwork_results"""
        return ''
    
    def get_sql_query_p1_p2(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT agent_id,external_id,assign_date,skill_id,skill_name FROM dbo.getwork_results where work_status NOT IN ('NO_WORK','NO_ASSIGNMENT') AND assign_date >= DATEADD(day, -1, GETUTCDATE())"""
        return f"""SELECT agent_id,external_id,assign_date,skill_id,skill_name FROM dbo.uat_getwork_results where work_status NOT IN ('NO_WORK','NO_ASSIGNMENT') AND assign_date >= DATEADD(day, -1, GETUTCDATE())"""
    
    def get_skill_agent_priority(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT * FROM dbo.skill_agent_priority"""
        return f"""SELECT * FROM dbo.uat_skill_agent_priority"""
    
    def get_unassigned_escalated_requests(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT request_id, request_reason, CONVERT(DATETIME2(0), submission_dt AT TIME ZONE 'UTC' AT TIME ZONE 'Eastern Standard Time') AS eastern_submission_dt FROM dbo.escalation WHERE status = 'open' AND assigned_dt IS NULL AND submission_dt <= DATEADD(hour, -24, GETUTCDATE())"""
        return f"""SELECT request_id, request_reason, CONVERT(DATETIME2(0), submission_dt AT TIME ZONE 'UTC' AT TIME ZONE 'Eastern Standard Time') AS eastern_submission_dt FROM dbo.uat_escalation WHERE status = 'open' AND assigned_dt IS NULL AND submission_dt <= DATEADD(hour, -24, GETUTCDATE())"""
    
    def get_unassigned_escalated_requests_dashboard(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f"""SELECT 
            request_id, 
            request_reason,
            DATEDIFF (day, submission_dt, GETUTCDATE()) AS days_since_submission
            FROM dbo.escalation 
            WHERE status = 'open' 
            AND assigned_dt IS NULL 
            AND submission_dt <= DATEADD(hour, -24, GETUTCDATE())"""
        return f"""SELECT 
            request_id, 
            request_reason,
            DATEDIFF (day, submission_dt, GETUTCDATE()) AS days_since_submission
            FROM dbo.uat_escalation 
            WHERE status = 'open' 
            AND assigned_dt IS NULL 
            AND submission_dt <= DATEADD(hour, -24, GETUTCDATE())"""

    # Method to get SQL query for DOW analysis overview
    def get_dow_analysis_overview(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return """WITH date_extraction AS (
                SELECT 
                smtpth_db_row_id,
                smtpth_evnt_desc,
                smtpth_evnt_dt,
                REGEXP_SUBSTR(smtpth_evnt_desc,
                '([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}\\.[0-9]{1,9}Z)|([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z)|([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{4}Z)|([0-9]{2}[A-Z]{3}[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2})'
                ) AS extracted_date, --This standardizes the format in which the new follow up date is written
                CAST(
                SUBSTR(extracted_date, 1, 10) || ' ' || 
                SUBSTR(extracted_date, 12, 2) || ':' || 
                SUBSTR(extracted_date, 14, 2) || ':00' 
                AS TIMESTAMP(0)
                ) AS new_followup_date --Extracts the new follow up date in the standardized format
                FROM GRP_JARVIS_ANALYSIS.fact_smtpth_event_v2
                WHERE smtpth_evnt_title = 'Follow-up date changed'
                AND smtpth_evnt_rperson_nm <> 'SYSTEM'
                AND smtpth_evnt_rperson_nm <> 'SYSTEM/AGENT'
                AND smtpth_evnt_desc LIKE '%T%Z%' --Ensures all of the new follow up dates are now in proper format
                AND smtpth_evnt_date >= '2025-01-01' --Start of date range for the data
                AND smtpth_evnt_date <= CURRENT_TIMESTAMP --End of date range for the data
                AND extracted_date IS NOT NULL
                ),
                mapped_dates AS (
                SELECT
                smtpth_db_row_id,
                smtpth_evnt_dt,
                new_followup_date,
                CASE 
                WHEN new_followup_date IS NULL THEN 'Null Follow Up Date'
                ELSE CASE td_day_of_week(CAST(new_followup_date AS DATE))
                WHEN 1 THEN 'Sunday (New Follow Up Date)'
                WHEN 2 THEN 'Monday (New Follow Up Date)'
                WHEN 3 THEN 'Tuesday (New Follow Up Date)'
                WHEN 4 THEN 'Wednesday (New Follow Up Date)'
                WHEN 5 THEN 'Thursday (New Follow Up Date)'
                WHEN 6 THEN 'Friday (New Follow Up Date)'
                WHEN 7 THEN 'Saturday (New Follow Up Date)'
                ELSE 'Unknown (New Follow Up Date)'
                END
                END AS new_follow_up_dow_name, --Creates buckets for the new follow up dates
                td_day_of_week(CAST(smtpth_evnt_dt AS DATE)) AS original_event_dow 
                FROM date_extraction
                ),
                base_data AS (
                SELECT
                new_follow_up_dow_name,
                COUNT(DISTINCT CASE WHEN original_event_dow = 1 THEN smtpth_db_row_id END) AS Sunday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 2 THEN smtpth_db_row_id END) AS Monday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 3 THEN smtpth_db_row_id END) AS Tuesday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 4 THEN smtpth_db_row_id END) AS Wednesday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 5 THEN smtpth_db_row_id END) AS Thursday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 6 THEN smtpth_db_row_id END) AS Friday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 7 THEN smtpth_db_row_id END) AS Saturday
                FROM mapped_dates
                GROUP BY new_follow_up_dow_name
                ), --Each case represents what day of week a follow up date was changed
                combined AS (
                SELECT
                new_follow_up_dow_name AS new_follow_up_dow,
                Sunday,
                Monday,
                Tuesday,
                Wednesday,
                Thursday,
                Friday,
                Saturday,
                (Sunday + Monday + Tuesday + Wednesday + Thursday + Friday + Saturday) AS Total,
                CASE new_follow_up_dow_name
                WHEN 'Sunday (New Follow Up Date)' THEN 0
                WHEN 'Monday (New Follow Up Date)' THEN 1
                WHEN 'Tuesday (New Follow Up Date)' THEN 2
                WHEN 'Wednesday (New Follow Up Date)' THEN 3
                WHEN 'Thursday (New Follow Up Date)' THEN 4
                WHEN 'Friday (New Follow Up Date)' THEN 5
                WHEN 'Saturday (New Follow Up Date)' THEN 6
                WHEN 'Null Follow Up Date' THEN 7
                ELSE 8
                END AS sort_order
                FROM base_data
                UNION ALL
                SELECT
                'Total',
                SUM(Sunday),
                SUM(Monday),
                SUM(Tuesday),
                SUM(Wednesday),
                SUM(Thursday),
                SUM(Friday),
                SUM(Saturday),
                SUM(Sunday + Monday + Tuesday + Wednesday + Thursday + Friday + Saturday),
                9 AS sort_order
                FROM base_data
                )
                SELECT
                new_follow_up_dow AS "New Follow Up Date Day of Week",
                Sunday       AS "Event Date on Sunday",
                Monday       AS "Event Date on Monday",
                Tuesday      AS "Event Date on Tuesday",
                Wednesday    AS "Event Date on Wednesday",
                Thursday     AS "Event Date on Thursday",
                Friday       AS "Event Date on Friday",
                Saturday     AS "Event Date on Saturday",
                Total        AS "Total"
                FROM combined
                ORDER BY sort_order, new_follow_up_dow"""
        return ''

    # Method to get SQL query for DOW analysis agents
    def get_dow_analysis_agents(self) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return """WITH date_extraction AS (
                SELECT 
                smtpth_db_row_id,
                smtpth_evnt_desc,
                smtpth_evnt_dt,
                smtpth_evnt_rperson_nm,
                REGEXP_SUBSTR(smtpth_evnt_desc,
                '([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}\\.[0-9]{1,9}Z)|([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z)|([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{4}Z)|([0-9]{2}[A-Z]{3}[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2})'
                ) AS extracted_date, --This standardizes the format in which the new follow up date is written
                CAST(
                SUBSTR(extracted_date, 1, 10) || ' ' || 
                SUBSTR(extracted_date, 12, 2) || ':' || 
                SUBSTR(extracted_date, 14, 2) || ':00' 
                AS TIMESTAMP(0)
                ) AS new_followup_date --Extracts the new follow up date in the standardized format
                FROM GRP_JARVIS_ANALYSIS.fact_smtpth_event_v2
                WHERE smtpth_evnt_title = 'Follow-up date changed'
                AND smtpth_evnt_rperson_nm <> 'SYSTEM'
                AND smtpth_evnt_rperson_nm <> 'SYSTEM/AGENT'
                AND smtpth_evnt_desc LIKE '%T%Z%' --Ensures all of the new follow up dates are now in proper format
                AND smtpth_evnt_date >= '2025-01-01' --Start of date range for the data
                AND smtpth_evnt_date <= CURRENT_TIMESTAMP --End of date range for the data
                AND extracted_date IS NOT NULL
                ),
                mapped_dates AS (
                SELECT
                smtpth_db_row_id,
                COALESCE(TRIM(smtpth_evnt_rperson_nm), 'UNKNOWN_AGENT') AS agent_name,
                smtpth_evnt_dt,
                new_followup_date,
                CASE 
                WHEN new_followup_date IS NULL THEN 'Null Follow Up Date'
                ELSE CASE td_day_of_week(CAST(new_followup_date AS DATE))
                WHEN 1 THEN 'Sunday (New Follow Up Date)'
                WHEN 2 THEN 'Monday (New Follow Up Date)'
                WHEN 3 THEN 'Tuesday (New Follow Up Date)'
                WHEN 4 THEN 'Wednesday (New Follow Up Date)'
                WHEN 5 THEN 'Thursday (New Follow Up Date)'
                WHEN 6 THEN 'Friday (New Follow Up Date)'
                WHEN 7 THEN 'Saturday (New Follow Up Date)'
                ELSE 'Unknown (New Follow Up Date)'
                END
                END AS new_follow_up_dow_name, --Creates buckets for the new follow up dates
                td_day_of_week(CAST(smtpth_evnt_dt AS DATE)) AS original_event_dow
                FROM date_extraction
                ),
                agg_per_agent AS (
                SELECT
                agent_name,
                new_follow_up_dow_name,
                COUNT(DISTINCT CASE WHEN original_event_dow = 1 THEN smtpth_db_row_id END) AS Sunday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 2 THEN smtpth_db_row_id END) AS Monday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 3 THEN smtpth_db_row_id END) AS Tuesday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 4 THEN smtpth_db_row_id END) AS Wednesday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 5 THEN smtpth_db_row_id END) AS Thursday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 6 THEN smtpth_db_row_id END) AS Friday,
                COUNT(DISTINCT CASE WHEN original_event_dow = 7 THEN smtpth_db_row_id END) AS Saturday
                FROM mapped_dates
                GROUP BY agent_name, new_follow_up_dow_name
                ), --Each case represents what day of week a follow up date was changed
                combined AS (
                SELECT
                agent_name,
                new_follow_up_dow_name AS new_follow_up_dow,
                Sunday,
                Monday,
                Tuesday,
                Wednesday,
                Thursday,
                Friday,
                Saturday,
                (Sunday + Monday + Tuesday + Wednesday + Thursday + Friday + Saturday) AS Total,
                CASE new_follow_up_dow_name
                WHEN 'Sunday (New Follow Up Date)' THEN 0
                WHEN 'Monday (New Follow Up Date)' THEN 1
                WHEN 'Tuesday (New Follow Up Date)' THEN 2
                WHEN 'Wednesday (New Follow Up Date)' THEN 3
                WHEN 'Thursday (New Follow Up Date)' THEN 4
                WHEN 'Friday (New Follow Up Date)' THEN 5
                WHEN 'Saturday (New Follow Up Date)' THEN 6
                WHEN 'Null Follow Up Date' THEN 7
                ELSE 8
                END AS sort_order
                FROM agg_per_agent
                ),
                agent_totals AS (
                SELECT
                agent_name,
                'Total' AS new_follow_up_dow,
                SUM(Sunday) AS Sunday,
                SUM(Monday) AS Monday,
                SUM(Tuesday) AS Tuesday,
                SUM(Wednesday) AS Wednesday,
                SUM(Thursday) AS Thursday,
                SUM(Friday) AS Friday,
                SUM(Saturday) AS Saturday,
                SUM(Total) AS Total,
                9 AS sort_order
                FROM combined
                GROUP BY agent_name
                ),
                final_result AS (
                SELECT * FROM combined
                UNION ALL
                SELECT * FROM agent_totals
                )
                SELECT
                agent_name AS "Agent",
                new_follow_up_dow AS "New Follow Up Date Day of Week",
                Sunday       AS "Event Date on Sunday",
                Monday       AS "Event Date on Monday",
                Tuesday      AS "Event Date on Tuesday",
                Wednesday    AS "Event Date on Wednesday",
                Thursday     AS "Event Date on Thursday",
                Friday       AS "Event Date on Friday",
                Saturday     AS "Event Date on Saturday",
                Total        AS "Total"
                FROM final_result
                ORDER BY
                agent_name,
                sort_order,
                new_follow_up_dow"""
        return ''
    