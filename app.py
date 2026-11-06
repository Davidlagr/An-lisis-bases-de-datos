
import streamlit as st
import pandas as pd
import io
from functools import reduce

# Configuración de la página
st.set_page_config(page_title="Cruce de Bases de Datos", layout="wide", page_icon="🔍")
st.title("🔍 Cruce de Información y Consolidación de Observaciones")
st.markdown("Sube múltiples bases de datos para encontrar coincidencias exactas por Cédula o Radicado y consolidar las observaciones de cada archivo.")

# Subida de múltiples archivos
uploaded_files = st.file_uploader("Sube las bases de datos (formatos soportados: Excel o CSV)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.info("⚠️ Por favor, sube al menos dos bases de datos para poder realizar el cruce.")
    else:
        # Diccionario para almacenar los DataFrames
        dataframes = {}
        
        for file in uploaded_files:
            try:
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                dataframes[file.name] = df
            except Exception as e:
                st.error(f"Error al leer el archivo {file.name}: {e}")
        
        # Identificar columnas comunes entre todos los archivos subidos
        columnas_por_df = [set(df.columns) for df in dataframes.values()]
        columnas_comunes = list(set.intersection(*columnas_por_df))
        
        if not columnas_comunes:
            st.error("No se encontraron columnas con el mismo nombre en todos los archivos. Asegúrate de que la llave (ej. 'CEDULA' o 'RADICADO') se llame exactamente igual en todas las bases.")
        else:
            # Seleccionar la llave de cruce
            st.markdown("### ⚙️ Configuración del Cruce")
            col1, col2 = st.columns(2)
            
            with col1:
                join_key = st.selectbox("1. Selecciona la columna llave para el cruce:", columnas_comunes)
            
            with col2:
                palabra_clave_obs = st.text_input("2. Palabra clave para filtrar observaciones (opcional):", value="observaci")

            if st.button("Ejecutar Cruce", type="primary"):
                processed_dfs = []
                
                for name, df in dataframes.items():
                    df_renamed = df.copy()
                    
                    # Estandarizar la columna llave (convertir a string, quitar espacios y decimales)
                    df_renamed[join_key] = df_renamed[join_key].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    
                    # Renombrar las columnas agregando el nombre del archivo de origen para evitar confusiones
                    df_renamed.columns = [f"{col} ({name})" if col != join_key else col for col in df_renamed.columns]
                    processed_dfs.append(df_renamed)
                
                # Realizar el cruce (Inner Join iterativo para asegurar coincidencias en TODAS las bases)
                try:
                    merged_df = reduce(lambda left, right: pd.merge(left, right, on=join_key, how='inner'), processed_dfs)
                    
                    if merged_df.empty:
                        st.warning("El cruce se ejecutó correctamente, pero no se encontraron coincidencias exactas entre los archivos para la columna seleccionada.")
                    else:
                        st.success(f"✅ Cruce exitoso. Se encontraron {len(merged_df)} registros coincidentes en todas las bases.")
                        
                        # Filtrar columnas para la vista resumen (Llave + Columnas que contengan la palabra clave)
                        obs_columns = [col for col in merged_df.columns if palabra_clave_obs.lower() in col.lower() or col == join_key]
                        
                        # Dataframe final a mostrar
                        df_resumen = merged_df[obs_columns] if len(obs_columns) > 1 else merged_df
                        
                        st.markdown("### 📊 Vista Previa: Coincidencias y Observaciones")
                        st.dataframe(df_resumen, use_container_width=True)
                        
                        # Preparar la descarga en Excel
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            # Hoja 1: Solo las observaciones
                            df_resumen.to_excel(writer, index=False, sheet_name='Resumen_Observaciones')
                            # Hoja 2: Toda la información unificada
                            merged_df.to_excel(writer, index=False, sheet_name='Cruce_Completo')
                        
                        excel_data = output.getvalue()
                        
                        st.download_button(
                            label="📥 Descargar Resultados en formato Excel",
                            data=excel_data,
                            file_name="Resultado_Cruce_Bases.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"Error durante el proceso de cruce: {e}")
