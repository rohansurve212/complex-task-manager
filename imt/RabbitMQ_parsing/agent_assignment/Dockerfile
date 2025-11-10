FROM python:3.10-slim-bullseye

# Proxy variables
ENV HTTP_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV HTTPS_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV http_proxy="http://fastwebwss-pac.int.bell.ca:8083"
ENV https_proxy="http://fastwebwss-pac.int.bell.ca:8083"

# Set timezone
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Toronto

# Install softwares
RUN apt update && apt install -y curl gnupg unixodbc-dev libgssapi-krb5-2 g++ libsasl2-dev python3-dev libldap2-dev libssl-dev && rm -rf /var/lib/apt/lists/*
RUN curl -k https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl -k https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN exit
RUN apt update
RUN ACCEPT_EULA=Y apt-get install -y mssql-tools18
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
RUN echo '/bin/bash source ~/.bashrc'

# Install python modules
COPY imt/RabbitMQ_parsing/agent_assignment/requirements.txt /requirements.txt
RUN python -m pip install -r requirements.txt --upgrade

# Add CA Certificates
# First, create a directory for the certificates
RUN mkdir -p /etc/ssl/cacerts/custom

# Copy the CA certificates into the container
COPY imt/RabbitMQ_parsing/agent_assignment/cacerts/BellIssuingCA8.cer /etc/ssl/cacerts/custom/
COPY imt/RabbitMQ_parsing/agent_assignment/cacerts/BellIssuingCA10.cer /etc/ssl/cacerts/custom/
COPY imt/RabbitMQ_parsing/agent_assignment/cacerts/BellRootCA1.cer /etc/ssl/cacerts/custom/

# Combine the certificates into a single bundle
RUN cat /etc/ssl/cacerts/custom/BellIssuingCA8.cer /etc/ssl/cacerts/custom/BellIssuingCA10.cer /etc/ssl/cacerts/custom/BellRootCA1.cer > /etc/ssl/cacerts/custom/ca_bundle.pem

# Copy the shared folder into the image
COPY shared /shared

# Set the PYTHONPATH to include the shared directory
ENV PYTHONPATH=/shared:$PYTHONPATH

# Add files
COPY imt/RabbitMQ_parsing/agent_assignment/parsing_agent_skills.py /
COPY imt/RabbitMQ_parsing/agent_assignment/rmq_consume_agent_skills.py /
COPY imt/RabbitMQ_parsing/agent_assignment/rmq.sh /

# Config
RUN chmod +x /parsing_agent_skills.py 
RUN chmod +x /rmq_consume_agent_skills.py 
RUN chmod +x /rmq.sh
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV http_proxy=""
ENV https_proxy=""

ENTRYPOINT /rmq.sh