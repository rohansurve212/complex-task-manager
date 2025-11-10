FROM python:3.10.4
ENV PYTHONUNBUFFERED 1

# Proxy and environment variables
ENV HTTP_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV HTTPS_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV http_proxy="http://fastwebwss-pac.int.bell.ca:8083"
ENV https_proxy="http://fastwebwss-pac.int.bell.ca:8083"

# Install necessary packages
RUN apt-get update && apt-get install -y \
	unixodbc \
	unixodbc-dev \
	tdsodbc
RUN apt-get install -y freetds-common freetds-bin freetds-dev
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools \
    && apt-get -y install g++ \
		&& apt-get -y install gettext

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY Escalation/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt 
##RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy the shared folder into the image
COPY shared /app/shared

# Copy the current folder content into the image
COPY Escalation /app
RUN mkdir -p /app/log

# Set the PYTHONPATH to include the shared directory
ENV PYTHONPATH=/app/shared:$PYTHONPATH

# Compile French translations
RUN python manage.py compilemessages

# Command to run the Django server
CMD python /app/manage.py runserver 0.0.0.0:8002
