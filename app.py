import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta, timezone
# IMPORTACIÓN ADICIONAL PARA LA INTEGRACIÓN DE SUPABASE
from supabase import create_client, Client

# =============================================================================
# MÓDULO 0: CONFIGURACIÓN PERIMETRAL, ESTILOS Y CONTROL DE SESIÓN ATÓMICO
# =============================================================================
st.set_page_config(
    page_title="ActivoPay Core v7.5 - Producción",
    layout="wide",
    initial_sidebar_state="expanded"
)

# INICIALIZACIÓN SEGURA DEL CLIENTE SUPABASE (CONEXIÓN PERMANENTE)
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.warning(f"⚠️ Alerta de Configuración: No se detectaron credenciales de Supabase en st.secrets. Modo Local activado. Error: {e}")
        return None

supabase: Client = init_supabase()

# Inyección de Estilos CSS Personalizados para la interfaz institucional
st.markdown("""
<style>
    .reportview-container { background: #f5f7f8; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: bold; }
    .card-negocios { background-color: #e3f2fd; padding: 15px; border-radius: 6px; border-left: 5px solid #1e88e5; margin-bottom: 10px; }
    .card-tecnico { background-color: #efebe9; padding: 15px; border-radius: 6px; border-left: 5px solid #6d4c41; margin-bottom: 10px; }
    .metric-box { background: #ffffff; padding: 10px; border-radius: 6px; box-shadow: 0px 1px 3px rgba(0,0,0,0.1); text-align: center; }
</style>
""", unsafe_allow_index=True)

# Inicialización de Estados de Sesión Críticos (Mecanismo Fallback en memoria)
if "perfil" not in st.session_state:
    st.session_state["perfil"] = "NEGOCIOS"
if "base_datos_central" not in st.session_state:
    st.session_state["base_datos_central"] = []
if "conversaciones_chats" not in st.session_state:
    st.session_state["conversaciones_chats"] = {}
if "staging_excel" not in st.session_state:
    st.session_state["staging_excel"] = None

# SINCRONIZACIÓN DE ENTRADA: Descargar datos desde Supabase a Session State al iniciar si la conexión está activa
if supabase and not st.session_state["base_datos_central"]:
    try:
        res = supabase.table("solicitudes").select("*").order("fecha_recibido", descending=False).execute()
        if res.data:
            st.session_state["base_datos_central"] = res.data
            # Sincronizar hilos de conversación correspondientes
            for row in res.data:
                sid = str(row["id"])
                chat_res = supabase.table("chats").select("*").eq("solicitud_id", sid).order("timestamp", descending=False).execute()
                st.session_state["conversaciones_chats"][sid] = chat_res.data if chat_res.data else []
    except Exception:
        pass

# =============================================================================
# MÓDULO 1: MOTOR DE VALIDACIÓN DE SINTAXIS Y NORMALIZACIÓN DE DATA (CUMPLIMIENTO)
# =============================================================================
def validar_rif(rif_str):
    if not rif_str: return False, None
    s = re.sub(r'[^A-Za-z0-9]', '', str(rif_str)).upper()
    if re.match(r'^[JVDG]-\d{8}-\d$', s): return True, s
    if re.match(r'^[JVDG]\d{9}$', s): return True, f"{s[0]}-{s[1:9]}-{s[9]}"
    if re.match(r'^\d{9}$', s): return True, f"J-{s[0:8]}-{s[8]}"
    return False, s

def validar_cuenta(cuenta_str):
    if not cuenta_str: return False, None
    c = re.sub(r'\D', '', str(cuenta_str))
    if len(c) == 20: return True, c
    return False, c

def validar_correo(correo_str):
    if not correo_str: return False
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(correo_str).strip()))

