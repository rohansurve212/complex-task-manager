USE bbm_stm

--- UAT  ---

DROP TABLE IF EXISTS dbo.uat_foc_targets
DROP TABLE IF EXISTS dbo.uat_proficiency
DROP TABLE IF EXISTS dbo.uat_dim_flow
DROP TABLE IF EXISTS dbo.uat_disposition_status
DROP TABLE IF EXISTS dbo.uat_permission_agent
DROP TABLE IF EXISTS dbo.uat_skill_action_category
DROP TABLE IF EXISTS dbo.uat_skill_gold_customer
DROP TABLE IF EXISTS dbo.uat_skill_tag
DROP TABLE IF EXISTS dbo.uat_skill_service_name
DROP TABLE IF EXISTS dbo.uat_skill_support_model
DROP TABLE IF EXISTS dbo.uat_skill_control_desk
DROP TABLE IF EXISTS dbo.uat_skill_pref_languages
DROP TABLE IF EXISTS dbo.uat_skill_market_segment
DROP TABLE IF EXISTS dbo.uat_skill_service_region
DROP TABLE IF EXISTS dbo.uat_skill_request_source
DROP TABLE IF EXISTS dbo.uat_skill_agent_priority
DROP TABLE IF EXISTS dbo.uat_skill_config
DROP TABLE IF EXISTS dbo.uat_agent
GO

-- ref: creating_db.py

-- tables without FK

CREATE TABLE dbo.uat_agent (
	agent_id VARCHAR(255) NOT NULL PRIMARY KEY,
	pein VARCHAR(255),
	full_name VARCHAR(255)
);

CREATE TABLE dbo.uat_skill_config (
	skill_id VARCHAR(255) NOT NULL PRIMARY KEY,
	skill_name VARCHAR(255),
	skill_distribution VARCHAR(255),
	skill_status VARCHAR(255),
);

-- tables with FK

CREATE TABLE dbo.uat_skill_agent_priority (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_agent(agent_id),
	skill_id VARCHAR(255) NOT NULL,
	CONSTRAINT pk_s_UAT_agent_priority PRIMARY KEY (agent_id,skill_id)
);

CREATE TABLE dbo.uat_skill_request_source (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	r_source VARCHAR(255),
	CONSTRAINT pk_s_UAT_request_source PRIMARY KEY (skill_id,r_source)
);

CREATE TABLE dbo.uat_skill_service_region (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	s_region VARCHAR(255),
	CONSTRAINT pk_s_UAT_service_region PRIMARY KEY (skill_id,s_region)
);

CREATE TABLE dbo.uat_skill_market_segment (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	m_segment VARCHAR(255),
	CONSTRAINT pk_s_UAT_market_segment PRIMARY KEY (skill_id,m_segment)
);

CREATE TABLE dbo.uat_skill_pref_languages (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	p_language VARCHAR(255),
	CONSTRAINT pk_s_UAT_pref_languages PRIMARY KEY (skill_id,p_language)
);

CREATE TABLE dbo.uat_skill_control_desk (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	c_desk VARCHAR(255),
	CONSTRAINT pk_s_UAT_control_desk PRIMARY KEY (skill_id,c_desk)
);

CREATE TABLE dbo.uat_skill_support_model (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	s_model VARCHAR(255),
	CONSTRAINT pk_s_UAT_support_model PRIMARY KEY (skill_id,s_model)
);

CREATE TABLE dbo.uat_skill_service_name (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	s_name VARCHAR(255),
	CONSTRAINT pk_s_UAT_service_name PRIMARY KEY (skill_id,s_name)
);

CREATE TABLE dbo.uat_skill_tag (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	s_tag VARCHAR(255),
	CONSTRAINT pk_s_UAT_tag PRIMARY KEY (skill_id,s_tag)
);

CREATE TABLE dbo.uat_skill_gold_customer (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	g_customer VARCHAR(255),
	CONSTRAINT pk_s_UAT_gold_customer PRIMARY KEY (skill_id,g_customer)
);

CREATE TABLE dbo.uat_skill_action_category (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_skill_config(skill_id),
	a_category VARCHAR(255),
	CONSTRAINT pk_s_UAT_action_category PRIMARY KEY (skill_id,a_category)
);

CREATE TABLE dbo.uat_permission_agent (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_agent(agent_id),
	permission VARCHAR(255),
	CONSTRAINT pk_uat_permission_agent PRIMARY KEY (agent_id,permission)
);

CREATE TABLE dbo.uat_disposition_status (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_agent(agent_id),
	status VARCHAR(255),
	CONSTRAINT pk_uat_disposition_status PRIMARY KEY (agent_id,status)
);

-- ref: creating_proficiency.py

CREATE TABLE dbo.uat_dim_flow (
	flow_id INT NOT NULL PRIMARY KEY,
	request_source VARCHAR(255),
	customer_support_model VARCHAR(255),
	request_type VARCHAR(255),
	foc_target INT
);

CREATE TABLE dbo.uat_proficiency (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.uat_agent(agent_id),
	flow_id INT FOREIGN KEY REFERENCES dbo.uat_dim_flow(flow_id),
	proficiency_mean REAL,
	proficiency_count REAL,
	flow_average REAL,
	rel_proficiency REAL,
	CONSTRAINT pk_uat_proficiency PRIMARY KEY (agent_id,flow_id)
);

-- ref: creating_foc_target.py

