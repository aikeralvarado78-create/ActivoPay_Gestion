import streamlit as st
import pandas as pd
import re
from datetime import datetime, timezone
from supabase import create_client, Client

# =========================================================================
# BLUEPRINT PASO 2: PERFILES DE USUARIO Y RESTRICCIONES DE SEGURIDAD
# =========================================================================
# Definición de roles del sistema para segregación de funciones y control puro.
ROLES = {
    "NEGOCIOS": "Ejecutivo / Gerente de Cuenta (Acceso restringido a su gestión e ingesta)",
    "TECNICO": "Integración de Aplicaciones / Administrador (Acceso global y cierre técnico)"
}

# =========================================================================
# CONEXIÓN SERVERLESS (SUPABASE FREE TIER)
# =========================================================================
# Configuración segura de credenciales sin servidor utilizando Streamlit Secrets.
@st.cache_resource
def conectar_supabase() -> Client:
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error("⚠️ Error de infraestructura: Configura 'SUPABASE_URL' y 'SUPABASE_KEY' en los Secrets de Streamlit.")
        return None

supabase: Client = conectar_supabase()

# =========================================================================
# BLUEPRINT PASO 8 & 9: REGLA RÍGIDA DE CAPTURA DE CUENTAS (10 DÍGITOS)
# =========================================================================
def normalizar_cuenta_10_digitos(cuenta_raw) -> str:
    """
    ALGORITMO DE CONSISTENCIA CORPORATIVA: Neutraliza formatos de 20 dígitos 
    con guiones o espacios (vistos en image_7a011e.png), extrayendo 
    estrictamente los últimos 10 caracteres numéricos de la cuenta cliente única.
    """
    if pd.isna(cuenta_raw) or str(cuenta_raw).strip() == "":
        return ""
    # Remover guiones, espacios, letras o caracteres especiales
    cuenta_limpia = re.sub(r'\D', '', str(cuenta_raw))
    # Extraer estrictamente los últimos 10 caracteres numéricos de la colas
    return cuenta_limpia[-10:] if len(cuenta_limpia) >= 10 else cuenta_limpia

