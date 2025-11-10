# Import necessary modules from Django
from django.contrib import admin
from django.urls import path,include
from django.contrib import admin
from django.urls import path, include
from STM import views as view


# URL patterns defining different routes and corresponding views
urlpatterns = [
    path('', view.table1, name='table1'),
    path('STM/', view.table1, name='table1'),
    path('jsonresponse/footballclubs', view.footballclubs, name='footballclubs'),
    path('export_csv', view.export_csv, name='exportcsv')

]