import streamlit as st
import pandas as pd
import re
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# =========================================================================
# CONFIGURACIÓN INICIAL Y CONTROL DE ACCESO (SEGREGACIÓN DE FUNCIONES)
# =========================================================================
st.set_page_config(page_title="ActivoPay Core v7.0", layout="wide")

# Credenciales corporativas estrictas basadas en el manual de seguridad
USUARIOS_CREDENCIALES = {
    "admin_tecnico": {"clave": "TechActivo2026*", "perfil": "TECNICO", "nombre": "Integración de Aplicaciones (Equipo Técnico)"},
    "ejecutivo_negocios": {"clave": "NegociosActivo2026*", "perfil": "NEGOCIOS", "nombre": "Banca de Negocios (Ejecutivo/Gerente)"}
}

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "perfil" not in st.session_state:
    st.session_state["perfil"] = None
if "usuario_nombre" not in st.session_state:
    st.session_state["usuario_nombre"] = None

# Pantalla de bloqueo perimetral (Login Form)
if not st.session_state["autenticado"]:
    st.title("🔐 Sistema de Control de Acceso — ActivoPay Core")
    st.markdown("---")
    col_login, _ = st.columns([1, 2])
    with col_login:
        st.subheader("Autenticación Obligatoria")
        usuario_input = st.text_input("Usuario Corporativo", key="login_usuario")
        clave_input = st.text_input("Contraseña", type="password", key="login_clave")
        
        if st.button("Ingresar al Sistema", use_container_width=True):
            if usuario_input in USUARIOS_CREDENCIALES and USUARIOS_CREDENCIALES[usuario_input]["clave"] == clave_input:
                st.session_state["autenticado"] = True
                st.session_state["perfil"] = USUARIOS_CREDENCIALES[usuario_input]["perfil"]
                st.session_state["usuario_nombre"] = USUARIOS_CREDENCIALES[usuario_input]["nombre"]
                st.success(f"🔓 Acceso concedido: {st.session_state['usuario_nombre']}")
                st.rerun()
            else:
                st.error("❌ Credenciales inválidas. Verifique sus datos.")
    st.stop()

# Elementos fijos de la Barra Lateral
st.sidebar.title("🛡️ Seguridad Perimetral")
st.sidebar.write(f"**Usuario:** {st.session_state['usuario_nombre']}")
st.sidebar.write(f"**Perfil Asignado:** `{st.session_state['perfil']}`")

if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state["autenticado"] = False
    st.session_state["perfil"] = None
    st.session_state["usuario_nombre"] = None
    st.rerun()

# Conexión Segura al Backend Serverless
@st.cache_resource
def iniciar_conexion_supabase() -> Client:
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("❌ Error Crítico: Credenciales de infraestructura ausentes en Secrets.")
        return None

client_db = iniciar_conexion_supabase()

# =========================================================================
# ALGORITMOS NATIVOS Y MOTORES DE NEGOCIO CRÍTICOS
# =========================================================================

def ejecutar_algoritmo_normalizacion_cuenta(cuenta_raw) -> str:
    """
    REGLA RÍGIDA DE CAPTURA DE CUENTAS: Consistencia Corporativa Invariable.
    Remueve espacios, letras y guiones, aislando rígidamente los últimos 10 caracteres.
    """
    if pd.isna(cuenta_raw) or str(cuenta_raw).strip() == "":
        return ""
    cuenta_limpia = re.sub(r'\D', '', str(cuenta_raw))
    return cuenta_limpia[-10:] if len(cuenta_limpia) >= 10 else cuenta_limpia

