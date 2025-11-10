import os

from dotenv import load_dotenv
load_dotenv()

class DB:
    _env = os.getenv('ENVIRONMENT')

    @staticmethod
    def agent():
        return DB._get_table_name('agent')

    @staticmethod
    def skill_config():
        return DB._get_table_name('skill_config')

    @staticmethod
    def skill_agent_priority():
        return DB._get_table_name('skill_agent_priority')

    @staticmethod
    def skill_request_source():
        return DB._get_table_name('skill_request_source')

    @staticmethod
    def skill_service_region():
        return DB._get_table_name('skill_service_region')

    @staticmethod
    def skill_pref_languages():
        return DB._get_table_name('skill_pref_languages')

    @staticmethod
    def skill_market_segment():
        return DB._get_table_name('skill_market_segment')

    @staticmethod
    def skill_control_desk():
        return DB._get_table_name('skill_control_desk')

    @staticmethod
    def skill_support_model():
        return DB._get_table_name('skill_support_model')

    @staticmethod
    def skill_service_name():
        return DB._get_table_name('skill_service_name')
    
    @staticmethod
    def skill_tag():
        return DB._get_table_name('skill_tag')

    @staticmethod
    def skill_gold_customer():
        return DB._get_table_name('skill_gold_customer')

    @staticmethod
    def skill_action_category():
        return DB._get_table_name('skill_action_category')

    @staticmethod
    def permission_agent():
        return DB._get_table_name('permission_agent')

    @staticmethod
    def disposition_status():
        return DB._get_table_name('disposition_status')

    @staticmethod
    def dim_flow():
        return DB._get_table_name('dim_flow')

    @staticmethod
    def proficiency():
        return DB._get_table_name('proficiency')

    @staticmethod
    def foc_targets():
        return DB._get_table_name('foc_targets')
    
    @staticmethod
    def getwork_results():
        return DB._get_table_name('getwork_results')

    @staticmethod
    def escalation():
        return DB._get_table_name('escalation')
    
    @staticmethod
    def skill_attributes():
        return DB._get_table_name('skill_attributes')

    @staticmethod
    def sla():
        return DB._get_table_name_TD('dim_smtpth_stm_trgt')
    
    @staticmethod
    def push_model_agents():
        return DB._get_table_name('push_model_agents')

    @staticmethod
    def _get_table_name(table_name: str) -> str:
        if DB._env == "PROD":
            return f"dbo.{table_name}"
        return f"dbo.uat_{table_name}"
    
    @staticmethod
    def _get_table_name_TD(table_name: str) -> str:
        return f"GRP_JARVIS_ANALYSIS.{table_name}"