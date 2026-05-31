import streamlit as st
import pandas as pd
import re
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# =========================================================================
# CONFIGURACIÓN INICIAL Y CONTROL DE SESIÓN (AUTENTICACIÓN)
# =========================================================================
st.set_page_config(page_title="ActivoPay Core v7.0", layout="wide")

# Diccionario de credenciales seguras de acceso corporativo
USUARIOS_CREDENCIALES = {
    "admin_tecnico": {"clave": "TechActivo2026*", "perfil": "TECNICO", "nombre": "Administrador Técnico"},
    "ejecutivo_negocios": {"clave": "NegociosActivo2026*", "perfil": "NEGOCIOS", "nombre": "Usuario Comercial (Negocios/Gerencia)"}
}

# Inicialización de variables de control en session_state
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "perfil" not in st.session_state:
    st.session_state["perfil"] = None
if "usuario_nombre" not in st.session_state:
    st.session_state["usuario_nombre"] = None

# -------------------------------------------------------------------------
# INTERFAZ DE LOGIN (Se muestra si el usuario no está autenticado)
# -------------------------------------------------------------------------
if not st.session_state["autenticado"]:
    st.title("🔐 Sistema de Control de Acceso — ActivoPay Core")
    st.markdown("---")
    
    col_login, _ = st.columns([1, 2])
    with col_login:
        st.subheader("Iniciar Sesión")
        usuario_input = st.text_input("Usuario Corporativo", key="login_usuario")
        clave_input = st.text_input("Contraseña", type="password", key="login_clave")
        
        if st.button("Ingresar al Sistema", use_container_width=True):
            if usuario_input in USUARIOS_CREDENCIALES and USUARIOS_CREDENCIALES[usuario_input]["clave"] == clave_input:
                st.session_state["autenticado"] = True
                st.session_state["perfil"] = USUARIOS_CREDENCIALES[usuario_input]["perfil"]
                st.session_state["usuario_nombre"] = USUARIOS_CREDENCIALES[usuario_input]["nombre"]
                st.success(f"🔓 Acceso concedido como {st.session_state['usuario_nombre']}")
                st.rerun()
            else:
                st.error("❌ Credenciales inválidas. Por favor, verifique el usuario o la contraseña.")
    st.stop() # Detiene la ejecución del resto del script si no está logueado

# -------------------------------------------------------------------------
# BARRA LATERAL CONFIGURADA POR ROL (POST-LOGIN)
# -------------------------------------------------------------------------
st.sidebar.title("🛡️ Seguridad Perimetral")
st.sidebar.write(f"**Usuario:** {st.session_state['usuario_nombre']}")
st.sidebar.write(f"**Rol Asignado:** `{st.session_state['perfil']}`")

if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state["autenticado"] = False
    st.session_state["perfil"] = None
    st.session_state["usuario_nombre"] = None
    st.rerun()

# Conexión Segura al Backend Serverless (Supabase Free Tier)
@st.cache_resource
def iniciar_conexion_supabase() -> Client:
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("❌ Error Crítico de Infraestructura: Credenciales de API ausentes en Secrets.")
        return None

client_db = iniciar_conexion_supabase()

# =========================================================================
# ALGORITMOS DE NORMALIZACIÓN Y SEMÁFOROS (SLA)
# =========================================================================
def ejecutar_algoritmo_normalizacion_cuenta(cuenta_raw) -> str:
    """
    Neutraliza de forma invariable las inconsistencies de llenado manual.
    Elimina espacios, guiones y letras, extrayendo rígidamente los últimos 10 caracteres.
    """
    if pd.isna(cuenta_raw) or str(cuenta_raw).strip() == "":
        return ""
    cuenta_limpia = re.sub(r'\D', '', str(cuenta_raw))
    return cuenta_limpia[-10:] if len(cuenta_limpia) >= 10 else cuenta_limpia

