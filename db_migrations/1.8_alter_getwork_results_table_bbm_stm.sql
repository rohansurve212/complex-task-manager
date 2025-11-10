--- UAT  ---


USE bbm_stm;
GO


ALTER TABLE dbo.uat_getwork_results
ADD external_id NVARCHAR(100) NULL;


ALTER TABLE dbo.uat_getwork_results
ADD followup_date date NULL;


GO


--- PROD  ---


USE bbm_stm;
GO


ALTER TABLE dbo.getwork_results
ADD external_id NVARCHAR(100) NULL;


ALTER TABLE dbo.getwork_results
ADD followup_date date NULL;


GO