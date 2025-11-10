# Import necessary modules
from django.db import models
import pandas as pd
from datetimeutc.fields import DateTimeUTCField  
from django.utils.translation import gettext_lazy as _
from STM.db import DB
import logging

# Setting up logging
logger = logging.getLogger("Escalation_Django log")

# Configure pandas display settings
pd.set_option('display.max_columns', None)

# Define the Escalation model for the database
class Escalation(models.Model):

    # Define fields for the Escalation model
    escalation_id = models.AutoField(primary_key=True)
    request_id = models.CharField(unique=True, max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS',blank=True)
    escalation_ticket_no = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True,unique=True,null=False) 
    choices = [('R1', _('Executive/VP Request')), ('R2', _('Past Contractual SLA')),('R3', _('Billing Dispute'))]
    request_level = models.CharField(max_length=255, choices=choices, blank=True)
    request_reason= models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True)
    priority = models.IntegerField(blank=True)
    submission_dt = DateTimeUTCField(auto_now_add=True)
    status = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS',default='open') #editable = False, 
    assigned_dt = models.DateTimeField(blank=True, null=True)
    submission_person_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS',null=True,blank=True)


    # Override the save method to set certain fields based on request level
    def save(self, *args, **kwargs):
        if 'username' in kwargs:
            self.submission_person_name = kwargs['username']
        self.request_id = self.request_id.upper()
        if self.request_level=='R1' :
            self.priority = 1
            self.request_reason = 'Executive/VP Request'
            super(Escalation, self).save(*args, **kwargs)
        if self.request_level=='R2' :
            self.priority = 1
            self.request_reason = 'Past Contractual SLA'   
            super(Escalation, self).save(*args, **kwargs)
        if self.request_level=='R3' :
            self.priority = 2
            self.request_reason = 'Billing Dispute'   
            super(Escalation, self).save(*args, **kwargs)


    # Update method for saving the record (same as save)
    def update(self, *args, **kwargs):
        super(Escalation, self).save(*args, **kwargs)

    # Meta configuration for the model
    class Meta:
        managed = False
        db_table = DB.escalation()
        verbose_name = _('Prioritized request')

# Define the Agent model for the database
class Agent(models.Model):
    agent_id = models.CharField(primary_key=True, max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    pein = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    full_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)

    # Meta configuration for the model
    class Meta:
        managed = False
        db_table = DB.agent()