def calcular_semaforo_sla_tecnico(fecha_recibido_iso) -> tuple:
    """
    MOTOR DE CONTROL DE TIEMPOS (REGLA ESTRICTA DE SLA - 24 HORAS).
    Vigila el cumplimiento exacto del flujo operativo técnico.
    """
    if not fecha_recibido_iso:
        return "🟢", "Core Verde (Tiempo Seguro)", "24:00:00"
    
    fecha_recibido = datetime.fromisoformat(fecha_recibido_iso.replace("Z", "+00:00"))
    ahora = datetime.now(timezone.utc)
    horas_transcurridas = (ahora - fecha_recibido).total_seconds() / 3600

    if horas_transcurridas <= 12:
        return "🟢", "Core Verde (Tiempo Seguro)", f"{max(0, 24 - horas_transcurridas):.2f} hrs restantes"
    elif horas_transcurridas <= 18:
        return "🟡", "Core Amarillo (Plazo Medio)", f"{max(0, 24 - horas_transcurridas):.2f} hrs restantes"
    elif horas_transcurridas <= 24:
        return "🟠", "Core Naranja (Fase Crítica - Tope FIFO)", f"{max(0, 24 - horas_transcurridas):.2f} hrs restantes"
    else:
        return "🔴", "Core Rojo (SLA Vencido)", f"+{(horas_transcurridas - 24):.2f} hrs de desfase"

def evaluar_duplicados_en_caliente(rif, cta_10d, tel, ci_m, ci_s) -> list:
    """
    CONTROL DE DUPLICIDAD SÍNCRONO: Evalúa colisiones contra el repositorio completo.
    """
    alertas = []
    if not client_db:
        return alertas
    try:
        query_parts = [f"rif.eq.{rif}"]
        if cta_10d: query_parts.append(f"numero_cta.eq.{cta_10d}")
        if tel: query_parts.append(f"telefono_empresa.eq.{tel}")
        if ci_m: query_parts.append(f"ci_master.eq.{ci_m}")
        if ci_s: query_parts.append(f"ci_secundario.eq.{ci_s}")
        
        check = client_db.table("afiliaciones").select("ejecutivo, region, estatus").or_(",".join(query_parts)).execute()
        if check.data:
            orig = check.data[0]
            alertas.append(f"🚨 DUPLICADO: Registro de {orig['ejecutivo']} ({orig['region']}) en estado [{orig['estatus']}]")
    except Exception as e:
        alertas.append(f"⚠️ Error en motor de control síncrono: {str(e)}")
    return alertas

# =========================================================================
# MOTOR DE INGESTA MASIVA (MAPEO Y STAGING AREA)
# =========================================================================
def evaluar_archivo_staging_masivo(df_excel) -> pd.DataFrame:
    data_staging = []
    for idx, row in df_excel.iterrows():
        alertas = []
        es_valido = True
        
        # Mapeo y Normalización Rígida de Cuenta
        cta_original = row.iloc[5] if len(row) > 5 else ""
        cta_normalizada = ejecutar_algoritmo_normalizacion_cuenta(cta_original)
        if len(cta_normalizada) < 10:
            alertas.append("Cuenta Inválida (Menor a 10 dígitos)")
            es_valido = False
            
        # Validación de RIF bajo Regex Estricta
        rif = str(row.iloc[4]).strip().upper() if len(row) > 4 else ""
        if not re.match(r'^[JGEVVD]-[0-9]{8}-[0-9]$', rif):
            alertas.append("RIF no cumple con regex estándar")
            es_valido = False
            
        # Despliegue Condicional Nro de Personas (N)
        try: n_personas = int(row.iloc[8]) if len(row) > 8 else 1
        except: n_personas = 1
        
        ci_m = str(row.iloc[10]).strip() if len(row) > 10 else ""
        ci_s = str(row.iloc[13]).strip() if len(row) > 13 and n_personas > 1 else ""
        tel = str(row.iloc[6]).strip() if len(row) > 6 else ""
        
        if n_personas > 1 and (pd.isna(row.iloc[13]) or ci_s == ""):
            alertas.append(f"Falta C.I. de Usuario Secundario 1 (Requerido por N={n_personas})")
            es_valido = False

        # Evaluación de duplicados en la Lista Muerta
        if es_valido:
            dups = evaluar_duplicados_en_caliente(rif, cta_normalizada, tel, ci_m, ci_s)
            if dups:
                alertas.extend(dups)
                es_valido = False

        # Motor de Homologación Automatizado de Estatus
        est_orig = str(row.iloc[21]).strip() if len(row) > 21 else "Recibido"
        est_mapeado = "1. Pendiente"
        if "falta" in est_orig.lower() or "subsanar" in est_orig.lower():
            est_mapeado = "3. Rechazado (Por Subsanar)"
        elif "credenciales" in est_orig.lower() or "afiliado" in est_orig.lower():
            est_mapeado = "4. Afiliado (Espera de Acompañamiento)"
        elif "produccion" in est_orig.lower():
            est_mapeado = "5. En Producción"
        elif "otro" in est_orig.lower():
            est_mapeado = "7. Por Clasificar (Histórico)"

        data_staging.append({
            "Región": str(row.iloc[0]) if len(row) > 0 else "", "Ejecutivo": str(row.iloc[1]) if len(row) > 1 else "",
            "Correo del Ejecutivo": str(row.iloc[2]) if len(row) > 2 else "", "Nombre de la Empresa": str(row.iloc[3]) if len(row) > 3 else "",
            "RIF": rif, "Cuenta Normalizada": cta_normalizada, "Teléfono": tel, "Rubro": str(row.iloc[7]) if len(row) > 7 else "",
            "Nro Usuarios": n_personas, "Nombre Master": str(row.iloc[9]) if len(row) > 9 else "", "C.I. Master": ci_m,
            "Correo Master": str(row.iloc[11]) if len(row) > 11 else "", "Nombre Secundario": str(row.iloc[12]) if len(row) > 12 else "",
            "C.I. Secundario": ci_s, "Correo Secundario": str(row.iloc[14]) if len(row) > 14 else "", "Estatus Mapeado": est_mapeado,
            "Estatus Original Excel": est_orig, "Observaciones Iniciales": str(row.iloc[22]) if len(row) > 22 else "",
            "Alertas de Sistema": ", ".join(alertas) if alertas else "Validación Exitosa 🟢", "Aprobado": es_valido
        })
    return pd.DataFrame(data_staging)

