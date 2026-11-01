--------------------------------------------------------------------------------
-- 1. CONTEO TOTAL DE REGISTROS (ORIGEN VS DESTINO)
--------------------------------------------------------------------------------
SELECT 
    'legacy_policies' AS dataset_name, 
    COUNT(*) AS total_records 
FROM legacy_policies
UNION ALL
SELECT 
    'target_policies' AS dataset_name, 
    COUNT(*) AS total_records 
FROM target_policies;


--------------------------------------------------------------------------------
-- 2. PÓLIZAS EN ORIGEN QUE NO FUERON MIGRADAS (MISSING_TARGET)
--------------------------------------------------------------------------------
SELECT 
    l.policy_id,
    l.client_id,
    l.policy_number,
    'MISSING_TARGET' AS validation_status
FROM legacy_policies l
LEFT JOIN target_policies t ON l.policy_id = t.policy_id
WHERE t.policy_id IS NULL;


--------------------------------------------------------------------------------
-- 3. DETECCIÓN DE REGISTROS DUPLICADOS EN ORIGEN
--------------------------------------------------------------------------------
SELECT 
    policy_id, 
    COUNT(*) AS occurrence_count
FROM legacy_policies
GROUP BY policy_id
HAVING COUNT(*) > 1;


--------------------------------------------------------------------------------
-- 4. CLIENTES QUE POSEEN MÁS DE UNA PÓLIZA EN ORIGEN
--------------------------------------------------------------------------------
SELECT 
    client_id, 
    COUNT(policy_id) AS total_policies
FROM legacy_policies
GROUP BY client_id
HAVING COUNT(policy_id) > 1
ORDER BY total_policies DESC;


--------------------------------------------------------------------------------
-- 5. RECONCILIACIÓN Y COMPARACIÓN CAMPO POR CAMPO (OK / ERROR / MISSING_TARGET)
--------------------------------------------------------------------------------
WITH comparison AS (
    SELECT 
        l.policy_id,
        CASE 
            WHEN t.policy_id IS NULL THEN 'MISSING_TARGET'
            WHEN l.client_id = t.client_id 
                 AND l.policy_number = t.policy_number 
                 AND l.premium = t.premium 
                 AND l.currency = t.currency 
                 AND l.start_date = t.start_date 
                 AND l.end_date = t.end_date 
                 AND l.status = t.status THEN 'OK'
            ELSE 'ERROR'
        END AS validation_status,
        -- Identificación dinámica de campos discrepantes
        TRIM(
            CONCAT(
                IFF(l.client_id <> t.client_id, 'client_id, ', ''),
                IFF(l.policy_number <> t.policy_number, 'policy_number, ', ''),
                IFF(l.premium <> t.premium, 'premium, ', ''),
                IFF(l.currency <> t.currency, 'currency, ', ''),
                IFF(l.start_date <> t.start_date, 'start_date, ', ''),
                IFF(l.end_date <> t.end_date, 'end_date, ', ''),
                IFF(l.status <> t.status, 'status, ', '')
            ), ', '
        ) AS fields_with_differences
    FROM legacy_policies l
    LEFT JOIN target_policies t ON l.policy_id = t.policy_id
)
SELECT 
    policy_id,
    validation_status,
    NULLIF(fields_with_differences, '') AS fields_with_differences
FROM comparison;