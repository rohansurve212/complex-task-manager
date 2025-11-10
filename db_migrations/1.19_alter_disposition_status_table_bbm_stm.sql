--- UAT  ---

USE bbm_stm;
GO

ALTER TABLE dbo.uat_disposition_status
ADD last_updated DATETIME NULL;
GO

--- PROD  ---

USE bbm_stm;
GO

ALTER TABLE dbo.disposition_status
ADD last_updated DATETIME NULL;
GO
