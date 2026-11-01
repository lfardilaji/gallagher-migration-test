# Gallagher Data Engineering Technical Assessment

## Descripción del Proyecto
Este repositorio contiene la solución para la prueba técnica de ingeniería de datos para Gallagher, enfocada en la migración, validación y conciliación de pólizas.

## Progreso y Componentes

- **Punto 1: Procesamiento Inicial con Python**
  - Implementación de scripts en Python (`quality_framework.py`) para la lectura, análisis y preparación de los conjuntos de datos (`legacy_policies` y `target_policies`).

- **Punto 2: Validación y Conciliación de Datos (Snowflake)**
  - Carga de datos en Snowflake manejando los formatos de fecha `DD/MM/YYYY`.
  - Script implementado en `reconciliation.sql` para auditar la integridad de la migración.

  ### Evidencias de Ejecución (Punto 2):

  1. **Conteo Volumétrico (Comparativa de registros totales):**
     ![Conteo Total](Conteo_Total.png)

  2. **Registros Faltantes / Sin Migrar (Pólizas en legacy no encontradas en target):**
     ![Sin Migrar](Sin%20migrar.png)

  3. **Detección de Duplicados en el Destino:**
     ![Duplicados](Duplicados.png)

- **Punto 3 y 4: Transformaciones y Modelado**
  - *Próximamente:* Modelado analítico y transformaciones estructuradas mediante dbt.