# =========================================================================
# BLUEPRINT PASO 7 & 8: MOTOR DE PRE-PROCESAMIENTO Y CONTROL DE DUPLICIDAD
# =========================================================================
def evaluar_duplicados_y_estructura(df_excel) -> pd.DataFrame:
    """
    MOTOR SÍNCRONO DE CONTROL DE CALIDAD: Evalúa en lote la data de entrada 
    del Excel contra el Repositorio Global para evitar contaminación de la base de datos.
    """
    data_staging = []
    
    for idx, row in df_excel.iterrows():
        alertas = []
        valido = True
        
        # 1. Aplicación de la regla de normalización de cuenta
        cuenta_original = row.get('Número de Cta', '')
        cuenta_normalizada = normalizar_cuenta_10_digitos(cuenta_original)
        
        if len(cuenta_normalizada) < 10:
            alertas.append("Estructura de Cuenta Inválida (Menor a 10 dígitos)")
            valido = False
            
        # 2. Validación de formato Regex para RIF corporativo
        rif = str(row.get('RIF (Jxxxxxxx)', '')).strip().upper()
        if not re.match(r'^[JGEVVD]-[0-9]{8}-[0-9]$', rif):
            alertas.append("Formato de RIF incorrecto (Debe incluir guiones. Ej: J-12345678-9)")
            valido = False
            
        # 3. Validación condicional de usuarios en base al número indicado (Paso 4 - Módulo I)
        try:
            n_usuarios = int(row.get('Número de Personas que Utilizaran la Aplicación', 1))
        except:
            n_usuarios = 1
            
        if n_usuarios > 1 and (pd.isna(row.get('C.I. Usuario Secundario 1')) or str(row.get('C.I. Usuario Secundario 1')).strip() == ""):
            alertas.append(f"Inconsistencia: Se indicaron {n_usuarios} usuarios pero faltan datos del Usuario Secundario")
            valido = False

        # 4. Control síncrono de Duplicidad en Supabase (Simulación de consulta cruzada local)
        if supabase:
            # Validación cruzada de RIF y Cuenta en el Repositorio Central (Lista Muerta)
            res = supabase.table("afiliaciones").select("ejecutivo, estatus").or_(f"rif.eq.{rif},numero_cta.eq.{cuenta_normalizada}").execute()
            if res.data:
                orig = res.data[0]
                alertas.append(f"🚨 DUPLICADO: Ya registrado por {orig['ejecutivo']} en estado [{orig['estatus']}]")
                valido = False

        # Homologación de estatus antiguos (Blueprint Paso 3)
        estatus_original = str(row.get('Estatus Inicial', 'Recibido')).strip()
        estatus_mapeado = "1. Pendiente"
        if "falta" in estatus_original.lower() or "subsanar" in estatus_original.lower():
            estatus_mapeado = "3. Rechazado (Por Subsanar)"
        elif "credenciales" in estatus_original.lower() or "afiliado" in estatus_original.lower():
            estatus_mapeado = "4. Afiliado (Espera de Acompañamiento)"
        elif "produccion" in estatus_original.lower():
            estatus_mapeado = "5. En Producción"

        data_staging.append({
            "Fila": idx + 1,
            "Región": row.get('Región', ''),
            "Ejecutivo": row.get('Ejecutivo', ''),
            "Correo del Ejecutivo": row.get('Correo del Ejecutivo', ''),
            "Nombre de la Empresa": row.get('Nombre de la Empresa', ''),
            "RIF": rif,
            "Cuenta Normalizada": cuenta_normalizada,
            "Teléfono": str(row.get('NRO DE TELEFONO Empresa (Principal)', '')),
            "Rubro": row.get('Rubro (Razón económica)', ''),
            "Nro Usuarios": n_usuarios,
            "Nombre Master": row.get('Nombre y Apellido (Usuario Master)', ''),
            "C.I. Master": str(row.get('C.I. Usuario Master (Principal)', '')),
            "Correo Master": row.get('Correo Electrónico Usuario Master', ''),
            "Nombre Secundario": row.get('Nombre y Apellido (Usuario Secundario 1)', ''),
            "C.I. Secundario": str(row.get('C.I. Usuario Secundario 1', '')),
            "Correo Secundario": row.get('Correo Electrónico Usuario Secundario 1', ''),
            "Estatus Mapeado": estatus_mapeado,
            "Estatus Original Excel": estatus_original,
            "Alertas de Sistema": ", ".join(alertas) if alertas else "Validación Exitosa 🟢",
            "Aprobado": valido
        })
        
    return pd.DataFrame(data_staging)

# =========================================================================
# BLUEPRINT PASO 7: MOTOR DE CONTROL DE TIEMPOS (SEMÁFORO DE SLA)
# =========================================================================
def calcular_semaforo_sla(fecha_recibido_str) -> tuple:
    """
    MONITOR DE SLA TÉCNICO DE 24 HORAS: Calcula dinámicamente el tiempo transcurrido 
    desde la máquina cliente, pintando las alertas del Core.
    """
    if not fecha_recibido_str:
        return "🟢", "Verde (Tiempo Seguro)", "24:00:00"
        
    fecha_recibido = datetime.fromisoformat(fecha_recibido_str.replace("Z", "+00:00"))
    ahora = datetime.now(timezone.utc)
    horas_transcurridas = (ahora - fecha_recibido).total_seconds() / 3600

    if horas_transcurridas <= 12:
        return "🟢", "Verde (Tiempo Seguro)", f"{max(0, int(24 - horas_transcurridas))}h restante"
    elif horas_transcurridas <= 18:
        return "🟡", "Amarillo (Plazo Medio)", f"{max(0, int(24 - horas_transcurridas))}h restante"
    elif horas_transcurridas <= 24:
        return "🟠", "Naranja (Fase Crítica)", f"{max(0, int(24 - horas_transcurridas))}h restante"
    else:
        return "🔴", "Rojo (SLA Vencido)", f"{int(horas_transcurridas - 24)}h de retraso"

# =========================================================================
# INTERFAZ GRÁFICA DE USUARIO (STREAMLIT CLIENT-SIDE)
# =========================================================================
st.set_page_config(page_title="ActivoPay Core", layout="wide")

# Gestión de sesión simulada para control de perfiles (Paso 2)
if "perfil" not in st.session_state:
    st.session_state["perfil"] = "NEGOCIOS"

