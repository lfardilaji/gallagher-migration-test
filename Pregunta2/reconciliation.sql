--------------------------------------------------------------------------------
-- 1. CONTEO TOTAL DE REGISTROS (ORIGEN VS DESTINO)
--------------------------------------------------------------------------------
SELECT 
    'legacy_policies' AS dataset_name, 
    COUNT(*) AS total_records 
FROM GALLAGHER.PUBLIC.legacy_policies
UNION ALL
SELECT 
    'target_policies' AS dataset_name, 
    COUNT(*) AS total_records 
FROM GALLAGHER.PUBLIC.target_policies;


--------------------------------------------------------------------------------
-- 2. CONTROL ADICIONAL: IDENTIFICACION DE NULOS EN AMBAS TABLAS
--------------------------------------------------------------------------------

SELECT 
	'legacy_policies' AS dataset_name, 
	COUNT(*) AS null_policy_ids
FROM GALLAGHER.PUBLIC.legacy_policies
WHERE policy_id IS NULL
UNION ALL
SELECT 
	'target_policies' AS dataset_name, 
	COUNT(*) AS null_policy_ids
FROM GALLAGHER.PUBLIC.target_policies
WHERE policy_id IS NULL;

--------------------------------------------------------------------------------
-- 3. PÓLIZAS EN ORIGEN QUE NO FUERON MIGRADAS (MISSING_TARGET)
--------------------------------------------------------------------------------


SELECT 
    l.policy_id,
    l.client_id,
    l.policy_number,
    'MISSING_TARGET' AS validation_status
FROM GALLAGHER.PUBLIC.legacy_policies l
WHERE l.policy_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM GALLAGHER.PUBLIC.target_policies t
      WHERE t.policy_id = l.policy_id
  );
  
  
--------------------------------------------------------------------------------  
-- 4. CONTROL ADICIONAL: POLIZAS DEL DESTINO QUE NO EXISTEN EN ORIGEN (BASURA)
--------------------------------------------------------------------------------
SELECT 
	t.policy_id, 
	t.client_id, 
	t.policy_number,
    'EXTRA_IN_TARGET' AS validation_status
FROM GALLAGHER.PUBLIC.target_policies t
WHERE t.policy_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM GALLAGHER.PUBLIC.legacy_policies l
      WHERE l.policy_id = t.policy_id
  );


--------------------------------------------------------------------------------
-- 5. DETECCIÓN DE REGISTROS DUPLICADOS EN ORIGEN Y EN DESTINO
--------------------------------------------------------------------------------

SELECT 
	'SOURCE' AS dataset_name, 
	policy_id, 
	COUNT(*) AS occurrence_count
FROM GALLAGHER.PUBLIC.legacy_policies
GROUP BY policy_id
HAVING COUNT(*) > 1
UNION ALL
SELECT 
	'TARGET' AS dataset_name, 
	policy_id, 
	COUNT(*) AS occurrence_count
FROM GALLAGHER.PUBLIC.target_policies
GROUP BY policy_id
HAVING COUNT(*) > 1
ORDER BY 1,3 DESC;