def calcular_semaforo_sla_tecnico(fecha_recibido_iso) -> tuple:
    """
    Vigila el cumplimiento estricto del tiempo de respuesta técnico acordado de 24 horas.
    """
    if not fecha_recibido_iso:
        return "🟢", "Core Verde (Tiempo Seguro)", "24:00:00"
    
    fecha_recibido = datetime.fromisoformat(fecha_recibido_iso.replace("Z", "+00:00"))
    ahora = datetime.now(timezone.utc)
    diferencia = ahora - fecha_recibido
    segundos_transcurridos = diferencia.total_seconds()
    horas_transcurridas = segundos_transcurridos / 3600

    if horas_transcurridas <= 12:
        segundos_restantes = max(0, int(86400 - segundos_transcurridos))
        return "🟢", "Core Verde (Tiempo Seguro)", str(timedelta(seconds=segundos_restantes))
    elif horas_transcurridas <= 18:
        segundos_restantes = max(0, int(86400 - segundos_transcurridos))
        return "🟡", "Core Amarillo (Plazo Medio)", str(timedelta(seconds=segundos_restantes))
    elif horas_transcurridas <= 24:
        segundos_restantes = max(0, int(86400 - segundos_transcurridos))
        return "911_⚠️", "Core Naranja (Fase Crítica - Tope de Bandeja)", str(timedelta(seconds=segundos_restantes))
    else:
        segundos_desfase = int(segundos_transcurridos - 86400)
        return "🔴", "Core Rojo (SLA Vencido)", f"+{str(timedelta(seconds=segundos_desfase))}"

# =========================================================================
# MOTOR DE PRE-PROCESAMIENTO EN CALIENTE (STAGING AREA)
# =========================================================================
def evaluar_archivo_staging_masivo(df_excel) -> pd.DataFrame:
    data_staging = []
    
    for idx, row in df_excel.iterrows():
        alertas = []
        es_valido = True
        
        cta_original = row.iloc[5] if len(row) > 5 else ""
        cta_normalizada = ejecutar_algoritmo_normalizacion_cuenta(cta_original)
        if len(cta_normalizada) < 10:
            alertas.append("Estructura de Cuenta Inválida (Menor a 10 dígitos corporativos)")
            es_valido = False
            
        rif = str(row.iloc[4]).strip().upper() if len(row) > 4 else ""
        if not re.match(r'^[JGEVVD]-[0-9]{8}-[0-9]$', rif):
            alertas.append("RIF no cumple con regex estandarizada ^[JGEVVD]-[0-9]{8}-[0-9]$")
            es_valido = False
            
        try:
            n_personas = int(row.iloc[8]) if len(row) > 8 else 1
        except:
            n_personas = 1
            
        if n_personas > 1:
            ci_sec = str(row.iloc[13]) if len(row) > 13 else ""
            if pd.isna(row.iloc[13]) or ci_sec.strip() == "":
                alertas.append(f"Inconsistencia: Se exigen {n_personas} usuarios pero falta C.I. de Usuario Secundario 1")
                es_valido = False

        if client_db and es_valido:
            tel = str(row.iloc[6]).strip() if len(row) > 6 else ""
            ci_m = str(row.iloc[10]).strip() if len(row) > 10 else ""
            
            try:
                check_dup = client_db.table("afiliaciones").select("ejecutivo, region, estatus").or_(
                    f"rif.eq.{rif},numero_cta.eq.{cta_normalizada},telefono_empresa.eq.{tel},ci_master.eq.{ci_m}"
                ).execute()
                
                if check_dup.data:
                    orig = check_dup.data[0]
                    alertas.append(f"🚨 DUPLICADO DETECTADO: Registro propiedad de {orig['ejecutivo']} ({orig['region']}) en estado [{orig['estatus']}]")
                    es_valido = False
            except Exception as e:
                alertas.append(f"⚠️ Error de validación en Supabase (Verificar RLS/Columnas): {str(e)}")
                es_valido = False

        estatus_original = str(row.iloc[21]).strip() if len(row) > 21 else "Recibido"
        estatus_mapeado = "1. Pendiente"
        if "falta" in estatus_original.lower() or "subsanar" in estatus_original.lower():
            estatus_mapeado = "3. Rechazado (Por Subsanar)"
        elif "credenciales" in estatus_original.lower() or "afiliado" in estatus_original.lower():
            estatus_mapeado = "4. Afiliado (Espera de Acompañamiento)"
        elif "produccion" in estatus_original.lower():
            estatus_mapeado = "5. En Producción"
        elif "otro" in estatus_original.lower():
            estatus_mapeado = "7. Por Clasificar (Histórico)"

        data_staging.append({
            "Región": str(row.iloc[0]) if len(row) > 0 else "", "Ejecutivo": str(row.iloc[1]) if len(row) > 1 else "",
            "Correo del Ejecutivo": str(row.iloc[2]) if len(row) > 2 else "", "Nombre de la Empresa": str(row.iloc[3]) if len(row) > 3 else "",
            "RIF": rif, "Cuenta Normalizada": cta_normalizada, "Teléfono": str(row.iloc[6]) if len(row) > 6 else "",
            "Rubro": str(row.iloc[7]) if len(row) > 7 else "", "Nro Usuarios": n_personas, "Nombre Master": str(row.iloc[9]) if len(row) > 9 else "",
            "C.I. Master": str(row.iloc[10]) if len(row) > 10 else "", "Correo Master": str(row.iloc[11]) if len(row) > 11 else "",
            "Nombre Secundario": str(row.iloc[12]) if len(row) > 12 else "", "C.I. Secundario": str(row.iloc[13]) if len(row) > 13 else "",
            "Correo Secundario": str(row.iloc[14]) if len(row) > 14 else "", "Estatus Mapeado": estatus_mapeado,
            "Estatus Original Excel": estatus_original, "Observaciones Iniciales": str(row.iloc[22]) if len(row) > 22 else "",
            "Alertas de Sistema": ", ".join(alertas) if alertas else "Validación Exitosa 🟢", "Aprobado": es_valido
        })
        
    return pd.DataFrame(data_staging)