# Barra de navegación lateral para conmutar perfiles de seguridad
st.sidebar.title("🔐 Seguridad y Acceso")
st.session_state["perfil"] = st.sidebar.selectbox("Seleccione su Rol", list(ROLES.keys()), format_func=lambda x: ROLES[x])

# =========================================================================
# VISTA GENERAL: PERFIL BANCA DE NEGOCIOS
# =========================================================================
if st.session_state["perfil"] == "NEGOCIOS":
    st.title("💼 Portal de Negocios y Red Comercial")
    
    tabs = st.tabs(["📥 Ingesta Masiva (Excel)", "📊 Tablero de Control de mis Solicitudes", "✏️ Pantalla de Subsanación"])
    
    # ---------------------------------------------------------------------
    # PASO 4 & 7: MÓDULO I - INGESTA MASIVA Y STAGING AREA
    # ---------------------------------------------------------------------
    with tabs[0]:
        st.header("Carga Masiva de Solicitudes (.xlsx)")
        archivo_cargado = st.file_uploader("Arrastre el archivo Excel estructurado de 23 columnas", type=["xlsx"])
        
        if archivo_cargado:
            df_crudo = pd.read_excel(archivo_cargado)
            df_staging = evaluar_duplicados_y_estructura(df_crudo)
            
            st.subheader("Grilla Editable en Pantalla (Staging Area)")
            st.info("💡 Corrija los campos marcados con alertas haciendo doble clic directo en la celda antes de procesar.")
            
            # Renderizado de la Grilla Interactiva del Paso 7
            df_grilla_editada = st.data_editor(
                df_staging,
                disabled=["Fila", "Alertas de Sistema"],
                hide_index=True,
                use_container_width=True
            )
            
            filas_invalidas = df_grilla_editada[df_grilla_editada["Aprobado"] == False]
            
            if len(filas_invalidas) > 0:
                st.error(f"⛔ Bloqueo de Ingesta: Existen {len(filas_invalidas)} filas con errores críticos o duplicados.")
            else:
                st.success("🟢 Datos validados y homologados correctamente. Todos los registros cumplen el Blueprint.")
                if st.button("Procesar Carga e Inyectar a Bandeja Técnica (Commit)"):
                    if supabase:
                        for _, r in df_grilla_editada.iterrows():
                            # Paso 10: Inyección exacta a la estructura de la base de datos
                            supabase.table("afiliaciones").insert({
                                "region": r["Región"], "ejecutivo": r["Ejecutivo"], "correo_ejecutivo": r["Correo del Ejecutivo"],
                                "estatus": r["Estatus Mapeado"], "estatus_original_excel": r["Estatus Original Excel"],
                                "nombre_empresa": r["Nombre de la Empresa"], "rif": r["RIF"], "numero_cta": r["Cuenta Normalizada"],
                                "telefono_empresa": r["Teléfono"], "rubro": r["Rubro"], "numero_personas": int(r["Nro Usuarios"]),
                                "nombre_master": r["Nombre Master"], "ci_master": r["C.I. Master"], "correo_master": r["Correo Master"],
                                "nombre_secundario": r["Nombre Secundario"], "ci_secundario": r["C.I. Secundario"], "correo_secundario": r["Correo Secundario"]
                            }).execute()
                        st.balloons()
                        st.success("🚀 Registros guardados en Supabase. ¡Semáforo de SLA inicializado a 24 horas!")

    # ---------------------------------------------------------------------
    # PASO 4: MÓDULO II - TABLERO DE CONTROL PERSONALIZADO
    # ---------------------------------------------------------------------
    with tabs[1]:
        st.header("Monitoreo de Solicitudes Activas")
        if supabase:
            # Filtro restrictivo de seguridad: Solo ve lo suyo (Jerarquía del Paso 2)
            correo_usuario = "ejecutivo_demo@banco.com" 
            res_casos = supabase.table("afiliaciones").select("*").eq("correo_ejecutivo", correo_usuario).execute()
            
            if res_casos.data:
                df_casos = pd.DataFrame(res_casos.data)
                st.dataframe(df_casos[["id", "nombre_empresa", "rif", "numero_cta", "estatus", "fecha_recibido"]], use_container_width=True)
            else:
                st.info("No posees solicitudes activas registradas en tu bandeja.")

    # ---------------------------------------------------------------------
    # PASO 4: MÓDULO III - LOGICA DE PANTALLA DE SUBSANACIÓN GUIADA
    # ---------------------------------------------------------------------
    with tabs[2]:
        st.header("Subsanación de Solicitudes Devueltas (Evita Duplicidad)")
        id_subsanar = st.text_input("Ingrese el ID de la solicitud con alerta naranja en su bandeja")
        
        if id_subsanar and supabase:
            # Control de Estado: Validar que sea un registro devuelto por el técnico (Paso 4)
            data_caso = supabase.table("afiliaciones").select("*").eq("id", id_subsanar).eq("estatus", "3. Rechazado (Por Subsanar)").execute()
            
            if data_caso.data:
                caso = data_caso.data[0]
                st.warning(f"⚠️ Nota de Integración Técnica: {caso.get('observaciones', 'Revisar datos de cuenta')}")
                
                # Campos bloqueados vs editables para proteger la auditoría
                st.text_input("Empresa (Bloqueado)", value=caso["nombre_empresa"], disabled=True)
                st.text_input("RIF (Bloqueado)", value=caso["rif"], disabled=True)
                
                # Campo Editable Objeto del Error
                nueva_cuenta = st.text_input("Corregir Número de Cuenta (20 dígitos o corto)", value=caso["numero_cta"])
                nota_ejecutivo = st.text_area("Comentarios de Subsanación para el Técnico")
                
                if st.button("Enviar Corrección"):
                    # Aplicar normalización en caliente al dato modificado antes del re-envío
                    cuenta_arreglada = normalizar_cuenta_10_digitos(nueva_cuenta)
                    
                    # Guardar y Resetear SLA a cero (Paso 4 - Módulo III)
                    bitacora_actualizada = f"{caso.get('observaciones','') or ''} | [Subsanado: {nota_ejecutivo}]"
                    supabase.table("afiliaciones").update({
                        "numero_cta": cuenta_arreglada,
                        "estatus": "1. Pendiente", # Conmuta estado
                        "fecha_recibido": datetime.now(timezone.utc).isoformat(), # Resetea semáforo a cero (Verde)
                        "observaciones": bitacora_actualizada
                    }).eq("id", id_subsanar).execute()
                    
                    st.success("🔄 Caso re-inyectado exitosamente en la Bandeja Técnica. Semáforo reiniciado a 24 horas.")
            else:
                st.error("ID inválido o el caso no se encuentra en estado '3. Rechazado (Por Subsanar)'.")

