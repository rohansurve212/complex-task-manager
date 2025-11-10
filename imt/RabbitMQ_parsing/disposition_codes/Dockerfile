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
RUN apt update && apt install -y curl gnupg unixodbc-dev libgssapi-krb5-2 g++
RUN curl -k https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl -k https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN exit
RUN apt update
RUN ACCEPT_EULA=Y apt-get install -y mssql-tools18
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
RUN echo '/bin/bash source ~/.bashrc'

# Install python modules
COPY imt/RabbitMQ_parsing/disposition_codes/requirements.txt /requirements.txt
RUN python -m pip install -r requirements.txt --upgrade

# Copy the shared folder into the image
COPY shared /shared

# Set the PYTHONPATH to include the shared directory
ENV PYTHONPATH=/shared:$PYTHONPATH

# Add files
COPY imt/RabbitMQ_parsing/disposition_codes/parsing_disposition_codes.py /
COPY imt/RabbitMQ_parsing/disposition_codes/rmq_consume_disposition_codes.py /
COPY imt/RabbitMQ_parsing/disposition_codes/rmq.sh /

# Config
RUN chmod +x /parsing_disposition_codes.py 
RUN chmod +x /rmq_consume_disposition_codes.py 
RUN chmod +x /rmq.sh
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV http_proxy=""
ENV https_proxy=""

ENTRYPOINT /rmq.sh