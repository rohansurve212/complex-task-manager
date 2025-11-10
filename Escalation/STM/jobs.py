# Import necessary modules
from apscheduler.schedulers.background import BackgroundScheduler
from .BackgroundClass import BackgroundClass

# Setting up logging
import logging
logger = logging.getLogger("Escalation_Django log")

def start():
    # Initialize the scheduler
    scheduler = BackgroundScheduler()

    # Add a job to update escalation every minute
    scheduler.add_job(BackgroundClass.update_escalation, 'interval', minutes=1)

    # Add a job to fetch assigned date every hour
    scheduler.add_job(BackgroundClass.fetch_assigned_date, 'interval', minutes=60)

    # Start the scheduler to begin executing jobs
    scheduler.start()

    # Log that the scheduler has been started successfully
    logger.info(f"Scheduler add_job successfully and started successfully")