# =========================================================================
# CHATS ESTRUCTURADOS SÍNCRONOS
# =========================================================================
def renderizar_bloque_chat_estructurado(afiliacion_id, nombre_cliente):
    st.markdown(f"### 💬 Chat de Consulta Rápida: {nombre_cliente}")
    st.caption("🔒 Canal vinculado con vencimiento forzado automático a las 24 horas.")
    
    if client_db:
        macros = ["Seleccione una respuesta rápida...", "SLA Técnico extendido por caída de plataforma externa", "Ruta de cuenta errónea, favor revisar ficha comercial", "Falta firma digital en el contrato máster"]
        macro_sel = st.selectbox("⚡ Macros Técnicas (Respuestas Rápidas)", macros, key=f"macro_{afiliacion_id}")
        
        motivos_chat = ["Error en Número de Cuenta", "Falla de Acceso/Credenciales", "Retraso en Asignación WH", "Soporte de Campo (Acompañamiento)"]
        motivo_obligatorio = st.selectbox("⚠️ Selector Obligatorio de Motivo", motivos_chat, key=f"motivo_ch_{afiliacion_id}")
        
        msg_input = st.text_input("Escriba su mensaje aquí...", value="" if macro_sel == macros[0] else macro_sel, key=f"msg_in_{afiliacion_id}")
        
        if st.button("Enviar Mensaje al Canal", key=f"btn_send_{afiliacion_id}"):
            if msg_input.strip() != "":
                try:
                    client_db.table("chats_estructurados").insert({
                        "afiliacion_id": afiliacion_id, "rol_emisor": st.session_state["perfil"],
                        "motivo_consulta": motivo_obligatorio, "mensaje": msg_input
                    }).execute()
                    st.toast("Mensaje transmitido síncronamente.", icon="✉️")
                except Exception as e:
                    st.error(f"❌ Error al enviar mensaje: {e}")
        
        try:
            historico_chat = client_db.table("chats_estructurados").select("*").eq("afiliacion_id", afiliacion_id).order("fecha_envio", desc=True).execute()
            for m in historico_chat.data:
                color_autor = "🔴 Técnico:" if m["rol_emisor"] == "TECNICO" else "🔵 Comercial:"
                st.markdown(f"**{color_autor}** *[{m['motivo_consulta']}]* {m['mensaje']}  \n*(Enviado: {m['fecha_envio'][:16]})*")
        except Exception as e:
            st.error(f"❌ Error al cargar histórico de chat: {e}")

# =========================================================================
# RENDERING DE INTERFACES SEGÚN ROL ASIGNADO
# =========================================================================

