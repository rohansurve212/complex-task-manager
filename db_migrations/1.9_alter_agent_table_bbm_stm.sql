--- UAT  ---

USE bbm_stm;
GO

ALTER TABLE dbo.uat_agent
ADD is_absent NVARCHAR(5) NOT NULL CONSTRAINT DF_Default_IsAbsent DEFAULT 'False' CHECK (is_absent IN ('True', 'False'));
GO

--- PROD  ---

USE bbm_stm;
GO

ALTER TABLE dbo.agent
ADD is_absent NVARCHAR(5) NOT NULL CONSTRAINT DF_Default_IsAbsent DEFAULT 'False' CHECK (is_absent IN ('True', 'False'));
GO