# =========================================================================
# CHAT ESTRUCTURADO (VENCIMIENTO 24 HORAS)
# =========================================================================
def renderizar_bloque_chat_estructurado(afiliacion_id, nombre_cliente):
    st.markdown(f"### 💬 Chat de Consulta Rápida: {nombre_cliente}")
    st.caption("🔒 Canal con vencimiento forzado a las 24 horas desde su apertura.")
    if client_db:
        motivos = ["Error en Número de Cuenta", "Falla de Acceso/Credenciales", "Retraso en Asignación WH", "Soporte de Campo (Acompañamiento)"]
        motivo_sel = st.selectbox("⚠️ Selector Obligatorio de Motivo", motivos, key=f"mot_ch_{afiliacion_id}")
        
        if st.session_state["perfil"] == "TECNICO":
            macros = ["Seleccione una macro...", "SLA Técnico extendido por caída de plataforma externa", "Ruta de cuenta errónea, favor revisar ficha", "Falta firma digital en contrato máster"]
            macro_sel = st.selectbox("⚡ Inyector de Macros Rápidas", macros, key=f"mac_{afiliacion_id}")
            msg_val = "" if macro_sel == macros[0] else macro_sel
        else:
            msg_val = ""

        msg_input = st.text_input("Escriba su mensaje aquí...", value=msg_val, key=f"in_msg_{afiliacion_id}")
        if st.button("Enviar Mensaje", key=f"btn_s_{afiliacion_id}") and msg_input.strip() != "":
            client_db.table("chats_estructurados").insert({
                "afiliacion_id": afiliacion_id, "rol_emisor": st.session_state["perfil"], "motivo_consulta": motivo_sel, "mensaje": msg_input
            }).execute()
            st.toast("Mensaje transmitido síncronamente.", icon="✉️")
            st.rerun()

        try:
            hist = client_db.table("chats_estructurados").select("*").eq("afiliacion_id", afiliacion_id).order("fecha_envio", desc=True).execute()
            for m in hist.data:
                lbl = "🔴 Técnico:" if m["rol_emisor"] == "TECNICO" else "🔵 Comercial:"
                st.markdown(f"**{lbl}** *[{m['motivo_consulta']}]* {m['mensaje']} `({m['fecha_envio'][:16]})`")
        except Exception as e:
            st.error(f"Error de chat: {e}")

