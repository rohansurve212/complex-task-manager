FROM ubuntu:20.04

# Proxy variables
ENV HTTP_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV HTTPS_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV http_proxy="http://fastwebwss-pac.int.bell.ca:8083"
ENV https_proxy="http://fastwebwss-pac.int.bell.ca:8083"

# Set timezone
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Toronto

# Install softwares
RUN apt update && apt install -y curl cron tzdata python3 python3-pip python3-dev libldap2-dev libsasl2-dev libssl-dev python-is-python3 unixodbc-dev nano
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt update && ACCEPT_EULA=Y apt-get install -y msodbcsql18
RUN apt update && ACCEPT_EULA=Y apt-get install -y mssql-tools18
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc

# Install python modules
ADD imt/Agent_Proficiency/requirements.txt /requirements.txt
RUN pip install -r requirements.txt --upgrade

# Copy the shared folder into the image
COPY shared /shared

# Set the PYTHONPATH to include the shared directory
ENV PYTHONPATH=/shared:$PYTHONPATH

# Add files
ADD imt/Agent_Proficiency/agent_prof_entrypoint.sh /agent_prof_entrypoint.sh
ADD imt/Agent_Proficiency/agent_prof_prod_db.sh /agent_prof_prod_db.sh
ADD imt/Agent_Proficiency/agent_prof_prod_db.py /agent_prof_prod_db.py

# System config
RUN chmod +x /agent_prof_entrypoint.sh 
RUN chmod +x /agent_prof_prod_db.sh
RUN chmod +x /agent_prof_prod_db.py

# Proxy variables
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV http_proxy=""
ENV https_proxy=""

ENTRYPOINT /agent_prof_entrypoint.sh