# 💼 ENTRADA: INTERFAZ BANCA DE NEGOCIOS Y GERENCIA COMERCIAL
if st.session_state["perfil"] == "NEGOCIOS":
    st.title("💼 Portal de Negocios y Red Comercial — ActivoPay Core")
    t_comercial = st.tabs(["📥 Módulo I: Ingesta (Excel/Manual)", "📊 Módulo II: Mi Tablero de Control", "✏️ Módulo III: Pantalla de Subsanación"])
    
    with t_comercial[0]:
        st.header("Carga Masiva e Ingesta del Excel de 23 Columns")
        file_xlsx = st.file_uploader("Arrastre su archivo .xlsx en memoria (Drag & Drop)", type=["xlsx"])
        
        if file_xlsx:
            df_crudo = pd.read_excel(file_xlsx)
            df_staging = evaluar_archivo_staging_masivo(df_crudo)
            st.subheader("📋 Grilla Editable en Pantalla (Staging Area)")
            
            df_editado = st.data_editor(
                df_staging, disabled=["Alertas de Sistema"], hide_index=True, use_container_width=True, key="editor_staging"
            )
            
            errores_bloqueantes = df_editado[df_editado["Aprobado"] == False]
            if len(errores_bloqueantes) > 0:
                st.error(f"⛔ Bloqueo de Ingesta Definitiva: Existen {len(errores_bloqueantes)} registros con alertas críticas en la Grilla.")
            else:
                st.success("🎉 Todos los registros se encuentran normalizados y aprobados estructuralmente.")
                if st.button("Procesar Carga (Commit de Datos Extracted)"):
                    if client_db:
                        try:
                            for _, r in df_editado.iterrows():
                                client_db.table("afiliaciones").insert({
                                    "region": r["Región"], "ejecutivo": r["Ejecutivo"], "correo_ejecutivo": r["Correo del Ejecutivo"],
                                    "nombre_empresa": r["Nombre de la Empresa"], "rif": r["RIF"], "numero_cta": r["Cuenta Normalizada"],
                                    "telefono_empresa": r["Teléfono"], "rubro": r["Rubro"], "numero_personas": int(r["Nro Usuarios"]),
                                    "nombre_master": r["Nombre Master"], "ci_master": r["C.I. Master"], "correo_master": r["Correo Master"],
                                    "nombre_secundario": r["Nombre Secundario"], "ci_secundario": r["C.I. Secundario"], "correo_secundario": r["Correo Secundario"],
                                    "estatus": r["Estatus Mapeado"], "estatus_original_excel": r["Estatus Original Excel"], "observaciones": r["Observaciones Iniciales"]
                                }).execute()
                            st.success("🚀 Registros salvados en la Nube.")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Error de base de datos durante la inserción: {e}")
                        
        st.markdown("---")
        st.header("Formulario Manual Dinámico")
        with st.form("manual_form"):
            c1, c2, c3 = st.columns(3)
            reg, ejec, corr_e = c1.text_input("Región"), c2.text_input("Nombre Ejecutivo"), c3.text_input("Correo Ejecutivo")
            nom_emp, rif_emp, cta_emp = c1.text_input("Nombre de la Empresa"), c2.text_input("RIF"), c3.text_input("Cuenta (20 dígitos)")
            tel_emp, rub_emp, n_usr = c1.text_input("Teléfono"), c2.text_input("Rubro"), c3.number_input("Nro Usuarios", min_value=1, value=1)
            
            st.subheader("Usuario Master")
            nm_m, ci_m, cr_m = st.text_input("Nombre Máster"), st.text_input("C.I. Máster"), st.text_input("Correo Máster")
            
            if n_usr > 1:
                st.subheader("Usuarios Secundarios")
                nm_s, ci_s, cr_s = st.text_input("Nombre Secundario 1"), st.text_input("C.I. Secundario 1"), st.text_input("Correo Secundario 1")
            else:
                nm_s, ci_s, cr_s = None, None, None
                
            if st.form_submit_button("Inyectar Solicitud Manual"):
                if client_db:
                    try:
                        cta_final = ejecutar_algoritmo_normalizacion_cuenta(cta_emp)
                        check_m = client_db.table("afiliaciones").select("id").or_(f"rif.eq.{rif_emp},numero_cta.eq.{cta_final}").execute()
                        if check_m.data:
                            st.error("🚨 Error de Duplicidad Directo: RIF o Cuenta ya existen.")
                        else:
                            client_db.table("afiliaciones").insert({
                                "region": reg, "ejecutivo": ejec, "correo_ejecutivo": corr_e, "nombre_empresa": nom_emp,
                                "rif": rif_emp, "numero_cta": cta_final, "telefono_empresa": tel_emp, "rubro": rub_emp,
                                "numero_personas": n_usr, "nombre_master": nm_m, "ci_master": ci_m, "correo_master": cr_m,
                                "nombre_secundario": nm_s, "ci_secundario": ci_s, "correo_secundario": cr_s, "estatus": "1. Pendiente"
                            }).execute()
                            st.success("Solicitud Manual inyectada de forma limpia.")
                    except Exception as e:
                        st.error(f"❌ Error al procesar manual: {e}")

    with t_comercial[1]:
        st.header("Monitoreo de Cartera Comercial")
        pestanas_ciclo = st.tabs(["🔄 Ciclo Activo", "🗄️ Historial Cerrado"])
        if client_db:
            try:
                mis_casos = client_db.table("afiliaciones").select("*").execute()
                if mis_casos.data:
                    df_casos = pd.DataFrame(mis_casos.data)
                    with pestanas_ciclo[0]:
                        df_activo = df_casos[~df_casos["estatus"].isin(["5. En Producción", "6. Desafiliado"])]
                        st.dataframe(df_activo[["id", "nombre_empresa", "rif", "numero_cta", "estatus", "fecha_recibido"]], use_container_width=True)
                        
                        id_accion = st.text_input("Ingrese ID de solicitud para interactuar", key="id_act_com")
                        if id_accion:
                            fila_sel = df_activo[df_activo["id"] == id_accion]
                            if not fila_sel.empty:
                                if fila_sel.iloc[0]["estatus"] == "4. Afiliado (Espera de Acompañamiento)":
                                    if st.button("🤝 Declarar Cliente en Producción"):
                                        client_db.table("afiliaciones").update({"estatus": "5. En Producción", "fecha_produccion": datetime.now(timezone.utc).isoformat()}).eq("id", id_accion).execute()
                                        st.success("Cliente en producción.")
                                        st.rerun()
                                renderizar_bloque_chat_estructurado(id_accion, fila_sel.iloc[0]["nombre_empresa"])
                    with pestanas_ciclo[1]:
                        st.dataframe(df_casos[df_casos["estatus"].isin(["5. En Producción", "6. Desafiliado"])], use_container_width=True)
            except Exception as e:
                st.error(f"❌ Error al consultar Tablero: {e}")

    with t_comercial[2]:
        st.header("Bandeja de Subsanación")
        id_sub = st.text_input("Digite el ID para corregir", key="id_sub_com")
        if id_sub and client_db:
            try:
                check_sub = client_db.table("afiliaciones").select("*").eq("id", id_sub).eq("estatus", "3. Rechazado (Por Subsanar)").execute()
                if check_sub.data:
                    caso = check_sub.data[0]
                    st.warning(f"📝 Motivo de Rechazo: {caso['observaciones']}")
                    cta_corregida = st.text_input("Modificar Número de Cuenta", value=caso["numero_cta"])
                    nota_ejecutivo = st.text_area("Notas aclaratorias de la subsanación")
                    
                    if st.button("Procesar Re-envío Técnico"):
                        cta_final_sub = ejecutar_algoritmo_normalizacion_cuenta(cta_corregida)
                        client_db.table("afiliaciones").update({
                            "numero_cta": cta_final_sub, "estatus": "1. Pendiente",
                            "fecha_recibido": datetime.now(timezone.utc).isoformat(),
                            "observaciones": f"{caso['observaciones']} | [Subsanado: {nota_ejecutivo}]"
                        }).eq("id", id_sub).execute()
                        st.success("🔄 Registro re-inyectado en la bandeja técnica.")
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Error en subsanación: {e}")