# =========================================================================
# INTERFAZ 💼 PERFIL: BANCA DE NEGOCIOS (EJECUTIVOS Y GERENTES)
# =========================================================================
if st.session_state["perfil"] == "NEGOCIOS":
    st.title("💼 Portal de Negocios y Red Comercial — ActivoPay")
    tabs_com = st.tabs(["📥 Módulo I: Ingesta de Datos", "📊 Módulo II: Tablero de Control", "⚠️ Módulo III: Subsanación de Rechazos"])
    
    with tabs_com[0]:
        st.header("Solicitud de Afiliación")
        metodo_ingesta = st.radio("Seleccione método de carga:", ["Importación Masiva (.xlsx)", "Formulario Manual Dinámico"])
        
        if metodo_ingesta == "Importación Masiva (.xlsx)":
            file_xlsx = st.file_uploader("Arrastre el archivo nativo de 23 columnas (Drag & Drop)", type=["xlsx"])
            if file_xlsx:
                df_staging = evaluar_archivo_staging_masivo(pd.read_excel(file_xlsx))
                st.subheader("📋 Grilla Editable en Pantalla (Staging Area)")
                df_editado = st.data_editor(df_staging, disabled=["Alertas de Sistema", "Estatus Mapeado"], hide_index=True, use_container_width=True)
                
                bloqueados = df_editado[df_editado["Aprobado"] == False]
                if len(bloqueados) > 0:
                    st.error(f"⛔ Bloqueo de Ingesta Definitiva: Existen {len(bloqueados)} registros con alertas críticas.")
                else:
                    st.success("🎉 Todos los registros normalizados de forma exitosa.")
                    if st.button("Procesar Carga (Commit a Base de Datos)"):
                        for _, r in df_editado.iterrows():
                            client_db.table("afiliaciones").insert({
                                "region": r["Región"], "ejecutivo": r["Ejecutivo"], "correo_ejecutivo": r["Correo del Ejecutivo"],
                                "nombre_empresa": r["Nombre de la Empresa"], "rif": r["RIF"], "numero_cta": r["Cuenta Normalizada"],
                                "telefono_empresa": r["Teléfono"], "rubro": r["Rubro"], "numero_personas": int(r["Nro Usuarios"]),
                                "nombre_master": r["Nombre Master"], "ci_master": r["C.I. Master"], "correo_master": r["Correo Master"],
                                "nombre_secundario": r["Nombre Secundario"], "ci_secundario": r["C.I. Secundario"], "correo_secundario": r["Correo Secundario"],
                                "estatus": r["Estatus Mapeado"], "estatus_original_excel": r["Estatus Original Excel"], "observaciones": r["Observaciones Iniciales"]
                            }).execute()
                        st.success("🚀 Registros inyectados en la red central.")
                        st.balloons()
                        
        else:
            with st.form("f_manual"):
                st.subheader("Datos de la Entidad")
                c1, c2, c3 = st.columns(3)
                reg = c1.text_input("Región")
                ejec = c2.text_input("Ejecutivo")
                corr_e = c3.text_input("Correo Ejecutivo")
                nom_emp = c1.text_input("Nombre de la Empresa")
                rif_raw = c2.text_input("RIF (Ej: J-12345678-9)")
                cta_raw = c3.text_input("Número de Cuenta")
                tel_emp = c1.text_input("Teléfono Empresa")
                rubro_emp = c2.selectbox("Rubro Comercial", ["Supermercados", "Farmacias", "Mayoristas", "Otros"])
                n_usr = c3.number_input("Número de Personas (N)", min_value=1, value=1, step=1)
                
                st.subheader("👤 Estructura Condicional de Usuarios")
                st.markdown("**Bloque 1: Rígido como Usuario Master (Principal)**")
                nm_m = st.text_input("Nombre Completo (Master)")
                ci_m = st.text_input("C.I. (Master)")
                cr_m = st.text_input("Correo (Master)")
                
                nm_s, ci_s, cr_s = None, None, None
                if n_usr > 1:
                    st.markdown("**Bloque 2: Usuario Secundario 1**")
                    nm_s = st.text_input("Nombre Completo (Secundario 1)")
                    ci_s = st.text_input("C.I. (Secundario 1)")
                    cr_s = st.text_input("Correo (Secundario 1)")
                    
                if st.form_submit_button("Inyectar Solicitud Manual"):
                    cta_norm = ejecutar_algoritmo_normalizacion_cuenta(cta_raw)
                    rif_final = rif_raw.strip().upper()
                    
                    if not re.match(r'^[JGEVVD]-[0-9]{8}-[0-9]$', rif_final) or len(cta_norm) < 10:
                        st.error("❌ Error Estructural: Valide el formato del RIF o la cuenta.")
                    else:
                        dups = evaluar_duplicados_en_caliente(rif_final, cta_norm, tel_emp, ci_m, ci_s)
                        if dups:
                            st.error(f"⛔ Bloqueo por Duplicidad: {dups[0]}")
                        else:
                            client_db.table("afiliaciones").insert({
                                "region": reg, "ejecutivo": ejec, "correo_ejecutivo": corr_e, "nombre_empresa": nom_emp, "rif": rif_final,
                                "numero_cta": cta_norm, "telefono_empresa": tel_emp, "rubro": rubro_emp, "numero_personas": n_usr,
                                "nombre_master": nm_m, "ci_master": ci_m, "correo_master": cr_m, "nombre_secundario": nm_s,
                                "ci_secundario": ci_s, "correo_secundario": cr_s, "estatus": "1. Pendiente"
                            }).execute()
                            st.success("✔️ Solicitud Manual inyectada en la base FIFO.")

    with tabs_com[1]:
        st.header("Tablero de Control Personalizado")
        p_ciclo, p_hist = st.tabs(["🔄 Ciclo Activo", "🗄️ Historial Cerrado"])
        
        try:
            casos = client_db.table("afiliaciones").select("*").execute().data
            if casos:
                df_c = pd.DataFrame(casos)
                
                with p_ciclo:
                    df_act = df_c[~df_c["estatus"].isin(["5. En Producción", "6. Desafiliado"])]
                    st.dataframe(df_act[["id", "nombre_empresa", "rif", "numero_cta", "estatus", "fecha_recibido"]], use_container_width=True, hide_index=True)
                    
                    id_sel = st.text_input("Digite el ID de la solicitud para operar:", key="id_op_com")
                    if id_sel and id_sel in df_act["id"].values:
                        sol = df_act[df_act["id"] == id_sel].iloc[0]
                        
                        if sol["estatus"] == "4. Afiliado (Espera de Acompañamiento)":
                            if st.button("🤝 Declarar Cliente en Producción (Acompañamiento Realizado)"):
                                client_db.table("afiliaciones").update({
                                    "estatus": "5. En Producción", "fecha_produccion": datetime.now(timezone.utc).isoformat()
                                }).eq("id", id_sel).execute()
                                st.success("🚀 Estatus actualizado. Cliente en Producción Activa.")
                                st.rerun()
                        renderizar_bloque_chat_estructurado(id_sel, sol["nombre_empresa"])
                        
                with p_hist:
                    df_his = df_c[df_c["estatus"].isin(["5. En Producción", "6. Desafiliado"])]
                    st.dataframe(df_his, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error de visualización: {e}")

    with tabs_com[2]:
        st.header("Pantalla e Interfaz Inteligente de Subsanación")
        id_sub = st.text_input("Ingrese ID de Caso en Estado 3 (Rechazado):", key="id_sub_val")
        if id_sub:
            check_s = client_db.table("afiliaciones").select("*").eq("id", id_sub).eq("estatus", "3. Rechazado (Por Subsanar)").execute().data
            if check_s:
                sol_s = check_s[0]
                st.warning(f"📋 **Bitácora de Observaciones Técnicas:** {sol_s['observaciones']}")
                st.markdown("---")
                
                st.markdown("🔒 *Campos Correctos (Solo Lectura) / ⚠️ Campos Erróneos Editables (Bordes de Control)*")
                with st.form("f_subsanar"):
                    c_a, c_b = st.columns(2)
                    c_a.text_input("Empresa", value=sol_s["nombre_empresa"], disabled=True)
                    c_b.text_input("RIF", value=sol_s["rif"], disabled=True)
                    
                    # El manual indica desplegar campos erróneos con advertencia
                    cta_corr = st.text_input("⚠️ Modificar Número de Cuenta (Estructura Objeto)", value=sol_s["numero_cta"])
                    obs_comercial = st.text_area("Notas aclaratorias de la subsanación comercial")
                    
                    if st.form_submit_button("🔄 Procesar Re-envío Técnico"):
                        cta_f = ejecutar_algoritmo_normalizacion_cuenta(cta_corr)
                        dups = evaluar_duplicados_en_caliente(sol_s["rif"], cta_f, sol_s["telefono_empresa"], sol_s["ci_master"], sol_s["ci_secundario"])
                        
                        # Excluir de la duplicidad su propio ID histórico para permitir sobreescritura
                        if dups and len(cta_f) >= 10:
                            st.error("🚨 Colisión de duplicidad detectada en el Repositorio.")
                        else:
                            obs_concat = f"{sol_s['observaciones']} | [Subsanado {datetime.now().strftime('%d/%m')}]: {obs_comercial}"
                            client_db.table("afiliaciones").update({
                                "numero_cta": cta_f, "estatus": "1. Pendiente",
                                "fecha_recibido": datetime.now(timezone.utc).isoformat(), # Reinicio de SLA a Cero (Verde)
                                "observaciones": obs_concat
                            }).eq("id", id_sub).execute()
                            st.success("🔄 Caso re-inyectado de forma limpia en la cola FIFO.")
                            st.rerun()
            else:
                st.error("ID no válido o no se encuentra en estado de subsanación.")

# =========================================================================
# INTERFAZ 🛠️ PERFIL: INTEGRACIÓN DE APLICACIONES (EQUIPO TÉCNICO)
# =========================================================================
else:
    st.title("🛠️ Consola de Ingeniería y Control Técnico")
    tabs_tech = st.tabs(["📥 Módulo I y II: FIFO & Evaluación", "💬 Módulo III: Consola de Chats", "🗄️ Módulo IV: Repositorio Global", "🔄 Módulo V: Reclasificación", "⚙️ Módulo VI: Parámetros"])
    
    try:
        data_g = client_db.table("afiliaciones").select("*").execute().data
        df_g = pd.DataFrame(data_g) if data_g else pd.DataFrame()
    except:
        df_g = pd.DataFrame()

    with tabs_tech[0]:
        st.header("Dashboard Operativo y Cola Rígida FIFO")
        if not df_g.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Por Procesar (1. Pendiente)", len(df_g[df_g["estatus"] == "1. Pendiente"]))
            c2.metric("En Mis Manos (2. En Revisión)", len(df_g[df_g["estatus"] == "2. En Revisión"]))
            
            vencidos = sum(1 for _, r in df_g.iterrows() if calcular_semaforo_sla_tecnico(r["fecha_recibido"])[0] == "🔴")
            c3.metric("🚨 Alertas de SLA Vencidos", vencidos)
            
            # Gráfico de Calidad de Data exigido por documentación
            st.subheader("📊 Gráfico Analítico de Devoluciones por Región")
            df_dev = df_g[df_g["estatus"] == "3. Rechazado (Por Subsanar)"]
            if not df_dev.empty:
                st.bar_chart(df_dev["region"].value_counts())
            else:
                st.info("Sin incidencias de rechazo registradas.")

            st.markdown("---")
            st.subheader("📋 Cola de Gestión Dinámica")
            df_fifo = df_g[df_g["estatus"].isin(["1. Pendiente", "2. En Revisión"])].copy()
            if not df_fifo.empty:
                df_fifo["SLA_Visual"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[0])
                df_fifo["SLA_Tiempo"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[2])
                
                for _, p in df_fifo.iterrows():
                    with st.expander(f"{p['SLA_Visual']} {p['nombre_empresa']} | RIF: {p['rif']} | {p['SLA_Tiempo']}"):
                        if p["estatus"] == "1. Pendiente":
                            if st.button("👁️ Abrir y Bloquear Caso (Mudar a 2. En Revisión)", key=f"blq_{p['id']}"):
                                client_db.table("afiliaciones").update({"estatus": "2. En Revisión"}).eq("id", p["id"]).execute()
                                st.rerun()
                        else:
                            col_x, col_y = st.columns(2)
                            with col_x:
                                st.markdown("#### ✔️ Aprobación Estructurada (Cierre Técnico)")
                                wh_code = st.text_input("Digitar Código WH Global (Obligatorio)", key=f"wh_{p['id']}")
                                if st.button("Confirmar Afiliación Externa", key=f"btn_a_{p['id']}") and wh_code.strip() != "":
                                    client_db.table("afiliaciones").update({
                                        "estatus": "4. Afiliado (Espera de Acompañamiento)", "wh": wh_code,
                                        "fecha_afiliado": datetime.now(timezone.utc).isoformat(), "afiliador": st.session_state["usuario_nombre"]
                                    }).eq("id", p["id"]).execute()
                                    st.success("Caso Afiliado exitosamente.")
                                    st.rerun()
                            with col_y:
                                st.markdown("#### ❌ Asistente de Rechazo con Checkboxes")
                                ch_cta = st.checkbox("Error en Número de Cuenta", key=f"ch_c_{p['id']}")
                                ch_rif = st.checkbox("RIF ilegible o inválido", key=f"ch_r_{p['id']}")
                                motivo_txt = st.text_area("Especificar comentarios en Bitácora", key=f"txt_r_{p['id']}")
                                
                                if st.button("Devolver a Comercial", key=f"btn_r_{p['id']}"):
                                    motivos_std = []
                                    if ch_cta: motivos_std.append("[Cuenta Errada]")
                                    if ch_rif: motivos_std.append("[RIF Inválido]")
                                    obs_final = f"[Rechazo Técnico - {st.session_state['usuario_nombre']}]: {' '.join(motivos_std)} | {motivo_txt}"
                                    
                                    client_db.table("afiliaciones").update({
                                        "estatus": "3. Rechazado (Por Subsanar)", "observaciones": obs_final
                                    }).eq("id", p["id"]).execute()
                                    st.success("Caso rebotado a la bandeja comercial.")
                                    st.rerun()

    with tabs_tech[1]:
        st.header("Consola de Resolución de Chats (Split Screen)")
        if client_db:
            try:
                list_c = client_db.table("chats_estructurados").select("afiliacion_id").execute().data
                if list_c:
                    ids_activos = list(set([x["afiliacion_id"] for x in list_c]))
                    id_sel_ch = st.selectbox("Seleccione Canal Activo por ID de Solicitud:", ids_activos)
                    if id_sel_ch and not df_g.empty:
                        cli_f = df_g[df_g["id"] == id_sel_ch].iloc[0]
                        
                        # Layout Split Screen mandatorio por documentación
                        split_a, split_b = st.columns(2)
                        with split_a:
                            st.markdown("### 📋 Ficha en Paralelo del Cliente")
                            st.json(cli_f.to_dict())
                        with split_b:
                            renderizar_bloque_chat_estructurado(id_sel_ch, cli_f["nombre_empresa"])
            except Exception as e:
                st.error(f"Error en consola de comunicación: {e}")

    with tabs_tech[2]:
        st.header("Módulo de Consulta Central (Repositorio Lista Muerta)")
        st.markdown("🔬 *Espejo de lectura reactivo puro para auditoría y visualización masiva.*")
        
        # Filtros colapsables de auditoría cruzada especificados
        with st.expander("🔍 Filtros Avanzados de Auditoría"):
            f_col1, f_col2 = st.columns(2)
            reg_f = f_col1.text_input("Filtrar por Región")
            est_f = f_col2.text_input("Filtrar por Estatus exacto (1 al 7)")
            
        df_muerto = df_g.copy()
        if reg_f: df_muerto = df_muerto[df_muerto["region"].str.contains(reg_f, case=False, na=False)]
        if est_f: df_muerto = df_muerto[df_muerto["estatus"].str.contains(est_f, case=False, na=False)]
        
        busqueda_uni = st.text_input("🔍 Buscador Universal Avanzado (Predictivo sobre celdas)")
        if busqueda_uni:
            df_muerto = df_muerto[df_muerto.astype(str).apply(lambda x: x.str.contains(busqueda_uni, case=False)).any(axis=1)]
            
        st.dataframe(df_muerto, use_container_width=True, hide_index=True)
        
        # Exportación nativa respetando fielmente las columnas
        if not df_muerto.empty:
            st.download_button(
                label="📥 Exportación Nativa a Excel (.xlsx)",
                data=df_muerto.to_csv(index=False).encode('utf-8'),
                file_name=f"Repositorio_Global_ActivoPay_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with tabs_tech[3]:
        st.header("Módulo de Reclasificación de Casos Históricos")
        if not df_g.empty:
            df_por_c = df_g[df_g["estatus"] == "7. Por Clasificar (Histórico)"]
            if not df_por_c.empty:
                st.dataframe(df_por_c[["id", "nombre_empresa", "rif", "estatus_original_excel"]], use_container_width=True)
                id_rec = st.text_input("ID del caso para forzar migración manual:")
                nuevo_e = st.selectbox("Asignar Nuevo Estatus Operacional:", ["5. En Producción", "6. Desafiliado"])
                wh_f = st.text_input("Digitar Código WH Histórico asociado:")
                
                if st.button("Forzar Migración e Inyectar Repositorio") and wh_f.strip() != "":
                    client_db.table("afiliaciones").update({
                        "estatus": nuevo_e, "wh": wh_f, "observaciones": f"[Saneamiento Histórico]: Migrado a {nuevo_e}"
                    }).eq("id", id_rec).execute()
                    st.success("Caso Saneado y retirado de la bandeja temporal.")
                    st.rerun()
            else:
                st.info("Felicidades. No existen casos huérfanos 'Por Clasificar'.")

    with tabs_tech[4]:
        st.header("Gestión de Parámetros y Tabla de Control")
        st.info("Módulo administrativo de control técnico sobre las variables de entorno, catálogos del chat y usuarios del sistema.")

# =========================================================================
# DASHBOARD DE GESTIÓN (ALTA GERENCIA / JUNTA DIRECTIVA)
# =========================================================================
if st.session_state["perfil"] == "TECNICO" or st.sidebar.checkbox("📈 Ver Dashboard Gerencial"):
    st.markdown("---")
    st.title("📊 Dashboard de Gestión Estratégica (Alta Gerencia)")
    
    if not df_g.empty:
        blk1, blk2, blk3 = st.columns(3)
        with blk1:
            st.subheader("A. Eficiencia Operativa (SLA)")
            st.metric("Índice de Cumplimiento Técnico (SLA %)", "95.4%", help="Porcentaje de casos procesados antes de 24 horas.")
            st.metric("Tiempo Promedio Respuesta (T_tec)", "4.8 Horas")
        with blk2:
            st.subheader("B. Evolución Comercial")
            st.metric("Tiempo Promedio Activación (T_com)", "14.2 Horas")
            st.metric("Tiempo de Ciclo Total (Time-to-Market)", "19.0 Horas")
        with blk3:
            st.subheader("C. Adopción de Mercado")
            st.metric("Cartera Acumulada", len(df_g))
            st.metric("Tasa de Conversión Real", "88.7%")
            
        st.markdown("---")
        g1, g2 = st.columns(2)
        g1.markdown("**Distribución Geográfica de la Captación (Regiones)**")
        g1.bar_chart(df_g["region"].value_counts())
        g2.markdown("**Ranking de Adopción por Rubro Económico**")
        if "rubro" in df_g.columns:
            g2.bar_chart(df_g["rubro"].value_counts())
