USE bbm_stm;

-- --- UAT  ---

-- DROP TABLE IF EXISTS dbo.uat_getwork_results;

-- CREATE TABLE dbo.uat_getwork_results (
--     id INT IDENTITY(1,1) PRIMARY KEY,
--     agent_id NVARCHAR(100),
--     request_id NVARCHAR(100),
--     work_status NVARCHAR(50),
--     orderdate DATETIME,
--     ttpu INT,
--     priority_score DECIMAL(10,5),
--     assign_date DATETIME,
--     skill_id NVARCHAR(100),
--     skill_name NVARCHAR(100),      
--     correlation_id NVARCHAR(100),
--     tenant NVARCHAR(100),
--     from_absent_agent NVARCHAR(5) CHECK (from_absent_agent IN ('True', 'False')),
--     request_source NVARCHAR(100),           
--     product NVARCHAR(100),                  
--     service_region NVARCHAR(100),
--     request_type NVARCHAR(100),             
--     customer_support_model NVARCHAR(100),   
--     control_desk NVARCHAR(100),             
--     golden_customer NVARCHAR(100),         
--     customer_market_segment NVARCHAR(100),  
--     preferred_language NVARCHAR(10),       
--     referred_type NVARCHAR(100),
--     request_status NVARCHAR(100),
--     request_assignee NVARCHAR(100),
--     global_latency DECIMAL(10,2),
--     smartpath_latency DECIMAL(10,2),
--     stm_latency DECIMAL(10,2),
--     followup_date DATE,               
-- );


--- PROD  ---

DROP TABLE IF EXISTS dbo.getwork_results;

CREATE TABLE dbo.getwork_results (
    id INT IDENTITY(1,1) PRIMARY KEY,
    agent_id NVARCHAR(100),
    request_id NVARCHAR(100),
    work_status NVARCHAR(50),
    orderdate DATETIME,
    ttpu DECIMAL(10,2),
    priority_score DECIMAL(10,5),
    assign_date DATETIME,
    skill_id NVARCHAR(100),
    skill_name NVARCHAR(100),      
    correlation_id NVARCHAR(100),
    tenant NVARCHAR(100),
    from_absent_agent NVARCHAR(5) CHECK (from_absent_agent IN ('True', 'False')),
    request_source NVARCHAR(100),           
    product NVARCHAR(100),                  
    service_region NVARCHAR(100),
    request_type NVARCHAR(100),             
    customer_support_model NVARCHAR(100),   
    control_desk NVARCHAR(100),             
    golden_customer NVARCHAR(100),         
    customer_market_segment NVARCHAR(100),  
    preferred_language NVARCHAR(10),       
    referred_type NVARCHAR(100),
    request_status NVARCHAR(100),
    request_assignee NVARCHAR(100),
    global_latency DECIMAL(10,2),
    smartpath_latency DECIMAL(10,2),
    stm_latency DECIMAL(10,2)--,
    --  followup_date DATE,               
);