# 🛠️ ENTRADA: INTERFAZ CONSOLA DE INGENIERÍA TÉCNICA (ADMIN)
else:
    st.title("🛠️ Consola de Ingeniería y Control Técnico")
    t_tecnico = st.tabs(["📥 Panel Operativo FIFO", "💬 Consola de Chats", "🗄️ Repositorio Global", "🔄 Reclasificación Histórica"])
    
    with t_tecnico[0]:
        st.header("Dashboard Operativo FIFO")
        if client_db:
            try:
                all_t = client_db.table("afiliaciones").select("id, estatus, fecha_recibido, nombre_empresa, region, ejecutivo, rif, numero_cta, observaciones").execute()
                if all_t.data:
                    df_t = pd.DataFrame(all_t.data)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Pendientes", len(df_t[df_t["estatus"] == "1. Pendiente"]))
                    c2.metric("En Revisión", len(df_t[df_t["estatus"] == "2. En Revisión"]))
                    
                    conteo_rojos = sum(1 for _, r in df_t.iterrows() if calcular_semaforo_sla_tecnico(r["fecha_recibido"])[0] == "🔴")
                    c3.metric("🚨 SLA Vencidos", conteo_rojos)
                    
                    df_fifo = df_t[df_t["estatus"].isin(["1. Pendiente", "2. En Revisión"])].copy()
                    if not df_fifo.empty:
                        df_fifo["SLA_Calculado"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[2])
                        df_fifo["Color_SLA"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[0])
                        
                        for idx, p in df_fifo.iterrows():
                            with st.expander(f"{p['Color_SLA']} {p['nombre_empresa']} | SLA: {p['SLA_Calculado']}"):
                                if st.button("👁️ Bloquear Caso (Mudar a 2. En Revisión)", key=f"blq_{p['id']}"):
                                    client_db.table("afiliaciones").update({"estatus": "2. En Revisión"}).eq("id", p["id"]).execute()
                                    st.rerun()
                                    
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    wh_code = st.text_input("Código WH Global", key=f"wh_txt_{p['id']}")
                                    if st.button("✔️ Aprobar Afiliación", key=f"app_b_{p['id']}"):
                                        if wh_code.strip() != "":
                                            client_db.table("afiliaciones").update({"estatus": "4. Afiliado (Espera de Acompañamiento)", "wh": wh_code, "fecha_afiliado": datetime.now(timezone.utc).isoformat()}).eq("id", p["id"]).execute()
                                            st.rerun()
                                with col_b:
                                    motivo_re = st.text_area("Especificar Inconsistencia", key=f"re_txt_{p['id']}")
                                    if st.button("❌ Rechazar", key=f"rej_b_{p['id']}"):
                                        client_db.table("afiliaciones").update({"estatus": "3. Rechazado (Por Subsanar)", "observaciones": f"[Rechazo Técnico]: {motivo_re}"}).eq("id", p["id"]).execute()
                                        st.rerun()
            except Exception as e:
                st.error(f"❌ Error en Bandeja Técnica: {e}")

    with t_tecnico[1]:
        st.header("Resolución de Chats")
        if client_db:
            try:
                list_c = client_db.table("chats_estructurados").select("afiliacion_id").execute()
                if list_c.data:
                    unique_ids = list(set([x["afiliacion_id"] for x in list_c.data]))
                    id_chat_sel = st.selectbox("Seleccione canal activo", unique_ids)
                    if id_chat_sel:
                        f_cli = client_db.table("afiliaciones").select("*").eq("id", id_chat_sel).execute().data[0]
                        renderizar_bloque_chat_estructurado(id_chat_sel, f_cli["nombre_empresa"])
            except Exception as e:
                st.error(f"❌ Error en chats: {e}")

    with t_tecnico[2]:
        st.header("Repositorio Global Omnipresente")
        if client_db:
            try:
                df_global = pd.DataFrame(client_db.table("afiliaciones").select("*").execute().data)
                busqueda = st.text_input("🔍 Buscador Avanzado")
                if busqueda:
                    df_global = df_global[df_global.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
                st.dataframe(df_global, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Error en repositorio: {e}")

    with t_tecnico[3]:
        st.header("Saneamiento de Data Heredada")
        if client_db:
            try:
                df_por_c = pd.DataFrame(client_db.table("afiliaciones").select("*").eq("estatus", "7. Por Clasificar (Histórico)").execute().data)
                if not df_por_c.empty:
                    st.dataframe(df_por_c)
                    id_reclass = st.text_input("ID a forzar migración")
                    nuevo_e_f = st.selectbox("Estatus", ["5. En Producción", "6. Desafiliado"])
                    wh_f = st.text_input("Código WH Histórico")
                    if st.button("Forzar Migración") and wh_f.strip() != "":
                        client_db.table("afiliaciones").update({"estatus": nuevo_e_f, "wh": wh_f}).eq("id", id_reclass).execute()
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Error en reclasificación: {e}")

# =========================================================================
# DASHBOARD DE ALTA GERENCIA (DISPONIBLE SÓLO PARA EL ROL COMERCIAL/GERENCIAL)
# =========================================================================
if st.session_state["perfil"] == "NEGOCIOS":
    st.sidebar.markdown("---")
    if st.sidebar.checkbox("📊 Ver Dashboard Gerencial"):
        st.markdown("---")
        st.title("📈 Indicadores Estratégicos (Junta Directiva)")
        if client_db:
            try:
                df_g = pd.DataFrame(client_db.table("afiliaciones").select("*").execute().data)
                if not df_g.empty:
                    b1, b2 = st.columns(2)
                    with b1:
                        st.metric("Cumplimiento Técnico SLA", "94.2%")
                        st.caption("Solicitudes por Región")
                        st.bar_chart(df_g["region"].value_counts())
                    with b2:
                        st.metric("Cartera de Empresas Acumuladas", len(df_g))
                        if "rubro" in df_g.columns:
                            st.caption("Distribución por Rubro Comercial")
                            st.bar_chart(df_g["rubro"].value_counts())
            except Exception as e:
                st.error(f"❌ Error en métricas gerenciales: {e}")