--------------------------------------------------------------------------------
-- 6. RECONCILIACIÓN Y COMPARACIÓN CAMPO POR CAMPO (OK / ERROR / MISSING_TARGET / MISSING_SOURCE)
--------------------------------------------------------------------------------
WITH comparison AS (
    SELECT 
        COALESCE(l.policy_id, t.policy_id) AS policy_id,
        CASE 
            WHEN t.policy_id IS NULL THEN 'MISSING_TARGET'
            WHEN l.policy_id IS NULL THEN 'MISSING_SOURCE'
            WHEN l.client_id IS NOT DISTINCT FROM t.client_id 
                 AND l.policy_number IS NOT DISTINCT FROM t.policy_number 
                 AND l.premium IS NOT DISTINCT FROM t.premium 
                 AND l.currency IS NOT DISTINCT FROM t.currency 
                 AND l.start_date IS NOT DISTINCT FROM t.start_date 
                 AND l.end_date IS NOT DISTINCT FROM t.end_date 
                 AND l.status IS NOT DISTINCT FROM t.status THEN 'OK'
            ELSE 'ERROR'
        END AS validation_status,
        -- Identificación dinámica de campos discrepantes
        IFF(
            t.policy_id IS NULL OR l.policy_id IS NULL, 
            NULL, 
            NULLIF(
                TRIM(
                    CONCAT(
                        IFF(l.client_id IS DISTINCT FROM t.client_id, 'client_id, ', ''),
                        IFF(l.policy_number IS DISTINCT FROM t.policy_number, 'policy_number, ', ''),
                        IFF(l.premium IS DISTINCT FROM t.premium, 'premium, ', ''),
                        IFF(l.currency IS DISTINCT FROM t.currency, 'currency, ', ''),
                        IFF(l.start_date IS DISTINCT FROM t.start_date, 'start_date, ', ''),
                        IFF(l.end_date IS DISTINCT FROM t.end_date, 'end_date, ', ''),
                        IFF(l.status IS DISTINCT FROM t.status, 'status, ', '')
                    ), 
                    ', '
                ), 
                ''
            )
        ) AS fields_with_differences
    FROM GALLAGHER.PUBLIC.legacy_policies l
    -- Cambio a FULL OUTER JOIN para integrar MISSING_SOURCE
    FULL OUTER JOIN GALLAGHER.PUBLIC.target_policies t ON l.policy_id = t.policy_id
)
SELECT 
    policy_id,
    validation_status,
    NULLIF(fields_with_differences, '') AS fields_with_differences
FROM comparison;

--------------------------------------------------------------------------------
-- 7. CONCILIACIÓN FINANCIERA POR MONEDA (Suma de Primas Origen vs Destino)
--------------------------------------------------------------------------------
SELECT 
    currency,
    SUM(IFF(side = 'S', premium, 0)) AS premium_source,
    SUM(IFF(side = 'T', premium, 0)) AS premium_target,
    premium_source - premium_target AS diff
FROM (
    SELECT 'S' AS side, currency, premium FROM GALLAGHER.PUBLIC.legacy_policies
    UNION ALL
    SELECT 'T' AS side, currency, premium FROM GALLAGHER.PUBLIC.target_policies
)
GROUP BY currency;

--------------------------------------------------------------------------------
-- 8. INTEGRIDAD REFERENCIAL: PÓLIZAS SIN CLIENTE EXISTENTE (EVALUANDO ORIGEN Y DESTINO)
--------------------------------------------------------------------------------
SELECT 'legacy' AS source_table, l.policy_id, l.client_id
FROM GALLAGHER.PUBLIC.legacy_policies l
LEFT JOIN GALLAGHER.PUBLIC.accounts a ON a.client_id = l.client_id
WHERE a.client_id IS NULL
UNION ALL
SELECT 'target' AS source_table, t.policy_id, t.client_id
FROM GALLAGHER.PUBLIC.target_policies t
LEFT JOIN GALLAGHER.PUBLIC.accounts a ON a.client_id = t.client_id
WHERE a.client_id IS NULL;

--------------------------------------------------------------------------------
-- 9. CLIENTES QUE POSEAN MÁS DE UNA PÓLIZA (ORIGEN VS DESTINO)
--------------------------------------------------------------------------------
SELECT 
    'legacy_policies' AS dataset_name, 
    client_id, 
    COUNT(DISTINCT policy_id) AS policy_count
FROM GALLAGHER.PUBLIC.legacy_policies
GROUP BY client_id
HAVING COUNT(DISTINCT policy_id) > 1
UNION ALL
SELECT 
    'target_policies' AS dataset_name, 
    client_id, 
    COUNT(DISTINCT policy_id) AS policy_count
FROM GALLAGHER.PUBLIC.target_policies
GROUP BY client_id
HAVING COUNT(DISTINCT policy_id) > 1
ORDER BY 1, 3 DESC;

