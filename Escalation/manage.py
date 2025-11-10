#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

es_logger = logging.getLogger('elasticsearch')
es_logger.setLevel(logging.WARNING)

logger = logging.getLogger("Escalation_Django log")
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('/app/log/escalation_django.log',when="midnight",interval=1,backupCount=7)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Escalation.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
