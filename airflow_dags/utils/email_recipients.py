# Import necessary classes from custom utils
from utils.envs.env_variable import EnvVariable, EnvironmentType

# Class to manage email recipients based on environment type
class Email:
    _env_var: EnvVariable
    
    # Initialize with environment variable instance
    def __init__(self, env_var: EnvVariable):
        self._env_var = env_var

    # Method to get email recipients for general notifications
    def get_email_recipients(self) -> list:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return ["stm.alerts@bell.ca"]
        return ["rohan.surve@bell.ca", "stm.alerts@bell.ca"]
    
    # Method to get email recipients for no work notifications
    def get_email_recipients_for_no_work(self) -> list:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return ["samandeep.singh@bell.ca","jeevika.baskaran@bell.ca","anna.lafarciola@bell.ca","debbie_lynn.borges@bell.ca","nizar.bu_ghanem@bell.ca","simon.lebel@bell.ca","shannon.peiris@bell.ca","marie-eve.roy@bell.ca","annick.bourbeau@bell.ca","nathalie.rompre@bell.ca","andy.nan@bell.ca","anne-marie.oostveen@bell.ca","louise.pesant@bell.ca","janie.labelle@bell.ca","deepika.verma@bell.ca","stm.alerts@bell.ca", "yousef.suedan@bell.ca"]
        return ["rohan.surve@bell.ca", "stm.alerts@bell.ca"]
    
    # Method to get email recipients for idle time notifications
    def get_email_recipients_for_idle_time(self) -> list:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return ["samandeep.singh@bell.ca","jeevika.baskaran@bell.ca","anna.lafarciola@bell.ca","simon.lebel@bell.ca","marie-eve.roy@bell.ca","deepika.verma@bell.ca","stm.alerts@bell.ca"]
        return ["rohan.surve@bell.ca", "stm.alerts@bell.ca"]
    
    # Method to get email recipients for unassigned escalations notifications
    def get_email_recipients_for_unassigned_escalations(self) -> list:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return ["samandeep.singh@bell.ca", "anna.lafarciola@bell.ca", "stm.alerts@bell.ca"]
        return ["rohan.surve@bell.ca", "stm.alerts@bell.ca"]
    
    # Method to get email recipients for unassigned escalations notifications
    def get_email_recipients_for_request_cache(self) -> list:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return ["samandeep.singh@bell.ca", "anna.lafarciola@bell.ca", "jeevika.baskaran@bell.ca", "stm.alerts@bell.ca"]
        return ["rohan.surve@bell.ca", "stm.alerts@bell.ca"]