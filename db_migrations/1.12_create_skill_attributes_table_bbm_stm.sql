--- UAT ---

DROP TABLE IF EXISTS dbo.uat_skill_attributes

SELECT 
    c.skill_id, 
    c.skill_name,
	  cd.controlDesk,
    gc.goldenCustomer,
    ms.customerMarketSegment, 
    pl.preferredlanguage, 
    rs.requestSource, 
    sn.product, 
    sr.serviceRegion, 
    sm.customerSupportModel, 
    ac.requestType,
	  t.tag
INTO dbo.uat_skill_attributes
FROM dbo.uat_skill_config AS c
LEFT JOIN (
    SELECT skill_id, STRING_AGG(c_desk, ';') AS controlDesk
    FROM dbo.uat_skill_control_desk
    GROUP BY skill_id
) AS cd ON c.skill_id = cd.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(g_customer, ';') AS goldenCustomer
    FROM dbo.uat_skill_gold_customer
    GROUP BY skill_id
) AS gc ON c.skill_id = gc.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(m_segment, ';') AS customerMarketSegment
    FROM dbo.uat_skill_market_segment
    GROUP BY skill_id
) AS ms ON c.skill_id = ms.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(p_language, ';') AS preferredlanguage
    FROM dbo.uat_skill_pref_languages
    GROUP BY skill_id
) AS pl ON c.skill_id = pl.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(r_source, ';') AS requestSource
    FROM dbo.uat_skill_request_source
    GROUP BY skill_id
) AS rs ON c.skill_id = rs.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_name, ';') AS product
    FROM dbo.uat_skill_service_name
    GROUP BY skill_id
) AS sn ON c.skill_id = sn.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_region, ';') AS serviceRegion
    FROM dbo.uat_skill_service_region
    GROUP BY skill_id
) AS sr ON c.skill_id = sr.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_model, ';') AS customerSupportModel
    FROM dbo.uat_skill_support_model
    GROUP BY skill_id
) AS sm ON c.skill_id = sm.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(a_category, ';') AS requestType
    FROM dbo.uat_skill_action_category
    GROUP BY skill_id
) AS ac ON c.skill_id = ac.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_tag, ';') AS tag
    FROM dbo.uat_skill_tag
    GROUP BY skill_id
) AS t ON c.skill_id = t.skill_id;

CREATE UNIQUE CLUSTERED INDEX [UX_uat_skill_attributes] ON [bbm_stm].[dbo].[uat_skill_attributes]
([skill_id]);


--- PROD ---

DROP TABLE IF EXISTS dbo.skill_attributes

SELECT 
    c.skill_id, 
    c.skill_name,
	  cd.controlDesk,
    gc.goldenCustomer,
    ms.customerMarketSegment, 
    pl.preferredlanguage, 
    rs.requestSource, 
    sn.product, 
    sr.serviceRegion, 
    sm.customerSupportModel, 
    ac.requestType,
	  t.tag
INTO dbo.skill_attributes
FROM dbo.skill_config AS c
LEFT JOIN (
    SELECT skill_id, STRING_AGG(c_desk, ';') AS controlDesk
    FROM dbo.skill_control_desk
    GROUP BY skill_id
) AS cd ON c.skill_id = cd.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(g_customer, ';') AS goldenCustomer
    FROM dbo.skill_gold_customer
    GROUP BY skill_id
) AS gc ON c.skill_id = gc.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(m_segment, ';') AS customerMarketSegment
    FROM dbo.skill_market_segment
    GROUP BY skill_id
) AS ms ON c.skill_id = ms.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(p_language, ';') AS preferredlanguage
    FROM dbo.skill_pref_languages
    GROUP BY skill_id
) AS pl ON c.skill_id = pl.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(r_source, ';') AS requestSource
    FROM dbo.skill_request_source
    GROUP BY skill_id
) AS rs ON c.skill_id = rs.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_name, ';') AS product
    FROM dbo.skill_service_name
    GROUP BY skill_id
) AS sn ON c.skill_id = sn.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_region, ';') AS serviceRegion
    FROM dbo.skill_service_region
    GROUP BY skill_id
) AS sr ON c.skill_id = sr.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_model, ';') AS customerSupportModel
    FROM dbo.skill_support_model
    GROUP BY skill_id
) AS sm ON c.skill_id = sm.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(a_category, ';') AS requestType
    FROM dbo.skill_action_category
    GROUP BY skill_id
) AS ac ON c.skill_id = ac.skill_id
LEFT JOIN (
    SELECT skill_id, STRING_AGG(s_tag, ';') AS tag
    FROM dbo.skill_tag
    GROUP BY skill_id
) AS t ON c.skill_id = t.skill_id;

CREATE UNIQUE CLUSTERED INDEX [UX_skill_attributes] ON [bbm_stm].[dbo].[skill_attributes]
([skill_id]);