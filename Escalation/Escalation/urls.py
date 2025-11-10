"""
Escalation URL Configuration

The urlpatterns list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns  
from django.utils.translation import gettext_lazy as _  
from .views import redirect_view  

# Define language-aware URL patterns using i18n_patterns
urlpatterns = i18n_patterns(
    path('admin/', redirect_view),  
    path('admin/', admin.site.urls),  
    path('admin/view-site/', redirect_view, name='admin-view-site'), 
    path('', include('STM.urls')), 
)

# Add additional patterns for internationalization (language switching)
urlpatterns += [
    path("i18n/", include("django.conf.urls.i18n"))
]

# Customize admin panel headers and titles with translations
admin.site.site_header = _("SAiRA Internal Exception Tool  ") 
admin.site.site_title = _("SAiRA Internal Exception Tool ADMIN SITE") 
admin.site.index_title = _("SAiRA Internal Exception Tool ")