CREATE TABLE dbo.uat_foc_targets (
	foc_id INT IDENTITY(1,1) PRIMARY KEY,
	request_source VARCHAR(255),
	product VARCHAR(255),
	service_region VARCHAR(255),
	request_type VARCHAR(255),
	foc_target INT,
);

--- PROD ---

DROP TABLE IF EXISTS dbo.foc_targets
DROP TABLE IF EXISTS dbo.proficiency
DROP TABLE IF EXISTS dbo.dim_flow
DROP TABLE IF EXISTS dbo.disposition_status
DROP TABLE IF EXISTS dbo.skill_action_category
DROP TABLE IF EXISTS dbo.skill_gold_customer
DROP TABLE IF EXISTS dbo.skill_tag
DROP TABLE IF EXISTS dbo.skill_service_name
DROP TABLE IF EXISTS dbo.skill_support_model
DROP TABLE IF EXISTS dbo.skill_control_desk
DROP TABLE IF EXISTS dbo.skill_pref_languages
DROP TABLE IF EXISTS dbo.skill_market_segment
DROP TABLE IF EXISTS dbo.skill_service_region
DROP TABLE IF EXISTS dbo.skill_request_source
DROP TABLE IF EXISTS dbo.skill_agent_priority
DROP TABLE IF EXISTS dbo.skill_config
DROP TABLE IF EXISTS dbo.agent
GO

-- ref: creating_db.py

-- tables without FK

CREATE TABLE dbo.agent (
	agent_id VARCHAR(255) NOT NULL PRIMARY KEY,
	pein VARCHAR(255),
	full_name VARCHAR(255)
);

CREATE TABLE dbo.skill_config (
	skill_id VARCHAR(255) NOT NULL PRIMARY KEY,
	skill_name VARCHAR(255),
	skill_distribution VARCHAR(255),
	skill_status VARCHAR(255),
);

-- tables with FK

CREATE TABLE dbo.skill_agent_priority (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.agent(agent_id),
	skill_id VARCHAR(255) NOT NULL,
	CONSTRAINT pk_s_agent_priority PRIMARY KEY (agent_id,skill_id)
);

CREATE TABLE dbo.skill_request_source (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	r_source VARCHAR(255),
	CONSTRAINT pk_s_request_source PRIMARY KEY (skill_id,r_source)
);

CREATE TABLE dbo.skill_service_region (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	s_region VARCHAR(255),
	CONSTRAINT pk_s_service_region PRIMARY KEY (skill_id,s_region)
);

CREATE TABLE dbo.skill_market_segment (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	m_segment VARCHAR(255),
	CONSTRAINT pk_s_market_segment PRIMARY KEY (skill_id,m_segment)
);

CREATE TABLE dbo.skill_pref_languages (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	p_language VARCHAR(255),
	CONSTRAINT pk_s_pref_languages PRIMARY KEY (skill_id,p_language)
);

CREATE TABLE dbo.skill_control_desk (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	c_desk VARCHAR(255),
	CONSTRAINT pk_s_control_desk PRIMARY KEY (skill_id,c_desk)
);

CREATE TABLE dbo.skill_support_model (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	s_model VARCHAR(255),
	CONSTRAINT pk_s_support_model PRIMARY KEY (skill_id,s_model)
);

CREATE TABLE dbo.skill_service_name (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	s_name VARCHAR(255),
	CONSTRAINT pk_s_service_name PRIMARY KEY (skill_id,s_name)
);

CREATE TABLE dbo.skill_tag (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	s_tag VARCHAR(255),
	CONSTRAINT pk_s_tag PRIMARY KEY (skill_id,s_tag)
);

CREATE TABLE dbo.skill_gold_customer (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	g_customer VARCHAR(255),
	CONSTRAINT pk_s_gold_customer PRIMARY KEY (skill_id,g_customer)
);

CREATE TABLE dbo.skill_action_category (
	skill_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.skill_config(skill_id),
	a_category VARCHAR(255),
	CONSTRAINT pk_s_action_category PRIMARY KEY (skill_id,a_category)
);

CREATE TABLE dbo.permission_agent (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.agent(agent_id),
	permission VARCHAR(255),
	CONSTRAINT pk_permission_agent PRIMARY KEY (agent_id,permission)
);

CREATE TABLE dbo.disposition_status (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.agent(agent_id),
	status VARCHAR(255),
	CONSTRAINT pk_disposition_status PRIMARY KEY (agent_id,status)
);

-- ref: creating_proficiency.py

CREATE TABLE dbo.dim_flow (
	flow_id INT NOT NULL PRIMARY KEY,
	request_source VARCHAR(255),
	customer_support_model VARCHAR(255),
	request_type VARCHAR(255),
	foc_target INT
);

CREATE TABLE dbo.proficiency (
	agent_id VARCHAR(255) FOREIGN KEY REFERENCES dbo.agent(agent_id),
	flow_id INT FOREIGN KEY REFERENCES dbo.dim_flow(flow_id),
	proficiency_mean REAL,
	proficiency_count REAL,
	flow_average REAL,
	rel_proficiency REAL,
	CONSTRAINT pk_proficiency PRIMARY KEY (agent_id,flow_id)
);

-- ref: creating_foc_target.py

CREATE TABLE dbo.foc_targets (
	foc_id INT IDENTITY(1,1) PRIMARY KEY,
	request_source VARCHAR(255),
	product VARCHAR(255),
	service_region VARCHAR(255),
	request_type VARCHAR(255),
	foc_target INT,
);
