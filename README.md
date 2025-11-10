# STM - Smart Task Management

## Goal 
Construct a routing algorithm and develop staffing and scheduling strategies in SmartPath in order to meet opex, revenue and customer satisfaction objectives while ensuring that 90% of the requests meet their FOC/SLA targets. 

### Links
* [Confluence](https://confluence.wnst.int.bell.ca/display/STMS/Smart+Task+Management+%28STM%29+Home)
* [JIRA](https://jira.wnst.int.bell.ca/projects/STMS/summary)

#### STM Services

The `docker-compose` files are the starting points for understanding the code structure. More information is also available on Confluence.  

- **imt/Agent_Proficiency**: Update agent proficiency tables once a day by quering BI reporting tables. 

- **imt/RabbitMQ_parsing**: Consume RabbitMQ messages from Smartpath, about skillset assignments, skillset configurations and disposition codes.

- **imt/db_init**: Scripts used in the initialisation of SQL tables before launch. Run [initialize_db_skill_agent_v2.py](imt/db_init/initialize_db_skill_agent_v2.py) and [initialize_db_skill_config_v2.py](imt/db_init/initialize_db_skill_config_v2.py) to update the agent and skill tables. Before running the above two scripts, login to SmartPath tool in the browser using your credentials and open Developer tools. Click on Network tab and go to the smartpath/ request. Go to the Headers tab and scroll down to see the "Cookie" field. Copy the value for this field and paste it as the value for `Cookie` field in the headers object in `get_all_skills_config()` function definition in `imt/db_init/initialize_db_skill_config_v2.py` file and the headers object in `get_all_agent_assignment()` function definition in `imt/db_init/initialize_db_skill_agent_v2.py` file.

- **imt/db_init/create_foc_target_v2.py**: This creates the new foc targets in PROD in dbo.foc_targets table. It takes the value from the csv that starts with `ttpu_targets_`. To complete the steps:
1. Check the csv file and make sure that it is mapped correctly in `create_foc_target_v2.py`.
2. Run the database removal and addition SQL Query for foc_target data. the query is:
```
USE bbm_stm
DROP TABLE IF EXISTS dbo.foc_targets


CREATE TABLE dbo.foc_targets (
	foc_id INT IDENTITY(1,1) PRIMARY KEY,
	request_source VARCHAR(255),
	product VARCHAR(255),
	service_region VARCHAR(255),
	request_type VARCHAR(255),
	foc_target INT,
);
GO
```

3. Run the `create_foc_target_v2.py` file after you check and make sure the `.env` has the right environment and values.

4. Update the docker image versions and restart the containers on the respective server (X or V depending on Environment) after pushing the changes to git.

- **imt/elastic**: Query Smartpath API every 3 seconds to get updated data on requests in Smartpath. 

- **imt/ldap**: Query LDAP every day to obtain agents partitions. Run gofish-ldap.py file to update the agent permissions.

- **stm-api**: Routing API
- **imt/db_init**: Scripts used in the initialisation of SQL tables before launch. Run [initialize_db_skill_agent_v2.py](imt/db_init/initialize_db_skill_agent_v2.py) and [initialize_db_skill_config_v2.py](imt/db_init/initialize_db_skill_config_v2.py) to update the agent and skill tables. Before running the above two scripts, login to SmartPath tool in the browser using your credentials and open Developer tools. Click on Network tab and go to the smartpath/ request. Go to the Headers tab and scroll down to see the "Cookie" field. Copy the value for this field and paste it as the value for `Cookie` field in the headers object in `get_all_skills_config()` function definition in `imt/db_init/initialize_db_skill_config_v2.py` file and the headers object in `get_all_agent_assignment()` function definition in `imt/db_init/initialize_db_skill_agent_v2.py` file.

- **imt/db_init/create_foc_target_v2.py**: This creates the new foc targets in PROD in dbo.foc_targets table. It takes the value from the csv that starts with `ttpu_targets_`. To complete the steps:
1. Check the csv file and make sure that it is mapped correctly in `create_foc_target_v2.py`.
2. Run the database removal and addition SQL Query for foc_target data. the query is:
```
USE bbm_stm
DROP TABLE IF EXISTS dbo.foc_targets


CREATE TABLE dbo.foc_targets (
	foc_id INT IDENTITY(1,1) PRIMARY KEY,
	request_source VARCHAR(255),
	product VARCHAR(255),
	service_region VARCHAR(255),
	request_type VARCHAR(255),
	foc_target INT,
);
GO
```

3. Run the `create_foc_target_v2.py` file after you check and make sure the `.env` has the right environment and values.

4. Update the docker image versions and restart the containers on the respective server (X or V depending on Environment) after pushing the changes to git.

- **imt/elastic**: Query Smartpath API every 3 seconds to get updated data on requests in Smartpath. 

- **imt/ldap**: Query LDAP every day to obtain agents partitions. Run gofish-ldap.py file to update the agent permissions.

- **stm-api**: Routing API
- **stm-api/app/Elastic**: Scripts used to update Elastic database. Run [elastic_api_index.py](stm-api/app/Elastic/elastic_api_index.py) to update Requests in Elastic DB.
- **getWork** :  Getwork starts  with stm-api/main.py. Follow that and also check stm-api/app/api.py and the logic lies in stm-api/app/GetWorkFlow/ and elastic logic is in stm-api/app/Elastic/
![Alt text](STM-diagram.png)
## Branches

Although this has not always been the case, the current branching model follows [this](https://nvie.com/posts/a-successful-git-branching-model/). The only exception to this rule is documentation, which was mosty updated directly in master. As of 08/05/22, code documentation, however, is most updated in the feature branch escalation. Moreover, we started recently to create release tags. Although not necessary, we decided to keep uat_1.0 and prod_1.1 branches alive. Those are the scripts in production as of 08/05/22. 

## Deployment

Go to the README file in the stm-api for information about how to deploy stm. 

- **docker-compose-prod.yml**: make sure to update the versions everytime you restart and rebuild the docker containers. 
                               Follow the steps below:
                               1. `docker-compose -f docker-compose-prod.yml down`
                               1 run `cat -n docker-compose-prod.yml` to confirm that the images have newer versions.
                               2. `docker-compose -f docker-compose-prod.yml up --force-recreate` to create the new versions of the images and deploy on the server

## RabbitMQ
RabbitMQ is a message queues service.

### Host
* In Production, the service can be reached at :
    - **Message queues** : dc6cgv.qc.bell.ca:5672
    - **UI Management** : http://dc6cgv.qc.bell.ca:15672/#/ 
* In UAT, the service can be reached at:
    - **Message queues** : dc6cgv.qc.bell.ca:5673
    - **UI Management** : http://dc6cgv.qc.bell.ca:15673/#/

### Queues
* Disposition codes
* Skillsets assignment
* Skillsets configuration

### Access
* Smartpath was provided `uat-publisher` and `prod-publisher` access. 
* STM is using a `uat-consumer` and `prod-consumer` access.
* STM project owners have a `uat-admin` and `prod-admin` acess.

### Links
* [Official web site](https://www.rabbitmq.com/)
* [Docker image](https://hub.docker.com/_/rabbitmq)


## Deployment

### To deploy a HotFix to Production

1. Create a new HotFix branch from the /master branch and make the hotfix.
2. Test the HotFix branch on UAT server by following the below sub-steps
	1. Go to /home/aiml/projects/stm folder 
	2. Change the tracking branch to your hotfix branch by running ```sudo git checkout -t origin/<hotfix_branch_name>```
	3. Restart the STM application on UAT server using the commands listed in the UAT section. 
	4. Make sure the hotfix works as expected on UAT
3. Update the image versions in both docker-compose-dev.yml and docker-compose-prod.yml files on the hotfix branch.
4. Create a Merge Request from hotfix branch to /master. Make sure to uncheck "delete branch" option.
5. Once approved, do the merge.
6. Go to Prod server, do manual git pull and restart the STM application using the commands listed in the PROD section below.
7. Check Portainer to make sure all STM containers are running fine.
8. Check the RabbitMQ server dashboard on the browser to make sure all the three connections are running and channels are receiving messages.
9. Check all the different logs on the server to make sure there are no errors in the logs.
10. Create a Merge Request from hotfix branch to /develop. Make sure to check "delete branch" option.
11. Go to UAT server and restore the tracking branch back to /develop by running ```sudo git checkout develop```
12. Restart the STM application on UAT server using the commands listed in the UAT section below.

### To deploy a RC (Release Candidate) to Production

1. Create a new feature branch using the following naming convention: "<ticket_no>-<ticket_description>" and make the required changes.
2. Test the feature branch on UAT server by following the below sub-steps.
	1. Go to /home/aiml/projects/stm folder.
	2. Change the tracking branch to your feature branch by running ```sudo git checkout -t origin/<feature_branch_name>```.
	3. Restart the STM application on UAT server using the commands listed in the UAT section.
	4. Make sure the code works as expected on UAT.
3. Create a Merge Request from the feature branch to /develop. Make sure to check "delete branch" option.
4. Once approved, do the merge.
5. Create a new RC (Release Candidate) branch from the most updated develop branch using the naming convention: "RC_X.X"
6. Update the image versions in both docker-compose-dev.yml and docker-compose-prod.yml files.
7. Create a new Merge Request from RC branch to /master. Make sure to uncheck "delete branch" option.
8. Once approved, do the merge.
9. Go to PROD server, do manual git pull and restart the STM application using the commands listed in the PROD section below.
10. Check Portainer to make sure all STM containers are running fine.
11. Check the RabbitMQ server dashboard on the browser to make sure all the three connections are running and channels are receiving messages.
12. Check all the different logs on the server to make sure there are no errors in the logs.
13. Create a new Merge Request from RC branch to /develop. Make sure to check "delete branch" option.
14. Go to UAT server and restore the tracking branch back to /develop by running ```sudo git checkout develop```.
15. Restart the STM application on UAT server using the commands listed in the UAT section below.


### UAT

#### RabbitMQ

**To Deploy**
1. move to folder : `cd /home/aiml/projects/stm`
1. Update code : `sudo git pull`
1. Stop running container : `sudo docker-compose -f docker-compose-rabbit-dev.yml -p "stm-rabbit" down`
1. deploy : `sudo docker-compose -f docker-compose-rabbit-dev.yml -p "stm-rabbit" up -d`
    1. Validate if all services are running : <todo>

**To stop**

1. Stop running container : `sudo docker-compose -f docker-compose-rabbit-dev.yml -p "stm-rabbit" down`


#### Everything else

**To Deploy**
1. move to folder : `cd /home/aiml/projects/stm`
1. Update code : `sudo git pull`
1. Stop running container : `sudo docker-compose -f docker-compose-dev.yml -p "stm" down`
1. deploy : `sudo docker-compose -f docker-compose-dev.yml -p "stm" up -d --build`
    1. Validate if all services are running : <todo>

**To stop**

1. Stop running container : `sudo docker-compose -f docker-compose-dev.yml -p "stm" down`

### PROD

#### RabbitMQ

**To Deploy**
1. move to folder : `cd /home/aiml/projects/stm`
1. Update code : `sudo git pull`
1. Stop running container : `sudo docker-compose -f docker-compose-rabbit-prod.yml -p "stm-rabbit" down`
1. deploy : `sudo docker-compose -f docker-compose-rabbit-prod.yml -p "stm-rabbit" up -d`
    1. Validate if all services are running : <todo>

**To stop**

1. Stop running container : `sudo docker-compose -f docker-compose-rabbit-prod.yml -p "stm-rabbit" down`


#### Everything else

**To Deploy**
1. move to folder : `cd /home/aiml/projects/stm`
1. Update code : `sudo git pull`
1. Stop running container : `sudo docker-compose -f docker-compose-prod.yml -p "stm" down`
1. deploy : `sudo docker-compose -f docker-compose-prod.yml -p "stm" up -d --build`
    1. Validate if all services are running : <todo>

**To stop**

1. Stop running container : `sudo docker-compose -f docker-compose-prod.yml -p "stm" down`

### How to restart a single service from a docker compose file?
#### (The below command works when you have modifed the underlying docker image, if you haven't modified the docker image then check the next section)

#### UAT
Run the command `sudo docker-compose -f docker-compose-dev.yml up -d --build [service_name]`

#### PROD
Run the command `sudo docker-compose -f docker-compose-prod.yml up -d --build [service_name]`

### How to restart a single service from a docker compose file, when you haven't modified the docker image?

#### UAT
Run the below commands in the same order
1. `sudo docker-compose -f docker-compose-dev.yml stop [service_name]`
2. `sudo docker-compose -f docker-compose-dev.yml rm -f [service_name]`
3. `sudo docker-compose -f docker-compose-dev.yml up -d --build [service_name]`

#### PROD
Run the below commands in the same order
1. `sudo docker-compose -f docker-compose-prod.yml stop [service_name]`
2. `sudo docker-compose -f docker-compose-prod.yml rm -f [service_name]`
3. `sudo docker-compose -f docker-compose-prod.yml up -d --build [service_name]`