USE bbm_stm
GO

--- UAT  ---

-- DROP TABLE IF EXISTS [dbo].[uat_escalation]
-- GO

-- CREATE TABLE [dbo].[uat_escalation](
-- 	[escalation_id] [INT] IDENTITY(1,1) NOT NULL PRIMARY KEY,
-- 	[request_id] [VARCHAR](255) NOT NULL UNIQUE,
-- 	[priority] [INT] NOT NULL CONSTRAINT chk_priority_uat CHECK ([priority] IN (1,2)),
-- 	[agent_id] [VARCHAR](255) NULL,
-- 	[submission_dt] [DATETIME] NOT NULL DEFAULT (GETUTCDATE()),
-- 	[updated_dt] [DATETIME] NOT NULL DEFAULT (GETUTCDATE()),
-- 	[completed_dt] [DATETIME] NULL, 
-- 	[status] [VARCHAR](255) NOT NULL CONSTRAINT chk_status_uat CHECK ([status] IN ('open', 'completed', 'assigned'))
-- )
-- GO

-- CREATE TRIGGER tgr_escalation_updated_dt_uat
-- ON [dbo].[uat_escalation]
-- AFTER UPDATE AS
-- UPDATE [dbo].[uat_escalation]
-- SET [updated_dt] = GETUTCDATE()
-- WHERE [escalation_id] IN (SELECT DISTINCT [escalation_id] FROM INSERTED)
-- GO

--- PROD ---

DROP TABLE IF EXISTS [dbo].[escalation]
GO

CREATE TABLE [dbo].[escalation](
	[escalation_id] [INT] IDENTITY(1,1) NOT NULL PRIMARY KEY,
	[request_id] [VARCHAR](255) NOT NULL UNIQUE,\
	[escalation_ticket_no] [VARCHAR] (255) NOT NULL,
	[request_reason] [VARCHAR] (255) NULL,
	[request_level] [VARCHAR] (255) NULL,
	[priority] [INT] NOT NULL CONSTRAINT chk_priority_prod CHECK ([priority] IN (1,2)),
	[agent_id] [VARCHAR](255) NULL,
	[submission_dt] [DATETIME] NOT NULL DEFAULT (GETUTCDATE()),
	[status] [VARCHAR] (255) NOT NULL  CONSTRAINT chk_status_prod CHECK ([status] IN ('open', 'completed', 'assigned', 'REQ_NOT_FOUND', 'AGENT_NOT_FOUND', 'already in work')),
	[assigned_dt] [DATETIME] NULL, 
	[submission_person_name] [VARCHAR](255) NULL
)
GO

CREATE TRIGGER tgr_escalation_updated_dt_prod
ON [dbo].[escalation]
AFTER UPDATE AS
UPDATE [dbo].[escalation]
SET [updated_dt] = GETUTCDATE()
WHERE [escalation_id] IN (SELECT DISTINCT [escalation_id] FROM INSERTED)
GO