# =============================================================================
# MÓDULO 2: INTERFAZ DINÁMICA DE ENRUTAMIENTO (SIDEBAR CONTROL)
# =============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/10149/10149458.png", width=70)
    st.title("ActivoPay Core v7.5")
    st.subheader("Control de Acceso Perimetral")
    
    perfil_cambio = st.radio(
        "Seleccione Perfil Operativo:",
        ["NEGOCIOS", "TECNICO"],
        index=0 if st.session_state["perfil"] == "NEGOCIOS" else 1
    )
    if perfil_cambio != st.session_state["perfil"]:
        st.session_state["perfil"] = perfil_cambio
        st.rerun()
        
    st.divider()
    st.markdown("### Estado del Sistema")
    if supabase:
        st.success("⚡ Conectado a Supabase Cloud")
    else:
        st.warning("⚠️ Modo Local (Sin Persistencia)")
        
    st.info(f"Sesión Activa: {st.session_state['perfil']}")
    
    # Botón de purga total para desarrollo/pruebas locales
    if st.button("Resetear Memoria Local"):
        st.session_state["base_datos_central"] = []
        st.session_state["conversaciones_chats"] = {}
        st.session_state["staging_excel"] = None
        st.toast("Memoria local despejada", icon="🧹")
        st.rerun()