# =========================================================================
# VISTA GENERAL: PERFIL ADMINISTRADOR (INTEGRACIÓN TÉCNICA)
# =========================================================================
else:
    st.title("🛠️ Consola Técnica de Integración de Aplicaciones")
    
    adm_tabs = st.tabs(["📥 Bandeja Global (FIFO)", "🗄️ Repositorio Central (Lista Muerta)", "📊 Dashboard de Gestión (Alta Gerencia)"])
    
    # ---------------------------------------------------------------------
    # PASO 5: MÓDULO II - BANDEJA GLOBAL DE OPERACIONES (EVALUACIÓN TÉCNICA)
    # ---------------------------------------------------------------------
    with adm_tabs[0]:
        st.header("Solicitudes Pendientes por Evaluar (Orden FIFO)")
        if supabase:
            res_pendientes = supabase.table("afiliaciones").select("*").in_("estatus", ["1. Pendiente", "2. En Revisión"]).order("fecha_recibido").execute()
            
            if res_pendientes.data:
                for idx, p in enumerate(res_pendientes.data):
                    # Calcular Semáforo de SLA dinámico en pantalla
                    color, fase, tiempo = calcular_semaforo_sla(p.get("fecha_recibido"))
                    
                    with st.expander(f"{color} Empresa: {p['nombre_empresa']} | SLA: {tiempo} ({fase})"):
                        st.write(f"**Ejecutivo:** {p['ejecutivo']} | **Región:** {p['region']}")
                        st.write(f"**Cuenta en Base de Datos (10 Digitos):** {p['numero_cta']}")
                        st.write(f"**RIF:** {p['rif']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            # Salida 1: Cierre Técnico Aprobado (Paso 5 - Módulo II)
                            wh_codigo = st.text_input("Código Webhook (WH) Manual Obligatorio", key=f"wh_{idx}")
                            if st.button("Aprobar Afiliación ✔️", key=f"ap_{idx}"):
                                if wh_codigo.strip() == "":
                                    st.error("Error: Debe digitar manualmente el código WH para aprobar.")
                                else:
                                    supabase.table("afiliaciones").update({
                                        "estatus": "4. Afiliado (Espera de Acompañamiento)",
                                        "wh": wh_codigo,
                                        "fecha_afiliado": datetime.now(timezone.utc).isoformat(),
                                        "afiliador": "Analista Técnico Activo"
                                    }).eq("id", p["id"]).execute()
                                    st.success("Afiliación completada de forma limpia.")
                                    st.rerun()
                        with col2:
                            # Salida 2: Rechazar y devolver para subsanación
                            motivo_rechazo = st.text_area("Observaciones e Inconsistencias Detectadas", key=f"obs_{idx}")
                            if st.button("Rechazar y Devolver ❌", key=f"re_{idx}"):
                                supabase.table("afiliaciones").update({
                                    "estatus": "3. Rechazado (Por Subsanar)",
                                    "observaciones": motivo_rechazo
                                }).eq("id", p["id"]).execute()
                                st.warning("Caso devuelto a la red comercial.")
                                st.rerun()
            else:
                st.info("Bandeja limpia. No hay solicitudes pendientes por procesar.")

    # ---------------------------------------------------------------------
    # PASO 5: MÓDULO IV - REPOSITORIO BASE DE DATOS (LISTA MUERTA)
    # ---------------------------------------------------------------------
    with adm_tabs[1]:
        st.header("Módulo de Consulta Centralizado (Solo Lectura Puro)")
        st.caption("Espejo masivo omnipotente con los 191 registros históricos y flujos nuevos.")
        
        if supabase:
            res_global = supabase.table("afiliaciones").select("*").execute()
            if res_global.data:
                df_global = pd.DataFrame(res_global.data)
                
                # Filtros Colapsables de Auditoría Cruzada (Paso 5)
                with st.sidebar.expander("🔍 Filtros de Auditoría"):
                    region_f = st.multiselect("Filtrar por Región", df_global["region"].unique())
                    estatus_f = st.multiselect("Filtrar por Estatus", df_global["estatus"].unique())
                
                df_filtrado = df_global.copy()
                if region_f:
                    df_filtrado = df_filtrado[df_filtrado["region"].isin(region_f)]
                if estatus_f:
                    df_filtrado = df_filtrado[df_filtrado["estatus"].isin(estatus_f)]
                    
                st.dataframe(df_filtrado, use_container_width=True)
                
                # Exportación Nativa a Excel
                st.download_button(
                    label="📥 Exportar Repositorio Completo a Excel (.xlsx)",
                    data=df_filtrado.to_csv(index=False).encode('utf-8'),
                    file_name="repositorio_activopay_core.csv",
                    mime="text/csv"
                )

    # ---------------------------------------------------------------------
    # PASO 6: DASHBOARD DE GESTIÓN (ALTA GERENCIA)
    # ---------------------------------------------------------------------
    with adm_tabs[2]:
        st.header("Dashboard de Gestión Estatus Estratégico")
        if supabase and res_global.data:
            df_dash = pd.DataFrame(res_global.data)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Clientes Captados", len(df_dash))
            with c2:
                # Medidor de Eficiencia del SLA del Producto
                pendientes = len(df_dash[df_dash["estatus"] == "1. Pendiente"])
                st.metric("Casos Técnicos en Cola", pendientes)
            with c3:
                # Tasa de Conversión a Producción (Paso 6 - Bloque B)
                en_prod = len(df_dash[df_dash["estatus"] == "5. En Producción"])
                tasa = (en_prod / len(df_dash) * 100) if len(df_dash) > 0 else 0
                st.metric("Tasa de Conversión Real", f"{tasa:.2f}%")
                
            st.subheader("Distribución Geográfica de la Cartera (Paso 6 - Bloque C)")
            st.bar_chart(df_dash["region"].value_counts())