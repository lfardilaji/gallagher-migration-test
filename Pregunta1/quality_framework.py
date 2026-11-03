import os
import sys
import logging
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Dict
import pandas as pd

# Configuración formal de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Diccionario explícito de llaves primarias por dataset.
PRIMARY_KEYS = {
    "accounts": "client_id",
    "legacy_policies": "policy_id",
    "target_policies": "policy_id"
}

@dataclass(frozen=True)
class Rule:
    """Estructura formal de una regla de calidad de datos basada en estándares ISO/IEC 25012."""
    name: str
    dimension: str          # Completitud, Unicidad, Validez, Integridad Referencial, Consistencia
    severity: str           # CRITICAL (bloquea migración/cuarentena) o WARNING (bandera de auditoría)
    dataset: str            # Dataset principal al que evalúa ('accounts', 'legacy_policies', 'target_policies')
    key: str                # Columna de identificación única
    check: Callable[[Dict[str, pd.DataFrame]], pd.DataFrame]  # Recibe TODOS los datasets y retorna errores
    description: str        # Detalle explicativo de la regla


class DataQualityFramework:
    """
    Data Quality Framework para la migración a OPTIMA con el set completo de 14 reglas de negocio.
    """
    def __init__(self):
        self.rules = []

    def add_rule(self, rule: Rule):
        """Registra una nueva regla estructurada de validación."""
        self.rules.append(rule)

    def run_validations(self, datasets: Dict[str, pd.DataFrame]):
        """Ejecuta las reglas evaluando el diccionario global de datasets."""
        summary = []
        details = []
        has_execution_errors = False

        for rule in self.rules:
            df = datasets.get(rule.dataset)
            if df is None or df.empty:
                logging.warning(f"Dataset '{rule.dataset}' no encontrado o vacío para la regla '{rule.name}'.")
                continue

            try:
                failed_df = rule.check(datasets)
                if not failed_df.empty:
                    status = "FAILED"
                    failed_df = failed_df.copy()
                    failed_df['rule'] = rule.name
                    failed_df['dimension'] = rule.dimension
                    failed_df['severity'] = rule.severity
                    failed_df['rule_description'] = rule.description
                    failed_df['source_dataset'] = rule.dataset
                    details.append(failed_df)
                else:
                    status = "PASSED"
            except Exception:
                logging.exception(f"ERROR: Fallo crítico al ejecutar la regla '{rule.name}' en '{rule.dataset}'.")
                status = "ERROR"
                has_execution_errors = True
                failed_df = pd.DataFrame()

            summary.append({
                "rule": rule.name,
                "dimension": rule.dimension,
                "status": status,
                "severity": rule.severity,
                "dataset": rule.dataset,
                "failed_count": len(failed_df) if not failed_df.empty else 0
            })

        summary_df = pd.DataFrame(summary)
        details_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
        
        return summary_df, details_df, has_execution_errors


