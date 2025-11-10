from django.utils import translation
from django.http import HttpResponseRedirect
from django.shortcuts import redirect

LANGUAGE_SESSION_KEY = '_language'

# def redirect_view(request):
#     response = redirect('STM/')
#     return response

# def set_language_from_url(request, user_language):
#     translation.activate(user_language)
#     request.session[LANGUAGE_SESSION_KEY] = user_language
#     # I use HTTP_REFERER to direct them back to previous path 
#     return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import activate
from django.contrib import admin

def redirect_view(request):
    current_language = request.LANGUAGE_CODE
    activate(current_language)
    #activate(current_language)

    # Get the current domain from the request
    current_domain = request.get_host()

    # Check if the current path is an admin URL with language prefix
    if 'admin' in request.path:
        if 'en' in request.path:
            admin.site.site_url = f'http://{current_domain}/en/'
            return HttpResponseRedirect(f'http://{current_domain}/en/admin/STM')

    # Check if the current path is a regular URL with language prefix
        elif 'fr' in request.path:
            admin.site.site_url = f'http://{current_domain}/fr/'
            return HttpResponseRedirect(f'http://{current_domain}/fr/admin/STM')
    else:
        if 'en' in request.path:
            admin.site.site_url = f'http://{current_domain}/en/'
            return HttpResponseRedirect(f'http://{current_domain}/en')

    # Check if the current path is a regular URL with language prefix
        elif 'fr' in request.path:
            admin.site.site_url = f'http://{current_domain}/fr/'
            return HttpResponseRedirect(f'http://{current_domain}/fr')

    # Default redirection for other cases


#     # Additional logic if needed
