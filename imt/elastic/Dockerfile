FROM ubuntu:20.04

# Set timezone
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Toronto
ENV http_proxy http://fastwebwss-pac.int.bell.ca:8083
ENV https_proxy http://fastwebwss-pac.int.bell.ca:8083

# Install softwares
RUN apt update && apt install -y curl cron tzdata unixodbc-dev python3 python3-pip python3-dev libldap2-dev libsasl2-dev libssl-dev python-is-python3 
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt update && ACCEPT_EULA=Y apt-get install -y msodbcsql18
RUN apt update && ACCEPT_EULA=Y apt-get install -y mssql-tools18
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc

# Install python modules
RUN pip install pip wheel setuptools pyodbc elasticsearch pandas requests python-dotenv --upgrade

# Copy the shared folder into the image
COPY shared /shared

# Set the PYTHONPATH to include the shared directory
ENV PYTHONPATH=/shared:$PYTHONPATH

# Add files
ADD imt/elastic/elastic_utils.py /elastic_utils.py
ADD imt/elastic/entrypoint.sh /entrypoint.sh
ADD imt/elastic/elastic_index.sh /elastic_index.sh
ADD imt/elastic/elastic_api_index.py /elastic_api_index.py
ADD imt/elastic/elastic_settings.py /elastic_settings.py

# System config
RUN chmod +x /entrypoint.sh
RUN chmod +x /elastic_index.sh
RUN chmod +x /elastic_api_index.py
RUN chmod +x /elastic_settings.py

# Proxy variables
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV http_proxy=""
ENV https_proxy=""

ENTRYPOINT /entrypoint.sh