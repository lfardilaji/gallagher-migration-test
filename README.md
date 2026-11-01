# Gallagher Data Engineering Technical Assessment

## Descripción del Proyecto
Este repositorio contiene la solución para la prueba técnica de ingeniería de datos para Gallagher, enfocada en la migración, validación y conciliación de pólizas.

## Progreso y Componentes

- **Punto 1: Procesamiento Inicial con Python**
  - Implementación de scripts en Python para la lectura, análisis y preparación de los conjuntos de datos (`legacy_policies` y `target_policies`).

- **Punto 2: Validación y Conciliación de Datos (Snowflake)**
  - Carga de datos en Snowflake manejando los formatos de fecha `DD/MM/YYYY`.
  - Script implementado en `reconciliation.sql` para auditar la integridad de la migración:
    - Conteo volumétrico total entre origen y destino.
    - Identificación de registros faltantes en el destino (`MISSING_TARGET`).
    - Detección de duplicados.
    - Auditoría campo por campo de atributos críticos (`premium`, `currency`, `start_date`, `end_date`, `status`) con indicadores de estatus (`OK` / `ERROR`).

- **Punto 3 y 4: Transformaciones y Modelado**
  - *Próximamente:* Modelado analítico y transformaciones estructuradas.

---
**Evidencia de Ejecución (Punto 2 en Snowflake):**
![Evidencia Snowflake](evidence_point2.png)
