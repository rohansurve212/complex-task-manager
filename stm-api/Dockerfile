FROM python:3.10-slim-bullseye

# Proxy and environment variables
ENV HTTP_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV HTTPS_PROXY="http://fastwebwss-pac.int.bell.ca:8083"
ENV http_proxy="http://fastwebwss-pac.int.bell.ca:8083"
ENV https_proxy="http://fastwebwss-pac.int.bell.ca:8083"

# Set working directory
WORKDIR /app

# Install necessary packages
RUN apt-get -y update
RUN apt-get install -y unixodbc-dev curl gnupg libgssapi-krb5-2 g++
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN exit
RUN apt update
RUN ACCEPT_EULA=Y apt-get install -yqq mssql-tools18
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
RUN echo '/bin/bash source ~/.bashrc'
RUN apt-get -yqq install python3-pip
RUN apt update && apt install nano

# Copy and install Teradata ODBC driver
COPY stm-api/drivers/tdodbc1720__ubuntu_x8664.17.20.00.47-1.tar.gz /app/drivers/
RUN apt-get -y update --fix-missing 
RUN apt-get install -y lib32stdc++6 
RUN tar xvzf /app/drivers/tdodbc1720__ubuntu_x8664.17.20.00.47-1.tar.gz -C /app/drivers/ \
    && dpkg -i /app/drivers/tdodbc1720/tdodbc1720-17.20.00.47-1.x86_64.deb \
    && rm -rf /app/drivers/tdodbc1720 \
    && ls -l /opt/teradata/client/ODBC_64/lib

# Configure ODBC drivers
RUN echo "[ODBC Driver 18 for SQL Server]" > /etc/odbcinst.ini \
    && echo "Description=Microsoft ODBC Driver 18 for SQL Server" >> /etc/odbcinst.ini \
    && echo "Driver=/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.4.so.1.1" >> /etc/odbcinst.ini \
    && echo "[Teradata Database ODBC Driver 17.20]" >> /etc/odbcinst.ini \
    && echo "Description=Teradata ODBC Driver" >> /etc/odbcinst.ini \
    && echo "Driver=/opt/teradata/client/ODBC_64/lib/tdataodbc_sb64.so" >> /etc/odbcinst.ini

# Copy requirements and install Python packages
COPY stm-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the shared folder into the image
COPY shared /app/shared

# Copy the stm-api folder content into the image
COPY stm-api /app

# Set the PYTHONPATH to include the shared directory
ENV PYTHONPATH=/app/shared:$PYTHONPATH

# Clear proxy variables
ENV http_proxy=""
ENV https_proxy=""
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""

# Expose the port the app runs on
EXPOSE 8000

# Command to run the Uvicorn server
CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]