# =============================================================================
# MÓDULO 3: VISTA PERFIL NEGOCIOS - INGESTA, MASIVOS Y ADMISIÓN
# =============================================================================
if st.session_state["perfil"] == "NEGOCIOS":
    st.title("💼 Mesa de Control de Negocios y Admisión")
    st.caption("Módulo de ingesta manual, procesamiento masivo por lotes y subsanación comercial.")
    
    tab1, tab2, tab3 = st.tabs(["📝 Registro Manual Único", "📊 Carga Masiva (Excel/CSV)", "📂 Subsanación y Tracking"])
    
    with tab1:
        st.subheader("Formulario de Registro de Afiliación")
        with st.form("form_registro_manual", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                reg = st.selectbox("Región / Territorio", ["Capital", "Central", "Occidente", "Oriente", "Los Andes"])
                ejec = st.text_input("Nombre Ejecutivo Comercial")
                corr_e = st.text_input("Correo del Ejecutivo")
            with col2:
                nom_emp = st.text_input("Razón Social / Nombre Empresa")
                rif_raw = st.text_input("RIF Empresa (Ej: J-12345678-9)")
                cta_raw = st.text_input("Número de Cuenta Activo (20 dígitos)")
            with col3:
                tel_emp = st.text_input("Teléfono de Contacto")
                rubro_emp = st.selectbox("Rubro Comercial", ["Tecnología", "Alimentos", "Salud", "Retail", "Servicios", "Otros"])
                n_usr = st.number_input("Usuarios Maestros Requeridos", min_value=1, max_value=20, value=1)
                
            st.markdown("#### Datos de Identidad del Usuario Maestro Principal")
            c1, c2, c3 = st.columns(3)
            with c1: nm_m = st.text_input("Nombre Completo (Maestro)")
            with c2: ci_m = st.text_input("Cédula / Pasaporte (Maestro)")
            with c3: cr_m = st.text_input("Correo Electrónico (Maestro)")
            
            st.markdown("#### Datos de Identidad del Usuario Maestro Secundario (Contingencia)")
            cs1, cs2, cs3 = st.columns(3)
            with cs1: nm_s = st.text_input("Nombre Completo (Secundario)")
            with cs2: ci_s = st.text_input("Cédula / Pasaporte (Secundario)")
            with cs3: cr_s = st.text_input("Correo Electrónico (Secundario)")
            
            submit_manual = st.form_submit_button("Validar e Inyectar al Core")
            
            if submit_manual:
                v_rif, rif_final = validar_rif(rif_raw)
                v_cta, cta_norm = validar_cuenta(cta_raw)
                v_cr1 = validar_correo(corr_e)
                v_cr2 = validar_correo(cr_m)
                
                errores = []
                if not v_rif: errores.append(f"RIF Inválido estructuralmente: '{rif_raw}'")
                if not v_cta: errores.append(f"Cuenta debe poseer exactamente 20 dígitos numéricos.")
                if not v_cr1: errores.append("Correo de Ejecutivo no cumple con el estándar.")
                if not v_cr2: errores.append("Correo de Usuario Maestro no cumple con el estándar.")
                if not nom_emp.strip(): errores.append("La Razón Social de la empresa es requerida.")
                
                if errores:
                    for err in errores: st.error(f"❌ {err}")
                else:
                    # Generación de ID incremental consistente con base de datos
                    prox_id = str(len(st.session_state["base_datos_central"]) + 1)
                    
                    nueva_solicitud = {
                        "id": prox_id,
                        "region": reg, "ejecutivo": ejec, "correo_ejecutivo": corr_e,
                        "nombre_empresa": nom_emp, "rif": rif_final, "numero_cta": cta_norm,
                        "telefono_empresa": tel_emp, "rubro": rubro_emp, "numero_personas": int(n_usr),
                        "nombre_master": nm_m, "ci_master": ci_m, "correo_master": cr_m,
                        "nombre_secundario": nm_s, "ci_secundario": ci_s, "correo_secundario": cr_s,
                        "estatus": "1. Pendiente", "estatus_original_excel": "Manual",
                        "fecha_recibido": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # PERSISTENCIA EN SUPABASE (INSERCIÓN REAL)
                    if supabase:
                        try:
                            res_db = supabase.table("solicitudes").insert(nueva_solicitud).execute()
                            if res_db.data:
                                nueva_solicitud["id"] = str(res_db.data[0]["id"])
                        except Exception as e:
                            st.warning(f"⚠️ Error al persistir en Supabase: {e}. Se guardará en contingencia local.")
                    
                    # Persistencia local fallback
                    st.session_state["base_datos_central"].append(nueva_solicitud)
                    st.session_state["conversaciones_chats"][nueva_solicitud["id"]] = []
                    st.success(f"✔️ Solicitud procesada exitosamente. ID Asignado: {nueva_solicitud['id']}")
                    st.rerun()

    with tab2:
        st.subheader("Carga Masiva Automatizada por Estructura de Datos")
        uploaded_file = st.file_uploader("Suba archivo Excel (.xlsx, .xls) o CSV", type=["xlsx", "xls", "csv"])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.session_state["staging_excel"] = df
                st.success(f"Archivo cargado en Staging Area. Detectadas {len(df)} filas.")
            except Exception as e:
                st.error(f"Error procesando estructura de archivo: {e}")
                
        if st.session_state["staging_excel"] is not None:
            df_stg = st.session_state["staging_excel"]
            st.markdown("### Pre-visualización de Datos en Staging")
            st.dataframe(df_stg.head(5))
            
            # Mapeo posicional dinámico
            st.markdown("#### Configuración de Correspondencia de Columnas")
            columnas_disponibles = list(df_stg.columns)
            
            c_map1, c_map2, c_map3 = st.columns(3)
            with c_map1:
                col_empresa = st.selectbox("Columna Empresa/Razón Social", columnas_disponibles, index=0)
                col_rif = st.selectbox("Columna RIF", columnas_disponibles, index=min(1, len(columnas_disponibles)-1))
            with c_map2:
                col_cuenta = st.selectbox("Columna Número Cuenta", columnas_disponibles, index=min(2, len(columnas_disponibles)-1))
                col_master = st.selectbox("Columna Nombre Maestro", columnas_disponibles, index=min(3, len(columnas_disponibles)-1))
            with c_map3:
                col_correo = st.selectbox("Columna Correo Maestro", columnas_disponibles, index=min(4, len(columnas_disponibles)-1))
                
            if st.button("Ejecutar Procesamiento y Migración Masiva"):
                conteo_exito = 0
                conteo_error = 0
                
                for idx in range(len(df_stg)):
                    try:
                        row_data = df_stg.iloc[idx]
                        raw_rif = str(row_data[col_rif])
                        raw_cta = str(row_data[col_cuenta])
                        
                        v_rif, rif_f = validar_rif(raw_rif)
                        v_cta, cta_f = validar_cuenta(raw_cta)
                        
                        estatus_fila = "1. Pendiente" if (v_rif and v_cta) else "4. Rechazado por Datos Inválidos"
                        
                        p_id = str(len(st.session_state["base_datos_central"]) + 1)
                        sol_masiva = {
                            "id": p_id,
                            "region": "Masivo Hub",
                            "ejecutivo": "Carga Automática",
                            "correo_ejecutivo": "sistema@activopay.com",
                            "nombre_empresa": str(row_data[col_empresa]),
                            "rif": rif_f if v_rif else raw_rif,
                            "numero_cta": cta_f if v_cta else raw_cta,
                            "telefono_empresa": "No especificado",
                            "rubro": "General",
                            "numero_personas": 1,
                            "nombre_master": str(row_data[col_master]),
                            "ci_master": "Pendiente",
                            "correo_master": str(row_data[col_correo]) if validar_correo(str(row_data[col_correo])) else "invalido@correo.com",
                            "nombre_secundario": "", "ci_secundario": "", "correo_secundario": "",
                            "estatus": estatus_fila,
                            "estatus_original_excel": "Válido" if estatus_fila == "1. Pendiente" else "Estructura Corrupta",
                            "fecha_recibido": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # PERSISTENCIA EN SUPABASE PARA CARGA MASIVA
                        if supabase:
                            try:
                                res_db = supabase.table("solicitudes").insert(sol_masiva).execute()
                                if res_db.data:
                                    sol_masiva["id"] = str(res_db.data[0]["id"])
                            except Exception:
                                pass
                                
                        st.session_state["base_datos_central"].append(sol_masiva)
                        st.session_state["conversaciones_chats"][sol_masiva["id"]] = []
                        
                        if estatus_fila == "1. Pendiente": conteo_exito += 1
                        else: conteo_error += 1
                    except Exception:
                        conteo_error += 1
                        
                st.success(f"🎯 Migración Concluida. Inyectados con éxito: {conteo_exito} registros. Rechazados por reglas de negocio: {conteo_error}")
                st.session_state["staging_excel"] = None
                st.rerun()

    with tab3:
        st.subheader("Bandeja de Subsanación de Expedientes")
        if not st.session_state["base_datos_central"]:
            st.info("No existen solicitudes en el repositorio central.")
        else:
            df_tracking = pd.DataFrame(st.session_state["base_datos_central"])
            st.dataframe(df_tracking[["id", "nombre_empresa", "rif", "numero_cta", "estatus", "estatus_original_excel"]])
            
            st.markdown("---")
            st.subheader("Sección de Re-ajuste y Edición de Rechazos")
            
            opciones_subsanar = [item["id"] for item in st.session_state["base_datos_central"] if "4." in item["estatus"] or "Rechazado" in item["estatus"]]
            
            if not opciones_subsanar:
                st.success("🎉 No se encuentran expedientes rechazados pendientes de corrección.")
            else:
                id_sub = st.selectbox("Seleccione ID del expediente rechazado a subsanar:", opciones_subsanar)
                
                # Ubicar ítem
                idx_item = next((index for (index, d) in enumerate(st.session_state["base_datos_central"]) if d["id"] == id_sub), None)
                if idx_item is not None:
                    item_data = st.session_state["base_datos_central"][idx_item]
                    st.warning(f"Modificando Errores de Origen para: {item_data['nombre_empresa']}")
                    
                    nuevo_rif_sub = st.text_input("Corregir RIF:", value=item_data["rif"])
                    nueva_cta_sub = st.text_input("Corregir Cuenta (20 Dígitos):", value=item_data["numero_cta"])
                    
                    if st.button("Aplicar Subsanación y Re-enviar a Cola Técnico"):
                        v_r, r_f = validar_rif(nuevo_rif_sub)
                        v_c, c_f = validar_cuenta(nueva_cta_sub)
                        
                        if v_r and v_c:
                            st.session_state["base_datos_central"][idx_item]["rif"] = r_f
                            st.session_state["base_datos_central"][idx_item]["numero_cta"] = c_f
                            st.session_state["base_datos_central"][idx_item]["estatus"] = "1. Pendiente"
                            
                            # PERSISTENCIA EN SUPABASE (ACTUALIZACIÓN SUBSANACIÓN)
                            if supabase:
                                try:
                                    supabase.table("solicitudes").update({
                                        "rif": r_f, "numero_cta": c_f, "estatus": "1. Pendiente"
                                    }).eq("id", id_sub).execute()
                                except Exception as e:
                                    st.error(f"Error de persistencia externa: {e}")
                                    
                            st.success("Expediente saneado y re-enrutado a la cola de análisis técnico.")
                            st.rerun()
                        else:
                            st.error("Los datos ingresados aún violan las reglas sintácticas.")

# =============================================================================
# MÓDULO 4: VISTA PERFIL TÉCNICO - ANÁLISIS, SLA Y PROCESAMIENTO FIFO
# =============================================================================
elif st.session_state["perfil"] == "TECNICO":
    st.title("🛠️ Panel Técnico de Configuración e Infraestructura")
    st.caption("Procesamiento por priorización de colas FIFO, control de SLAs y mensajería directa.")
    
    if not st.session_state["base_datos_central"]:
        st.info("Bandeja de Entrada Técnica Vacía. No hay datos en el repositorio central.")
    else:
        df_tec = pd.DataFrame(st.session_state["base_datos_central"])
        
        # Filtrado FIFO: Solo mostrar los que no estén rechazados de origen por datos corruptos
        cola_fifo = df_tec[df_tec["estatus"] != "4. Rechazado por Datos Inválidos"].copy()
        
        # Métrica de Control Superior
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.metric("Total Solicitudes en Sistema", len(df_tec))
        with c_m2:
            st.metric("Pendientes en Cola FIFO", len(cola_fifo[cola_fifo["estatus"] == "1. Pendiente"]))
        with c_m3:
            st.metric("Casos Listos en Producción", len(df_tec[df_tec["estatus"] == "3. En Producción"]))
            
        st.markdown("### Cola de Casos Entrantes (Orden Cronológico de Entrada)")
        st.dataframe(cola_fifo[["id", "fecha_recibido", "nombre_empresa", "rif", "estatus"]])
        
        st.markdown("---")
        st.subheader("Consola Operativa de Gestión y Despliegue de Credenciales")
        
        opciones_operar = list(cola_fifo["id"].values)
        if not opciones_operar:
            st.info("Sin registros viables para operación.")
        else:
            id_operar = st.selectbox("Seleccione ID de Afiliación a Procesar:", opciones_operar)
            
            # Recuperar registro específico
            idx_op = next((i for (i, d) in enumerate(st.session_state["base_datos_central"]) if d["id"] == id_operar), None)
            
            if idx_op is not None:
                item_op = st.session_state["base_datos_central"][idx_op]
                
                # CÁLCULO DINÁMICO DE SLA (24 Horas)
                fecha_ingreso = datetime.fromisoformat(item_op["fecha_recibido"])
                fecha_limite = fecha_ingreso + timedelta(hours=24)
                ahora_utc = datetime.now(timezone.utc)
                tiempo_restante = fecha_limite - ahora_utc
                
                # Pintar Tarjeta informativa del estado del caso
                st.markdown(f"""
                <div class="card-tecnico">
                    <h4>Empresa: {item_op['nombre_empresa']} | RIF: {item_op['rif']}</h4>
                    <p><b>Estatus Actual del Flujo:</b> {item_op['estatus']}</p>
                    <p><b>Cuenta Destino Activo:</b> {item_op['numero_cta']}</p>
                    <p><b>Contacto Maestro:</b> {item_op['nombre_master']} ({item_op['correo_master']})</p>
                </div>
                """, unsafe_allow_index=True)
                
                # Visualización del Semáforo de SLA
                if tiempo_restante.total_seconds() > 0:
                    horas_disp = tiempo_restante.total_seconds() / 3600
                    st.success(f"⏳ SLA Vigente: Quedan {horas_disp:.2f} horas para completar la integración dentro del límite institucional.")
                else:
                    horas_exceso = abs(tiempo_restante.total_seconds()) / 3600
                    st.error(f"🚨 SLA VIOLADO: El caso excede el límite de respuesta reglamentario por {horas_exceso:.2f} horas.")
                
                # Botones de Acción de Estatus Avanzados
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    if st.button("Tomar Caso (En Revisión Técnico)"):
                        st.session_state["base_datos_central"][idx_op]["estatus"] = "2. En Revisión"
                        
                        # PERSISTENCIA EN SUPABASE (ACTUALIZACIÓN ESTATUS EN REVISIÓN)
                        if supabase:
                            try:
                                supabase.table("solicitudes").update({"estatus": "2. En Revisión"}).eq("id", id_operar).execute()
                            except Exception:
                                pass
                                
                        st.rerun()
                with col_btn2:
                    if st.button("Rechazar por Criterio Técnico / Documental"):
                        st.session_state["base_datos_central"][idx_op]["estatus"] = "4. Rechazado por Criterio Técnico"
                        
                        # PERSISTENCIA EN SUPABASE (ACTUALIZACIÓN ESTATUS RECHAZO TÉCNICO)
                        if supabase:
                            try:
                                supabase.table("solicitudes").update({"estatus": "4. Rechazado por Criterio Técnico"}).eq("id", id_operar).execute()
                            except Exception:
                                pass
                                
                        st.rerun()
                with col_btn3:
                    if st.button("🚀 DECLARAR EN PRODUCCIÓN (Puesta en Marcha)"):
                        st.session_state["base_datos_central"][idx_op]["estatus"] = "3. En Producción"
                        
                        # PERSISTENCIA EN SUPABASE (ACTUALIZACIÓN ESTATUS PRODUCCIÓN)
                        if supabase:
                            try:
                                supabase.table("solicitudes").update({"estatus": "3. En Producción"}).eq("id", id_operar).execute()
                            except Exception:
                                pass
                                
                        st.balloons()
                        st.rerun()

                # =============================================================================
                # MÓDULO 5: CANAL DE CONSULTA RÁPIDA (CHATS INTER-DEPARTAMENTALES)
                # =============================================================================
                st.markdown("---")
                st.subheader(f"✉️ Hilo de Mensajería y Alertas Internas - Caso #{id_operar}")
                
                # Asegurar existencia del nodo del chat en local
                if id_operar not in st.session_state["conversaciones_chats"]:
                    st.session_state["conversaciones_chats"][id_operar] = []
                
                # Formulario de Envío de Mensajes
                with st.form(f"chat_form_{id_operar}", clear_on_submit=True):
                    motivo_sel = st.selectbox("Motivo / Clasificación del Mensaje", 
                                              ["Falta Documento de Identidad", "Cuenta No Coincide con Nombre", 
                                               "Error en Token de Acceso", "Alerta de Fraude", "Consulta General"])
                    msg_input = st.text_area("Cuerpo del mensaje para la mesa de control:")
                    enviar_msg = st.form_submit_button("Inyectar Comentario al Historial")
                    
                    if enviar_msg and msg_input.strip() != "":
                        nuevo_mensaje = {
                            "solicitud_id": id_operar,
                            "emisor": st.session_state["perfil"],
                            "motivo": motivo_sel,
                            "msg": msg_input.strip(),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # PERSISTENCIA EN SUPABASE (INSERCIÓN DE MENSAJES REALES DE CHAT)
                        if supabase:
                            try:
                                supabase.table("chats").insert(nuevo_mensaje).execute()
                            except Exception as e:
                                st.warning(f"Error de persistencia del chat en Supabase: {e}")
                        
                        # Almacenar localmente en memoria fallback
                        st.session_state["conversaciones_chats"][id_operar].append(nuevo_mensaje)
                        st.toast("Mensaje registrado", icon="📨")
                        st.rerun()
                
                # Renderizado histórico del chat invertido (últimos mensajes arriba)
                historial_actual = st.session_state["conversaciones_chats"][id_operar]
                if not historial_actual:
                    st.info("No hay registros ni interacciones de soporte técnico previas en este caso.")
                else:
                    st.markdown("#### Bitácora del Caso")
                    for m in reversed(historial_actual):
                        prefix = "🔴 TÉCNICO" if m["emisor"] == "TECNICO" else "🔵 COMERCIAL"
                        try:
                            time_f = pd.to_datetime(m["timestamp"]).strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            time_f = "Hora no especificada"
                        st.markdown(f"**{prefix}** *[{m['motivo']}]* ({time_f}): {m['msg']}")
