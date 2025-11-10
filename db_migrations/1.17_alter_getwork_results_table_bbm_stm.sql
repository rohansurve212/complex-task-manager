--- UAT  ---


USE bbm_stm;
GO


ALTER TABLE dbo.uat_getwork_results
ADD is_escalated INT NULL;


ALTER TABLE dbo.uat_getwork_results
ADD has_sla INT NULL;


GO


--- PROD  ---


USE bbm_stm;
GO


ALTER TABLE dbo.getwork_results
ADD is_escalated INT NULL;


ALTER TABLE dbo.getwork_results
ADD has_sla INT NULL;


GO