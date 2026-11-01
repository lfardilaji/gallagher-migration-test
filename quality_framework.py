import os
from datetime import datetime
import pandas as pd

class DataQualityFramework:
    """
    Data Quality Framework para la migración a OPTIMA.
    Permite registrar reglas de negocio y aplicarlas sobre DataFrames.
    """
    def __init__(self):
        self.rules = []

    def add_rule(self, rule_name: str, validation_func, description: str):
        """Registra una nueva regla de validación."""
        self.rules.append({
            "name": rule_name,
            "func": validation_func,
            "description": description
        })

    def run_validations(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """Aplica las reglas y retorna un DataFrame con los registros defectuosos."""
        failure_reports = []

        for rule in self.rules:
            try:
                failed_df = rule["func"](df)
                if not failed_df.empty:
                    failed_df = failed_df.copy()
                    failed_df['failed_rule'] = rule["name"]
                    failed_df['rule_description'] = rule["description"]
                    failed_df['source_dataset'] = dataset_name
                    failure_reports.append(failed_df)
            except Exception as e:
                print(f"ERROR: Fallo al ejecutar la regla '{rule['name']}' en {dataset_name}. Detalle: {e}")

        if failure_reports:
            return pd.concat(failure_reports, ignore_index=True)
        return pd.DataFrame()


def generate_text_log(all_reports: dict, log_filename="dq_execution_log.txt"):
    """
    Exporta un reporte estructurado en formato de texto plano (.txt) 
    actuando como un Log de Ejecución con marca de tiempo y detalle de errores.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write(f" REPORTE DE CALIDAD DE DATOS - LOG DE EJECUCIÓN\n")
        f.write(f" Timestamp de Ejecución: {current_time}\n")
        f.write("=" * 70 + "\n\n")
        
        total_incidences = sum(len(rep) for rep in all_reports.values())
        f.write(f"Resumen General: Se detectaron {total_incidences} incidencias totales.\n\n")
        
        for ds_name, report_df in all_reports.items():
            f.write(f"--- Dataset Evaluado: {ds_name.upper()} ---\n")
            if report_df.empty:
                f.write("Status: ✅ OK (Sin anomalías detectadas)\n\n")
            else:
                f.write(f"Status: ⚠️ ATENCIÓN ({len(report_df)} registros con errores)\n")
                for _, row in report_df.iterrows():
                    # Identificamos dinámicamente si es client_id o policy_id
                    identifier = row.get('client_id') or row.get('policy_id', 'N/A')
                    f.write(f"  * Registro ID   : {identifier}\n")
                    f.write(f"    Regla Fallida : {row['failed_rule']}\n")
                    f.write(f"    Descripción   : {row['rule_description']}\n")
                    f.write("-" * 50 + "\n")
            f.write("\n")
            
    print(f"\n[INFO] Log de ejecución exportado con éxito en: '{log_filename}'")


if __name__ == "__main__":
    # 1. Configuración de archivos
    files_to_process = {
        'accounts': 'accounts.csv',
        'legacy_policies': 'legacy_policies.csv',
        'target_policies': 'target_policies.csv'
    }

    datasets = {}
    print("Iniciando ingesta de datos...")
    for name, filepath in files_to_process.items():
        if os.path.exists(filepath):
            datasets[name] = pd.read_csv(filepath)
            print(f" -> {name} cargado correctamente ({len(datasets[name])} filas).")
        else:
            print(f" -> ADVERTENCIA: No se encontró el archivo {filepath}.")

    # 2. Instanciación de frameworks
    dq_accounts = DataQualityFramework()
    dq_policies = DataQualityFramework()

    # Definición de reglas (Accounts)
    dq_accounts.add_rule(
        rule_name="Invalid_Document_Type",
        validation_func=lambda df: df[~df['document_type'].isin(['DNI', 'RUT'])],
        description="El tipo de documento debe ser DNI o RUT según diccionario."
    )
    dq_accounts.add_rule(
        rule_name="Malformed_Email",
        validation_func=lambda df: df[~df['email'].str.contains('@', na=False)],
        description="Formato de email inválido (falta el @)."
    )
    dq_accounts.add_rule(
        rule_name="Missing_Document_Number",
        validation_func=lambda df: df[(df['document_number'].isna()) | (df['document_number'] == '')],
        description="Document_number nulo o vacío."
    )

    # Definición de reglas (Policies)
    dq_policies.add_rule(
        rule_name="Invalid_Premium_Value",
        validation_func=lambda df: df[(df['premium'].isna()) | (df['premium'] <= 0)],
        description="La prima debe ser un valor positivo."
    )
    dq_policies.add_rule(
        rule_name="Invalid_Currency",
        validation_func=lambda df: df[~df['currency'].isin(['PEN', 'USD', 'COP', 'CLP'])],
        description="Moneda no reconocida en el catálogo."
    )

    # 3. Plan de ejecución
    execution_plan = [
        {"dataset": "accounts", "framework": dq_accounts},
        {"dataset": "legacy_policies", "framework": dq_policies},
        {"dataset": "target_policies", "framework": dq_policies}
    ]

    all_reports = {}
    for plan in execution_plan:
        ds_name = plan["dataset"]
        if ds_name in datasets:
            report = plan["framework"].run_validations(datasets[ds_name], dataset_name=ds_name)
            all_reports[ds_name] = report

    # 4. Generación del reporte de texto plano (.txt) tipo log
    generate_text_log(all_reports, log_filename="dq_execution_log.txt")