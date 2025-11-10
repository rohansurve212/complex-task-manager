USE bbm_stm;

--- UAT ---

DROP TABLE IF EXISTS dbo.uat_push_model_agents;

CREATE TABLE dbo.uat_push_model_agents (
  id INT IDENTITY(1,1) PRIMARY KEY,
  agent_id NVARCHAR(100),
);

--- PROD ---

DROP TABLE IF EXISTS dbo.push_model_agents;

CREATE TABLE dbo.push_model_agents (
  id INT IDENTITY(1,1) PRIMARY KEY,
  agent_id NVARCHAR(100),
);