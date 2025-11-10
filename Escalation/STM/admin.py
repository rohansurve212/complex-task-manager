from django.contrib import admin

# Register your models here.
from STM.models import Escalation,Agent
from datetime import datetime
import datetime
import logging
# Configure logger for Escalation Django application
logger = logging.getLogger("Escalation_Django log")

# Import search-related functionality from STM documents
from STM.documents import *
from STM import BackgroundClass
from django import forms
from django.forms import Select
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# Suppress warnings from insecure HTTP requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_request(request, accessToken):
    # Fetch request details from Smartpath ElasticSearch
    request_response = get_request_from_smtpth_elastic(request, accessToken)
    request_response_text = json.loads(request_response.text)
    request_object = request_response_text['results']
    return request_object

# Define a custom form for managing Escalation objects in the admin panel
class PersonAdminForm(forms.ModelForm):

    class Meta:
        model = Escalation
        fields = "__all__"

        # Define widgets to customize the display of specific fields
        widgets = {
            'status':  forms.HiddenInput(),
            'assigned_dt':  forms.HiddenInput(),
            'request_level': Select(attrs={ 'value': 'Select Option'}),
            'request_reason':  forms.HiddenInput(),
            'priority':forms.HiddenInput(),
            'submission_person_name':  forms.HiddenInput(),
            }
        # Labels for form fields with translations
        labels = {
        "request_id": _("Smartpath Original Request ID*"),
        "escalation_ticket_no":_("Smartpath Escalation Request ID*"),
        "request_level": _("Reason for request*"),
        "submission_person_name": _("Submission person name"),        
    }
        
    # Custom validation logic for the form
    def clean(self):
        accessToken = BackgroundClass.get_token()
        
        if self.cleaned_data["escalation_ticket_no"]=='' and self.cleaned_data["request_id"]=='':
            raise forms.ValidationError(_("Smartpath Original Request ID AND Smartpath Escalation Request ID IS REQUIRED"))
        
        if  self.cleaned_data["escalation_ticket_no"]!='' and self.cleaned_data["request_id"]=='':
            raise forms.ValidationError(_("REQUEST_ID IS REQUIRED"))
        
        if self.cleaned_data["escalation_ticket_no"]=='' and self.cleaned_data["request_id"]!='':
            raise forms.ValidationError(_("Smartpath Escalation Request ID IS REQUIRED"))
        
        if self.cleaned_data["request_level"] == '' :
            raise forms.ValidationError(_("Select Request Reason"))

        request_list = get_request(self.cleaned_data["request_id"], accessToken)
        
        if self.cleaned_data["request_id"]!='' and request_exists(self.cleaned_data["request_id"], request_list)==False:
            raise forms.ValidationError(_("Request Not Found"))
        
        if self.cleaned_data["request_id"]!='' and request_is_completed(self.cleaned_data["request_id"], request_list)==True:
            raise forms.ValidationError(_("Request already completed"))
        
        if self.cleaned_data["request_id"]!='' and request_is_cancelled(self.cleaned_data["request_id"], request_list)==True:
            raise forms.ValidationError(_("Request already cancelled"))
        
        if self.cleaned_data["request_id"]!='' and check_control_desk_before_escalation(self.cleaned_data["request_id"], request_list)==True:
            raise forms.ValidationError(_("Control desk is related to escalation"))

        try:
            # Check for duplicate request IDs
            qs=Escalation.objects.all().filter(request_id=self.cleaned_data["request_id"])
            logger.info(f"Escalation.objects.all().filter(request_id=request_id) {qs} successfully")
            print('qs',qs)
            if qs:
                raise forms.ValidationError(_('Request ID already exists'))
        except Escalation.DoesNotExist:
            return self.cleaned_data["request_id"]        
        
        # Check for duplicate escalation ticket numbers
        try:
            qs=Escalation.objects.all().filter(escalation_ticket_no=self.cleaned_data["escalation_ticket_no"])
            logger.info(f"Escalation.objects.all().filter(request_id=request_id) {qs} successfully")
            print('qs',qs)
            if qs:
                raise forms.ValidationError(_('Smartpath Escalation Request ID already exists'))
        except Escalation.DoesNotExist:
            return self.cleaned_data["escalation_ticket_no"]

# Define an alternate form for editing Escalation objects
class PersonAdminForm_Edit(forms.ModelForm):

    class Meta:
        model = Escalation
        fields = "__all__"
        widgets = {
            'status':  forms.HiddenInput(),
            'assigned_dt':  forms.HiddenInput(),
            'request_level': Select(attrs={ 'value': 'Select Option'}),
            'request_reason':  forms.HiddenInput(),
            'priority':forms.HiddenInput(),
            'submission_person_name':  forms.HiddenInput(),
            }
        labels = {
        "request_id": _("Smartpath Original Request ID*"),
        "escalation_ticket_no":_("Smartpath Escalation Request ID*"),
        "request_level": _("Reason for request*"),
        "submission_person_name": _("Submitter name"),        
    }

    def clean(self):
        accessToken = BackgroundClass.get_token()
        request_list = get_request(self.cleaned_data["request_id"], accessToken)
        if request_exists(self.cleaned_data["request_id"], request_list)==False:
            raise forms.ValidationError(_("Request Not Found"))
        
import datetime
from django.utils.timezone import utc
# Register the Escalation model with custom admin behavior
@admin.register(Escalation)
class PersonAdmin(admin.ModelAdmin):
    view_on_site = True
    model = Escalation

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.user.username[0].upper() != "J":
            if "delete_selected" in actions:
                del actions["delete_selected"]
        return actions
 
    change_form_template = "admin/custom_change_form.html" 

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.form = PersonAdminForm_Edit
        else:
            self.form = PersonAdminForm
        return super(PersonAdmin, self).get_form(request, obj, **kwargs)

    def render_change_form(self, request, context, add=True, change=True, form_url='', obj=None):
        context.update({
            'show_save': False,
            'show_save_and_continue': False,
            'show_save_and_add_another': True,
            'show_close': False, 
            'custom_button': True,
            'show_delete_link and original':False,
            'show_save_as_new':False,
        })
        return super().render_change_form(request, context, add, change, form_url, obj)
    # Custom logic to save a model with additional attributes
    def save_model(self, request, obj, form, change):
        # Update submission_person_name with the logged-in user's username
        obj.submission_person_name = str(request.user)

        # Check and set priority if it's not set
        if not obj.priority:
            # Your logic for setting priority based on request level
            if obj.request_level == 'R1':
                obj.priority = 1
            elif obj.request_level == 'R2':
                obj.priority = 1
            elif obj.request_level == 'R3':
                obj.priority = 2

        # Save the model
        super().save_model(request, obj, form, change)


# Customize the User model's admin interface
from django.contrib.auth import get_user_model
from copy import deepcopy
from django.contrib.auth.admin import UserAdmin 
from django.contrib.auth.models import User
class UserAdmin(UserAdmin):

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(UserAdmin, self).get_fieldsets(request, obj)
        if not obj:
            return fieldsets
        # Remove 'is_superuser' field for non-superusers or if editing their own profile
        if not request.user.is_superuser or request.user.pk == obj.pk:
            fieldsets = deepcopy(fieldsets)
            for fieldset in fieldsets:
                if 'is_superuser' in fieldset[1]['fields']:
                    if type(fieldset[1]['fields']) == tuple :
                        fieldset[1]['fields'] = list(fieldset[1]['fields'])
                    fieldset[1]['fields'].remove('is_superuser')
                    break

        return fieldsets

# Unregister default User admin and register the customized UserAdmin
User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
