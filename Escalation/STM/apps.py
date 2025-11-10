from django.apps import AppConfig 
from django.utils.translation import gettext_lazy as _ 

import logging 
logger = logging.getLogger("Escalation_Django log")  # Creating a logger for the app with a custom log name

class STMConfig(AppConfig):  # Defining a new AppConfig class for the STM application
    default_auto_field = 'django.db.models.BigAutoField' 
    name = 'STM' 
    verbose_name = _("Smartpath Artificial Intelligence Routing Algorithm") 

    def ready(self):  # Overriding the ready method which is called when the app is ready
        import os  
        from . import jobs 

        # Checking if the app is running in the main process (to avoid running jobs in worker processes)
        if os.environ.get('RUN_MAIN', None) != 'true':  
            jobs.start()  # Starting the jobs when the app is ready
            logger.info(f"Job starts successfully") 