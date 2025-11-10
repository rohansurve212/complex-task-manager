## Debug

Follow this guide to debug the API.

NB: The first two steps are only for the first time or when a package change in Pipfile

1. Run pip install -r stm-api\requirements.txt
1. Go to main.py and press F5


# Start Docker locally

## Prerequisite

* Install [Docker](https://docs.docker.com/desktop/windows/install/)
* Enable the Virtualization in the Bios. (You need do request it to CGI)
* Install this extension (ms-azuretools.vscode-docker) into VSCode.

## Launch Docker

* Comment the four lines for proxy setup into all Dockerfile : ex `ENV HTTP_PROXY`
* (Optional) Comment all services you don't want to start into `docker-compose-dev.yml`
* Start `docker-compose-dev.yml`
    * Rigth click on `docker-compose-dev.yml` file
    * Click on `Compose Up`

# Deploy

STM is hosted on DC6CGV. The code is located in `/var/stm` (UAT) or `/var/stm-prod/` (PROD). Log files can be found in `/rawdata/stm-uat` (UAT) and `/rawdata/stm` (PROD). 

### Environment variables
Before deploying on Prod or Local machine an `.env` with needed variables should be create at the root of the project.

**Tips**: The file `.env-example` could be use as a starting point. It contains all needed variables but without values.

**NB**: It's very important to **never** include the `.env` file in the Git reposistory for **security** purpose.

**Obtaining credentials**: Please contact [Eric Goulet](mailto:eric.goulet@bell.ca) or [Stephanie-Ye Xia](mailto:stephanieye.xia@bell.ca).



## UAT

*Before launching a new version, update the image version in `docker-compose-uat.yml`*

* move to folder : `cd /var/stm/`
* Update source code : `sudo git pull`
* hack : edit prod version to add "-uat" in the image name : `sudo cp docker-compose-uat.yml docker-compose.yml`
* build image : `sudo docker-compose build`
    - To validate if the new images has been created, do : `sudo docker image ls`
* Update compose file for docker stack
    - change to sudo user : `sudo -i`
    - move to folder : `cd /var/stm/`
    - To create or after update .env file : `sudo docker-compose -f "./docker-compose-uat.yml" config > docker-stack-uat.yml`
    - exit sudo user : `exit`
* deploy : `sudo docker stack deploy -c docker-stack-uat.yml stm-uat`
    - Validate if all services are running : `http://dc6cgv.qc.bell.ca:9999/#!/1/docker/stacks/stm-uat?type=1&external=true`
* remove the hack : `sudo rm docker-compose.yml`

## Prod

*Before launching a new version, update the image version in `docker-compose-prod.yml`*

* move to folder : `cd /var/stm-prod/`
* Update source code : `sudo git pull`
* hack : edit prod version to add "-prod" in the image name : `sudo cp docker-compose-prod.yml docker-compose.yml`
* build image : `sudo docker-compose build`
    - To validate if the new images has been created, do : `sudo docker image ls`
* Update compose file for docker stack
    - change to sudo user : `sudo -i`
    - move to folder : `cd /var/stm-prod/`
    - To create or after update .env file : `sudo docker-compose -f "./docker-compose-prod.yml" config > docker-stack-prod.yml`
    - exit sudo user : `exit`
* Stop old version : `sudo docker stack remove stm`
* deploy : `sudo docker stack deploy -c docker-stack-prod.yml stm`
    - Validate if all services are running : `http://dc6cgv.qc.bell.ca:9999/#!/1/docker/stacks/stm?type=1&external=true`

## Rabbit

* move to folder : `cd /var/stm-prod/`
* Update compose file for docker stack
    - change to sudo user : `sudo -i`
    - move to folder : `cd /var/stm-prod/`
    - To create or after update .env file : `sudo docker-compose -f "./docker-compose-rabbit.yml" config > docker-stack-rabbit.yml`
    - exit sudo user : `exit`
* deploy : `sudo docker stack deploy -c docker-stack-rabbit.yml stm-rabbit`
    - Validate if all services are running : `http://dc6cgv.qc.bell.ca:9999/#!/1/docker/stacks/stm-rabbit?type=1&external=true`

# Stop

## UAT

* remove : `sudo docker stack remove stm-uat`

## Prod

* remove : `sudo docker stack remove stm`

## Rabbit

* remove : `sudo docker stack remove stm-rabbit`


# Initialize Elastic before launch 

1. use `stm-api/app/Elastic/initialize_elastic_index.py` for first initialization

2. if index is not created
    - choose `create_index=True` in smartpath_data_to_elastic_stm
    - In [Kibana](https://kibana-icn-paas-bali.apps.ocp-prd-wyn.bell.corp.bce.ca/app/home#/)
        - K on the top right;
        - Manage Kibana;
        - Index Pattern;
        - Choose right index and add lastUpdated as timestamp.

3. if index is created, choose `create_index=False`

4. for the first initialisation, choose `filter_comp=True`

5. keeping in mind the timestamp of the previous run, run the script multiple times until it is very quick, just before launch. In those iterations, choose `filter_comp=False` and `create=False` (if not already done)

# Update skills SQL tables before launch (data from RabbitMQ)

The strategy is to first launch RabbitMQ before launching Docker containers that consumme the messages. In between, we need to do an update of our SQL tables.

1. launch RabbitMQ using the procedure described above.

2. use `imt/db_init/initialize_db_skill_agent_v2.py` and `imt/db_init/initialize_db_skill_config_v2.py` to reinitialize tables.

3. Login to SmartPath tool in the browser using your credentials and open Developer tools. Click on Network tab and go to the smartpath/ request. Go to the Headers tab and scroll down to see the "Cookie" field. Copy the value for this field and paste it as the value for `Cookie` field in the headers object in `get_all_skills_config()` function definition in `imt/db_init/initialize_db_skill_config_v2.py` file and the headers object in `get_all_agent_assignment()` function definition in `imt/db_init/initialize_db_skill_agent_v2.py` file.

4. launch rmq containers using the procedure described above.