def generate_text_log(summary_df: pd.DataFrame, details_df: pd.DataFrame, log_filepath="dq_execution_log.txt"):
    """Exporta un reporte estructurado agrupado por estados y dimensiones."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_filepath, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write(f" REPORTE DE CALIDAD DE DATOS - LOG DE EJECUCIÓN (ISO/IEC 25012)\n")
        f.write(f" Timestamp de Ejecución: {current_time}\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("--- RESUMEN DE ESTADO DE REGLAS ---\n")
        for _, row in summary_df.iterrows():
            f.write(f" * Regla: {row['rule']} | Dataset: {row['dataset']} | Estado: {row['status']} | Fallidos: {row['failed_count']}\n")
        f.write("\n" + "=" * 70 + "\n\n")

        if details_df.empty:
            f.write("Detalle de Incidencias: ✅ Sin registros defectuosos encontrados.\n")
        else:
            for ds_name, group_df in details_df.groupby('source_dataset'):
                f.write(f"--- Dataset Evaluado: {ds_name.upper()} ---\n")
                f.write(f"Status: ⚠️ ATENCIÓN ({len(group_df)} registros con errores)\n")
                
                pk_col = PRIMARY_KEYS.get(ds_name, 'client_id')
                
                for row in group_df.to_dict("records"):
                    identifier = row.get(pk_col, 'N/A')
                    f.write(f"  * Registro ID   : {identifier}\n")
                    f.write(f"    Dimensión     : {row.get('dimension', 'N/A')}\n")
                    f.write(f"    Severidad     : {row.get('severity', 'CRITICAL')}\n")
                    f.write(f"    Regla Fallida : {row['rule']}\n")
                    f.write(f"    Descripción   : {row['rule_description']}\n")
                    f.write("-" * 50 + "\n")
                f.write("\n")
            
    logging.info(f"Log de ejecución exportado con éxito en: '{log_filepath}'")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, ".."))
    enunciado_dir = os.path.join(root_dir, "Enunciado")
    
    files_to_process = {
        'accounts': os.path.join(enunciado_dir, 'accounts.csv'),
        'legacy_policies': os.path.join(enunciado_dir, 'legacy_policies.csv'),
        'target_policies': os.path.join(enunciado_dir, 'target_policies.csv')
    }

    datasets = {}
    logging.info("Iniciando ingesta segura de datos y normalización de formatos...")
    for name, filepath in files_to_process.items():
        if os.path.exists(filepath):
            # 1. Cargar preservando texto
            df = pd.read_csv(filepath, dtype=str)
            
            # A. Normalizar nombres de columnas a minúsculas y sin espacios (Evita KeyError)
            df.columns = df.columns.str.strip().str.lower()
            
            # B. Limpiar y estandarizar correos si la columna existe
            if 'email' in df.columns:
                df['email'] = df['email'].astype(str).str.strip()
                df.loc[df['email'].isin(['nan', 'None', '']), 'email'] = None

            # C. Forzar formato de fechas europeo (dayfirst=True) para evitar inversión MM/DD
            columnas_fecha = ['start_date', 'end_date', 'created_date', 'birthdate']
            for col in columnas_fecha:
                if col in df.columns:
                    # errors='coerce' convierte valores mal formados en NaT en lugar de romper
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            # =========================================================================

            datasets[name] = df
            logging.info(f" -> {name} cargado y normalizado correctamente ({len(datasets[name])} filas).")
        else:
            logging.warning(f" -> ADVERTENCIA: No se encontró el archivo en {filepath}.")

    dq_framework = DataQualityFramework()

    # --- SET COMPLETO DE 14 REGLAS DE NEGOCIO Y CALIDAD (T12) ---

    # 1. Correo por Regex 
    def check_malformed_email(d):
        df = d["accounts"]
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        
        # Detectar sintaxis realmente rota (sin @, sin punto, espacios, etc.)
        sintaxis_rota = ~df['email'].str.match(email_regex, na=False)
        
        # Retorna solo los que tienen sintaxis rota de verdad
        return df[sintaxis_rota]

    dq_framework.add_rule(Rule(
        name="Malformed_Email", dimension="Validez", severity="WARNING",
        dataset="accounts", key="client_id", check=check_malformed_email,
        description="Formato de email inválido o dominio placeholder (@example.com)."
    ))

    # 2. Documento único por tipo + número (Unicidad)
    dq_framework.add_rule(Rule(
        name="Duplicate_Document", dimension="Unicidad", severity="CRITICAL",
        dataset="accounts", key="client_id",
        check=lambda d: d["accounts"][d["accounts"].duplicated(subset=['document_type', 'document_number'], keep=False)],
        description="Combinación de tipo y número de documento duplicada."
    ))

   # 3. Correo único (Unicidad) - 
    def check_duplicate_email(d):
        df = d["accounts"]
        # Validar que la columna exista (evita KeyError si hay variaciones)
        col_email = 'email' if 'email' in df.columns else [c for c in df.columns if 'email' in c.lower()][0]
        
        # Filtrar solo registros que tengan un correo válido (no nulos ni vacíos)
        valid_emails = df[df[col_email].notna() & (df[col_email].str.strip() != '') & (df[col_email].str.lower() != 'nan')]
        
        # Retornar los duplicados exactos
        return valid_emails[valid_emails.duplicated(subset=[col_email], keep=False)]

    dq_framework.add_rule(Rule(
        name="Duplicate_Email", dimension="Unicidad", severity="WARNING",
        dataset="accounts", key="client_id",
        check=check_duplicate_email,
        description="Mismo correo electrónico asignado a múltiples clientes."
    ))

    # 4. Longitud de documento por tipo (Validez)
    def check_doc_length(d):
        df = d["accounts"]
        # Supuesto: DNI/RUT válidos deben tener entre 7 y 12 dígitos por ejemplo, detectando anómalos de 5 o 11 dígitos extraños
        mask_len = df['document_number'].str.len().isin([5, 6, 11])
        return df[mask_len]

    dq_framework.add_rule(Rule(
        name="Invalid_Document_Length", dimension="Validez", severity="CRITICAL",
        dataset="accounts", key="client_id", check=check_doc_length,
        description="Longitud de documento de identidad anómala (5, 6 u 11 dígitos)."
    ))

    # 5. Consistencia país vs tipo de documento (Consistencia)
    dq_framework.add_rule(Rule(
        name="Country_Document_Mismatch", dimension="Consistencia", severity="WARNING",
        dataset="accounts", key="client_id",
        check=lambda d: d["accounts"][(d["accounts"]['country_code'] == 'PER') & (d["accounts"]['document_type'] == 'RUT')],
        description="Inconsistencia: Tipo de documento RUT (Chile) asignado a cliente de Perú."
    ))

    # 6. Teléfono centinela (Validez / Valor por defecto)
    dq_framework.add_rule(Rule(
        name="Sentinel_Phone", dimension="Validez", severity="WARNING",
        dataset="accounts", key="client_id",
        check=lambda d: d["accounts"][d["accounts"]['phone'] == '7010001'],
        description="Teléfono de relleno o centinela repetido masivamente."
    ))

    # 7. Fecha de nacimiento en rango (Validez temporal)
    def check_birthdate_range(d):
        df = d["accounts"].copy()
        df['birth_year'] = pd.to_datetime(df['birthdate'], errors='coerce').dt.year
        return df[(df['birth_year'] < 1920) | (df['birth_year'] > 2010)]

    dq_framework.add_rule(Rule(
        name="Invalid_Birthdate_Range", dimension="Validez", severity="CRITICAL",
        dataset="accounts", key="client_id", check=check_birthdate_range,
        description="Fecha de nacimiento fuera de rango lógico (ej. años 1880 o 1893)."
    ))

    # 8. Edad mínima a la creación (Menor de 18 años al momento de created_date)
    def check_underage(d):
        df = d["accounts"].copy()
        df['birth'] = pd.to_datetime(df['birthdate'], errors='coerce')
        df['created'] = pd.to_datetime(df['created_date'], errors='coerce')
        df['age_at_creation'] = ((df['created'] - df['birth']).dt.days / 365.25)
        return df[(df['age_at_creation'] < 18) & df['age_at_creation'].notna()]

    dq_framework.add_rule(Rule(
        name="Underage_At_Creation", dimension="Validez", severity="WARNING",
        dataset="accounts", key="client_id", check=check_underage,
        description="Titular menor de 18 años al momento de la creación de la cuenta."
    ))

    # 9. created_date entre 2014 y hoy (Validez)
    def check_created_date(d):
        df = d["accounts"].copy()
        df['created'] = pd.to_datetime(df['created_date'], errors='coerce')
        return df[(df['created'].dt.year < 2014) | (df['created'] > pd.Timestamp.today())]

    dq_framework.add_rule(Rule(
        name="Invalid_Created_Date", dimension="Validez", severity="CRITICAL",
        dataset="accounts", key="client_id", check=check_created_date,
        description="Fecha de creación anterior a 2014 (inicio de operaciones) o futura."
    ))

    # 10. start_date < end_date en pólizas
    def check_policy_dates(d, ds_name):
        df = d[ds_name].copy()
        df['start'] = pd.to_datetime(df['start_date'], errors='coerce')
        df['end'] = pd.to_datetime(df['end_date'], errors='coerce')
        return df[df['start'] > df['end']]

    dq_framework.add_rule(Rule(
        name="Invalid_Policy_Dates", dimension="Validez", severity="CRITICAL",
        dataset="legacy_policies", key="policy_id",
        check=lambda d: check_policy_dates(d, "legacy_policies"),
        description="Fecha de inicio posterior a la fecha de fin en póliza (Legacy)."
    ))
    dq_framework.add_rule(Rule(
        name="Invalid_Policy_Dates", dimension="Validez", severity="CRITICAL",
        dataset="target_policies", key="policy_id",
        check=lambda d: check_policy_dates(d, "target_policies"),
        description="Fecha de inicio posterior a la fecha de fin en póliza (Target)."
    ))

    # 11. Póliza ACTIVE con cliente INACTIVE
    def check_active_policy_inactive_client(d, ds_name):
        df = d[ds_name].merge(d["accounts"][['client_id', 'status']], on='client_id', suffixes=('', '_acc'), how='inner')
        return df[(df['status'] == 'ACTIVE') & (df['status_acc'] == 'INACTIVE')]

    dq_framework.add_rule(Rule(
        name="Active_Policy_Inactive_Client", dimension="Consistencia", severity="WARNING",
        dataset="target_policies", key="policy_id",
        check=lambda d: check_active_policy_inactive_client(d, "target_policies"),
        description="Póliza en estado ACTIVE asociada a un cliente INACTIVE."
    ))

    # 12. Póliza ACTIVE con inicio futuro
    def check_future_active_policy(d, ds_name):
        df = d[ds_name].copy()
        df['start'] = pd.to_datetime(df['start_date'], errors='coerce')
        return df[(df['status'] == 'ACTIVE') & (df['start'] > pd.Timestamp.today())]

    dq_framework.add_rule(Rule(
        name="Future_Start_Date", dimension="Validez", severity="WARNING",
        dataset="target_policies", key="policy_id",
        check=lambda d: check_future_active_policy(d, "target_policies"),
        description="Póliza ACTIVE con fecha de inicio futura."
    ))

    # 13. Integridad referencial (Póliza huérfana)
    dq_framework.add_rule(Rule(
        name="Orphan_Policy", dimension="Integridad Referencial", severity="CRITICAL",
        dataset="target_policies", key="policy_id",
        check=lambda d: d["target_policies"][~d["target_policies"]['client_id'].isin(d["accounts"]['client_id'].dropna())],
        description="Póliza huérfana: el client_id no existe en la tabla accounts."
    ))

    # 14. Vigencia anterior a la creación del cliente
    def check_policy_before_client(d, ds_name):
        df = d[ds_name].merge(d["accounts"][['client_id', 'created_date']], on='client_id', how='inner')
        df['start'] = pd.to_datetime(df['start_date'], errors='coerce')
        df['created'] = pd.to_datetime(df['created_date'], errors='coerce')
        return df[df['start'] < df['created']]

    dq_framework.add_rule(Rule(
        name="Policy_Before_Client_Creation", dimension="Consistencia", severity="WARNING",
        dataset="target_policies", key="policy_id",
        check=lambda d: check_policy_before_client(d, "target_policies"),
        description="Vigencia de póliza anterior a la fecha de creación del cliente."
    ))

    # Ejecución global con control de estados
    summary_df, details_df, has_errors = dq_framework.run_validations(datasets)

    # Exportación del log
    log_output_path = os.path.join(current_dir, "dq_execution_log.txt")
    generate_text_log(summary_df, details_df, log_filepath=log_output_path)

    # Salida con error si hay fallas críticas o excepciones técnicas
    if has_errors or not summary_df[(summary_df['severity'] == 'CRITICAL') & (summary_df['failed_count'] > 0)].empty:
        logging.error("La ejecución de calidad finalizó con errores críticos detectados.")
        sys.exit(1)
    else:
        logging.info("Validación de calidad completada con éxito operativo.")
        sys.exit(0)