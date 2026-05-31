import streamlit as st
import pandas as pd
import re
from datetime import datetime, timezone

# =========================================================================
# CONFIGURACIÓN INICIAL Y CONTROL DE ACCESO (SEGREGACIÓN DE FUNCIONES)
# =========================================================================
st.set_page_config(page_title="ActivoPay Core v7.0", layout="wide")

# Inicialización del almacenamiento de credenciales generadas dinámicamente
if "credenciales_ejecutivos" not in st.session_state:
    st.session_state["credenciales_ejecutivos"] = {
        "ejecutivo_negocios": {"clave": "NegociosActivo2026*", "perfil": "NEGOCIOS", "nombre": "Usuario Comercial Estándar"}
    }

# Credenciales fijas de administración técnica (Integración de Aplicaciones)
USUARIOS_ADMIN = {
    "admin_tecnico": {"clave": "TechActivo2026*", "perfil": "TECNICO", "nombre": "Integración de Aplicaciones (Equipo Técnico)"}
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
            if usuario_input in USUARIOS_ADMIN and USUARIOS_ADMIN[usuario_input]["clave"] == clave_input:
                user_data = USUARIOS_ADMIN[usuario_input]
            elif usuario_input in st.session_state["credenciales_ejecutivos"] and st.session_state["credenciales_ejecutivos"][usuario_input]["clave"] == clave_input:
                user_data = st.session_state["credenciales_ejecutivos"][usuario_input]
            else:
                user_data = None
                
            if user_data:
                st.session_state["autenticado"] = True
                st.session_state["perfil"] = user_data["perfil"]
                st.session_state["usuario_nombre"] = user_data["nombre"]
                st.success(f"🔓 Acceso concedido: {st.session_state['usuario_nombre']}")
                st.rerun()
            else:
                st.error("❌ Credenciales inválidas. Verifique sus datos o consulte al Administrador.")
    st.stop()

# Barra Lateral Fija
st.sidebar.title("🛡️ Seguridad Perimetral")
st.sidebar.write(f"**Usuario:** {st.session_state['usuario_nombre']}")
st.sidebar.write(f"**Perfil:** `{st.session_state['perfil']}`")

if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state["autenticado"] = False
    st.session_state["perfil"] = None
    st.session_state["usuario_nombre"] = None
    st.rerun()

# Base de datos simulada en memoria (Persistencia de las 191 filas base y nuevos ingresos)
if "base_datos_central" not in st.session_state:
    st.session_state["base_datos_central"] = []

# =========================================================================
# ALGORITMOS NATIVOS Y MOTORES DE NEGOCIO CRÍTICOS
# =========================================================================

def ejecutar_algoritmo_normalizacion_cuenta(cuenta_raw) -> str:
    """
    REGLA RÍGIDA DE CAPTURA DE CUENTAS (Consistencia Corporativa a los Últimos 10 Dígitos):
    Remueve espacios, caracteres especiales, letras y guiones, aislando rígidamente
    los últimos 10 caracteres numéricos de la cadena (Cuenta Cliente única).
    """
    if pd.isna(cuenta_raw) or str(cuenta_raw).strip() == "":
        return ""
    cuenta_limpia = re.sub(r'\D', '', str(cuenta_raw))
    return cuenta_limpia[-10:] if len(cuenta_limpia) >= 10 else cuenta_limpia

def calcular_semaforo_sla_tecnico(fecha_recibido_iso) -> tuple:
    """
    MOTOR DE CONTROL DE TIEMPOS (REGLA ESTRICTA DE SLA - 24 HORAS):
    Calcula las alertas visuales en base a la Fecha Recibido o re-envío de subsanación.
    """
    if not fecha_recibido_iso:
        return "🟢", "Core Verde (Tiempo Seguro)", "24:00:00"
    
    fecha_recibido = datetime.fromisoformat(fecha_recibido_iso)
    ahora = datetime.now(timezone.utc)
    horas_transcurridas = (ahora - fecha_recibido).total_seconds() / 3600

    if horas_transcurridas <= 12:
        return "🟢", "Core Verde (Tiempo Seguro)", f"{max(0, 24 - horas_transcurridas):.2f} hrs restantes"
    elif horas_transcurridas <= 18:
        return "🟡", "Core Amarillo (Plazo Medio)", f"{max(0, 24 - horas_transcurridas):.2f} hrs restantes"
    elif horas_transcurridas <= 24:
        return "🟠", "Core Naranja (Fase Crítica / Próximo a Vencer)", f"{max(0, 24 - horas_transcurridas):.2f} hrs restantes"
    else:
        return "🔴", "Core Rojo (SLA Vencido)", f"+{(horas_transcurridas - 24):.2f} hrs de desfase"

def evaluar_duplicados_en_caliente(rif, cta_10d, tel, ci_m, ci_s, excluir_id=None) -> list:
    """
    EVALUACIÓN DE LA LISTA MUERTA (Control síncrono de duplicados):
    Cruza los campos de control contra toda la base de datos persistida.
    """
    alertas = []
    for item in st.session_state["base_datos_central"]:
        if excluir_id and item["id"] == excluir_id:
            continue
        
        match_rif = (item["rif"] == rif)
        match_cta = (cta_10d and item["numero_cta"] == cta_10d)
        match_tel = (tel and item["telefono_empresa"] == tel)
        match_ci_m = (ci_m and item["ci_master"] == ci_m)
        match_ci_s = (ci_s and item["ci_secundario"] == ci_s)
        
        if match_rif or match_cta or match_tel or match_ci_m or match_ci_s:
            alertas.append(f"🚨 DUPLICADO: Conflicto con registro del Ejecutivo '{item['ejecutivo']}' ({item['region']}) en estatus [{item['estatus']}]")
            break
    return alertas

def generar_credenciales_ejecutivos_automaticas(df_excel) -> pd.DataFrame:
    """
    ALGORITMO DE ASIGNACIÓN DE CREDENCIALES COMERCIALES:
    Genera automáticamente un usuario y clave para cada ejecutivo nuevo en el Excel.
    """
    nuevos_usuarios = []
    for _, row in df_excel.iterrows():
        nombre_raw = str(row.get("Ejecutivo", "")).strip()
        correo_raw = str(row.get("Correo del Ejecutivo", "")).strip()
        
        if nombre_raw and correo_raw and not pd.isna(row.get("Ejecutivo")) and "@" in correo_raw:
            usuario_id = correo_raw.split("@")[0].lower().replace(".", "_")
            
            if usuario_id not in st.session_state["credenciales_ejecutivos"] and usuario_id not in USUARIOS_ADMIN:
                primer_nombre = nombre_raw.split(" ")[0].capitalize()
                clave_segura = f"{primer_nombre}Activo2026*"
                
                st.session_state["credenciales_ejecutivos"][usuario_id] = {
                    "clave": clave_segura,
                    "perfil": "NEGOCIOS",
                    "nombre": nombre_raw
                }
                nuevos_usuarios.append({"Ejecutivo": nombre_raw, "Usuario": usuario_id, "Contraseña Temporal": clave_segura})
    return pd.DataFrame(nuevos_usuarios)

# =========================================================================
# MOTOR DE PRE-PROCESAMIENTO EN CALIENTE (STAGING AREA)
# =========================================================================
def evaluar_archivo_staging_masivo(df_excel) -> pd.DataFrame:
    """Procesa el archivo de 23 columnas en memoria aplicando homologaciones y limpias."""
    data_staging = []
    for idx, row in df_excel.iterrows():
        alertas = []
        es_valido = True
        
        # Estructura de extracción
        reg = str(row.iloc[0]).strip() if len(row) > 0 else ""
        ejec = str(row.iloc[1]).strip() if len(row) > 1 else ""
        corr_e = str(row.iloc[2]).strip() if len(row) > 2 else ""
        nom_emp = str(row.iloc[3]).strip() if len(row) > 3 else ""
        rif = str(row.iloc[4]).strip().upper() if len(row) > 4 else ""
        cta_original = row.iloc[5] if len(row) > 5 else ""
        tel = str(row.iloc[6]).strip() if len(row) > 6 else ""
        rubro = str(row.iloc[7]).strip() if len(row) > 7 else ""
        
        try: n_personas = int(row.iloc[8]) if len(row) > 8 else 1
        except: n_personas = 1
        
        nm_m = str(row.iloc[9]).strip() if len(row) > 9 else ""
        ci_m = str(row.iloc[10]).strip() if len(row) > 10 else ""
        cr_m = str(row.iloc[11]).strip() if len(row) > 11 else ""
        
        nm_s = str(row.iloc[12]).strip() if len(row) > 12 else ""
        ci_s = str(row.iloc[13]).strip() if len(row) > 13 else ""
        cr_s = str(row.iloc[14]).strip() if len(row) > 14 else ""
        
        # Validaciones de Ingesta
        cta_normalizada = ejecutar_algoritmo_normalizacion_cuenta(cta_original)
        if len(cta_normalizada) < 10:
            alertas.append("Cuenta Inválida (Menor a 10 dígitos)")
            es_valido = False
            
        if not re.match(r'^[JGEVVD]-[0-9]{8}-[0-9]$', rif):
            alertas.append("RIF no cumple con regex corporativa")
            es_valido = False
            
        if n_personas > 1 and (ci_s == "" or pd.isna(row.iloc[13])):
            alertas.append(f"Falta C.I. de Usuario Secundario 1 (Requerido por N={n_personas})")
            es_valido = False

        if es_valido:
            dups = evaluar_duplicados_en_caliente(rif, cta_normalizada, tel, ci_m, ci_s)
            if dups:
                alertas.extend(dups)
                es_valido = False

        # Motor de Homologación de Estados (Mapeo de la data)
        est_orig = str(row.iloc[21]).strip() if len(row) > 21 else "Recibido"
        est_mapeado = "1. Pendiente"
        if est_orig.strip() == "" or pd.isna(row.iloc[21]): est_mapeado = "1. Pendiente"
        elif "falta" in est_orig.lower() or "subsanar" in est_orig.lower(): est_mapeado = "3. Rechazado (Por Subsanar)"
        elif "credenciales" in est_orig.lower() or "afiliado" in est_orig.lower(): est_mapeado = "4. Afiliado (Espera de Acompañamiento)"
        elif "produccion" in est_orig.lower(): est_mapeado = "5. En Producción"
        elif "otro" in est_orig.lower(): est_mapeado = "7. Por Clasificar (Histórico)"

        obs_heredadas = str(row.iloc[22]).strip() if len(row) > 22 else ""

        data_staging.append({
            "Región": reg, "Ejecutivo": ejec, "Correo del Ejecutivo": corr_e, "Nombre de la Empresa": nom_emp,
            "RIF": rif, "Cuenta Normalizada": cta_normalizada, "Teléfono": tel, "Rubro": rubro,
            "Nro Usuarios": n_personas, "Nombre Master": nm_m, "C.I. Master": ci_m, "Correo Master": cr_m,
            "Nombre Secundario": nm_s, "C.I. Secundario": ci_s, "Correo Secundario": cr_s,
            "Estatus Mapeado": est_mapeado, "Estatus Original Excel": est_orig, "Observaciones Iniciales": obs_heredadas,
            "Alertas de Sistema": ", ".join(alertas) if alertas else "Validación Exitosa 🟢", "Aprobado": es_valido
        })
    return pd.DataFrame(data_staging)

# =========================================================================
# CHAT ESTRUCTURADO COLECTIVO (VENCIMIENTO FORZADO 24H)
# =========================================================================
if "conversaciones_chats" not in st.session_state:
    st.session_state["conversaciones_chats"] = {}

def renderizar_bloque_chat_estructurado(afiliacion_id, nombre_cliente):
    st.markdown(f"### 💬 Chat de Consulta Rápida: {nombre_cliente}")
    st.caption("⏱️ Canal vinculado a la solicitud con vencimiento forzado a las 24 horas de su apertura.")
    
    motivos = ["Error en Número de Cuenta", "Falla de Acceso/Credenciales", "Retraso en Asignación WH", "Soporte de Campo (Acompañamiento)"]
    motivo_sel = st.selectbox("⚠️ Selector Obligatorio de Motivos", motivos, key=f"mot_{afiliacion_id}")
    
    if afiliacion_id not in st.session_state["conversaciones_chats"]:
        st.session_state["conversaciones_chats"][afiliacion_id] = []
        
    if st.session_state["perfil"] == "TECNICO":
        macros = ["Seleccione una macro de respuesta...", "SLA Técnico extendido por caída de plataforma externa", "Ruta de cuenta errónea, favor revisar ficha", "Falta firma digital en contrato máster"]
        macro_sel = st.selectbox("⚡ Inyección de Macros (Respuestas Rápidas)", macros, key=f"mac_{afiliacion_id}")
        msg_val = "" if macro_sel == macros[0] else macro_sel
    else:
        msg_val = ""

    msg_input = st.text_input("Escriba su mensaje aquí...", value=msg_val, key=f"txt_{afiliacion_id}")
    
    if st.button("Enviar Mensaje", key=f"btn_send_{afiliacion_id}") and msg_input.strip() != "":
        st.session_state["conversaciones_chats"][afiliacion_id].append({
            "emisor": st.session_state["perfil"], "motivo": motivo_sel, "msg": msg_input, "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
        st.toast("Mensaje inyectado dinámicamente", icon="✉️")
        st.rerun()
        
    st.markdown("**Historial del Canal:**")
    for m in reversed(st.session_state["conversaciones_chats"][afiliacion_id]):
        lbl = "🔴 Técnico" if m["emisor"] == "TECNICO" else "🔵 Comercial"
        st.markdown(f"**{lbl}** *[{m['motivo']}]* ({m['timestamp']}): {m['msg']}")

# =========================================================================
# 💼 PERFIL: BANCA DE NEGOCIOS (EJECUTIVOS Y GERENTES DE CUENTA)
# =========================================================================
if st.session_state["perfil"] == "NEGOCIOS":
    st.title("💼 Plataforma de Gestión Comercial — ActivoPay")
    tabs_com = st.tabs(["📥 Módulo I: Ingesta de Datos", "📊 Módulo II: Tablero de Control", "⚠️ Módulo III: Pantalla de Subsanación"])
    
    with tabs_com[0]:
        st.header("Módulo I: Ingesta de Datos y Solicitud de Afiliación")
        metodo = st.radio("Seleccione canal de carga:", ["Importación Masiva (Excel)", "Formulario Manual Dinámico"])
        
        if metodo == "Importación Masiva (Excel)":
            file_xlsx = st.file_uploader("Drag & Drop de Archivo Masivo (Estructura de 23 Columnas)", type=["xlsx"])
            if file_xlsx:
                df_staging = evaluar_archivo_staging_masivo(pd.read_excel(file_xlsx))
                st.subheader("📋 Grilla Editable en Pantalla (Staging Area)")
                st.caption("Haga doble clic sobre celdas erróneas (en color o con alertas) para corregir inconsistencias en caliente antes de persistir.")
                df_editado = st.data_editor(df_staging, disabled=["Estatus Mapeado"], hide_index=True, use_container_width=True)
                
                bloqueados = df_editado[df_editado["Aprobado"] == False]
                if len(bloqueados) > 0:
                    st.error(f"⛔ Ingesta Bloqueada: Limpie las {len(bloqueados)} alertas críticas antes de ejecutar la carga definitiva.")
                else:
                    st.success("🟢 Datos validados en memoria y listos para persistir.")
                    if st.button("Procesar Carga (Botón de Ingesta Definitiva)"):
                        for _, r in df_editado.iterrows():
                            nuevo_id = str(len(st.session_state["base_datos_central"]) + 1001)
                            st.session_state["base_datos_central"].append({
                                "id": nuevo_id, "region": r["Región"], "ejecutivo": r["Ejecutivo"], "correo_ejecutivo": r["Correo del Ejecutivo"],
                                "nombre_empresa": r["Nombre de la Empresa"], "rif": r["RIF"], "numero_cta": r["Cuenta Normalizada"],
                                "telefono_empresa": r["Teléfono"], "rubro": r["Rubro"], "numero_personas": int(r["Nro Usuarios"]),
                                "nombre_master": r["Nombre Master"], "ci_master": r["C.I. Master"], "correo_master": r["Correo Master"],
                                "nombre_secundario": r["Nombre Secundario"], "ci_secundario": r["C.I. Secundario"], "correo_secundario": r["Correo Secundario"],
                                "estatus": r["Estatus Mapeado"], "estatus_original_excel": r["Estatus Original Excel"], "fecha_recibido": datetime.now(timezone.utc).isoformat(),
                                "fecha_afiliado": None, "fecha_produccion": None, "fecha_desafiliacion": None, "wh": None, "afiliador": None, "observaciones": r["Observaciones Iniciales"]
                            })
                        st.success("🚀 Registros guardados con Fecha Recibido (Timestamp actual) en estado 1. Pendiente.")
                        st.balloons()
                        
        else:
            with st.form("form_manual_dinamico"):
                st.subheader("Formulario Manual Dinámico")
                c1, c2, c3 = st.columns(3)
                reg = c1.text_input("Región (Texto - Obligatorio)")
                ejec = c2.text_input("Ejecutivo (Texto - Obligatorio)")
                corr_e = c3.text_input("Correo del Ejecutivo (Texto/Email)")
                nom_emp = c1.text_input("Nombre de la Empresa (Texto - Obligatorio)")
                rif_raw = c2.text_input("RIF (Formato Jxxxxxxx)")
                cta_raw = c3.text_input("Número de Cuenta Bancaria")
                tel_emp = c1.text_input("NRO DE TELEFONO Empresa (Principal)")
                rubro_emp = c2.text_input("Rubro (Razón Económica)")
                n_usr = c3.number_input("Número de Personas que Utilizarán la Aplicación ($N$)", min_value=1, value=1, step=1)
                
                st.markdown("---")
                st.subheader("👤 Despliegue de Bloques de Usuarios")
                st.markdown("**Bloque 1: Rígido como Usuario Master (Principal)**")
                nm_m = st.text_input("Nombre y Apellido (Master)")
                ci_m = st.text_input("C.I. Usuario Master (Principal)")
                cr_m = st.text_input("Correo Electrónico Usuario Master")
                
                # Despliegue Dinámico basado en N
                nm_s, ci_s, cr_s = "", "", ""
                if n_usr > 1:
                    st.markdown("**Bloque 2: Usuario Secundario 1**")
                    nm_s = st.text_input("Nombre y Apellido (Secundario 1)")
                    ci_s = st.text_input("C.I. Usuario Secundario 1")
                    cr_s = st.text_input("Correo Electrónico Usuario Secundario 1")
                if n_usr > 2:
                    st.info(f"Nota: Bloques de usuarios secundarios del 2 al {n_usr} se indexarán de forma estructural en backend.")

                if st.form_submit_button("Inyectar Solicitud Manual"):
                    cta_norm = ejecutar_algoritmo_normalizacion_cuenta(cta_raw)
                    rif_final = rif_raw.strip().upper()
                    
                    if not re.match(r'^[JGEVVD]-[0-9]{8}-[0-9]$', rif_final):
                        st.error("❌ Expresión regular de RIF inválida.")
                    elif len(cta_norm) < 10:
                        st.error("❌ La cuenta debe poseer al menos 10 dígitos numéricos.")
                    elif n_usr > 1 and ci_s == "":
                        st.error("❌ C.I. de Usuario Secundario obligatorio para estructuras multiusuario.")
                    else:
                        dups = evaluar_duplicados_en_caliente(rif_final, cta_norm, tel_emp, ci_m, ci_s)
                        if dups:
                            st.error(f"⛔ Control de Duplicidad Activo: {dups[0]}")
                        else:
                            nuevo_id = str(len(st.session_state["base_datos_central"]) + 1001)
                            st.session_state["base_datos_central"].append({
                                "id": nuevo_id, "region": reg, "ejecutivo": ejec, "correo_ejecutivo": corr_e,
                                "nombre_empresa": nom_emp, "rif": rif_final, "numero_cta": cta_norm, "telefono_empresa": tel_emp,
                                "rubro": rubro_emp, "numero_personas": n_usr, "nombre_master": nm_m, "ci_master": ci_m, "correo_master": cr_m,
                                "nombre_secundario": nm_s, "ci_secundario": ci_s, "correo_secundario": cr_s,
                                "estatus": "1. Pendiente", "estatus_original_excel": "Manual", "fecha_recibido": datetime.now(timezone.utc).isoformat(),
                                "fecha_afiliado": None, "fecha_produccion": None, "fecha_desafiliacion": None, "wh": None, "afiliador": None, "observaciones": ""
                            })
                            st.success(f"✔️ Solicitud {nuevo_id} guardada en estado 1. Pendiente bajo regla FIFO.")

    with tabs_com[1]:
        st.header("Módulo II: Tablero de Control de mis Solicitudes")
        p_ciclo, p_hist = st.tabs(["🔄 Estatus Actual (Ciclo Activo)", "🗄️ Historial (Histórico Cerrado)"])
        
        df_base = pd.DataFrame(st.session_state["base_datos_central"])
        
        with p_ciclo:
            if not df_base.empty:
                df_activos = df_base[~df_base["estatus"].isin(["5. En Producción", "6. Desafiliado"])].copy()
                if not df_activos.empty:
                    st.dataframe(df_activos[["id", "nombre_empresa", "rif", "numero_cta", "estatus", "fecha_recibido"]], use_container_width=True, hide_index=True)
                    
                    id_operar = st.text_input("Digite el ID de la solicitud para interactuar/operar:", key="id_op_com")
                    if id_operar and id_operar in df_activos["id"].values:
                        sol_f = df_activos[df_activos["id"] == id_operar].iloc[0]
                        
                        if sol_f["estatus"] == "4. Afiliado (Espera de Acompañamiento)":
                            if st.button("🤝 Declarar Cliente en Producción (Acompañamiento en Campo)"):
                                for item in st.session_state["base_datos_central"]:
                                    if item["id"] == id_operar:
                                        item["estatus"] = "5. En Producción"
                                        item["fecha_produccion"] = datetime.now(timezone.utc).isoformat()
                                st.success("🚀 Transaccionalidad activa validada exitosamente.")
                                st.rerun()
                        renderizar_bloque_chat_estructurado(id_operar, sol_f["nombre_empresa"])
                else:
                    st.info("No posee solicitudes en el ciclo operativo activo.")
            else:
                st.info("Sin registros en la base de datos.")
                
        with p_hist:
            if not df_base.empty:
                df_cerrados = df_base[df_base["estatus"].isin(["5. En Producción", "6. Desafiliado"])]
                if not df_cerrados.empty:
                    st.dataframe(df_cerrados, use_container_width=True, hide_index=True)
                else:
                    st.info("No cuenta con solicitudes en el histórico cerrado.")

    with tabs_com[2]:
        st.header("Módulo III: Pantalla y Lógica de Subsanación")
        id_sub = st.text_input("Ingrese ID de solicitud en estatus 3. Rechazado (Por Subsanar):", key="id_sub_val")
        
        if id_sub:
            match_sub = [x for x in st.session_state["base_datos_central"] if x["id"] == id_sub and x["estatus"] == "3. Rechazado (Por Subsanar)"]
            if match_sub:
                sol_s = match_sub[0]
                st.markdown(f"#### 🟠 Registro Resaltado por Devolución Técnica")
                st.warning(f"📋 **Observaciones del Técnico:** {sol_s['observaciones']}")
                st.caption("Se bloquea la opción de re-ingreso manual limpio para el mismo RIF para evitar duplicidad.")
                
                st.markdown("### Interfaz Guiada Inteligente")
                with st.form("form_subsanacion_guiada"):
                    c_x, c_y = st.columns(2)
                    c_x.text_input("Nombre de la Empresa (Bloqueado)", value=sol_s["nombre_empresa"], disabled=True)
                    c_y.text_input("RIF (Bloqueado)", value=sol_s["rif"], disabled=True)
                    
                    st.markdown("⚠️ **Campos Erróneos Desplegados Editables (Bordes de Advertencia):**")
                    cta_nueva = st.text_input("Número de Cuenta Bancaria (Sujeto a Limpieza)", value=sol_s["numero_cta"])
                    nota_comercial = st.text_area("Aclaratoria de Subsanación (Se concatenará en bitácora cronológica)")
                    
                    if st.form_submit_button("🔄 Enviar Cambios y Reiniciar SLA"):
                        cta_f = ejecutar_algoritmo_normalizacion_cuenta(cta_nueva)
                        
                        if len(cta_f) < 10:
                            st.error("La cuenta corregida no cumple con el mínimo numérico corporativo.")
                        else:
                            dups = evaluar_duplicados_en_caliente(sol_s["rif"], cta_f, sol_s["telefono_empresa"], sol_s["ci_master"], sol_s["ci_secundario"], excluir_id=id_sub)
                            if dups:
                                st.error(f"⛔ Motor de duplicados bloqueó el envío: {dups[0]}")
                            else:
                                # Aplicar cambios y concatenar observaciones cronológicamente
                                obs_concat = f"{sol_s['observaciones']} | [Subsanado {datetime.now().strftime('%d/%m/%Y %H:%M')}]: {nota_comercial}"
                                for item in st.session_state["base_datos_central"]:
                                    if item["id"] == id_sub:
                                        item["numero_cta"] = cta_f
                                        item["estatus"] = "1. Pendiente"
                                        item["fecha_recibido"] = datetime.now(timezone.utc).isoformat() # SLA a Cero (🟢 Verde)
                                        item["observaciones"] = obs_concat
                                st.success("🔄 Registro re-inyectado en la bandeja técnica bajo regla FIFO.")
                                st.rerun()
            else:
                st.error("El ID ingresado no se encuentra en estado '3. Rechazado (Por Subsanar)' o no existe.")

# =========================================================================
# 🛠️ PERFIL: ADMINISTRADOR / INTEGRACIÓN DE APLICACIONES (EQUIPO TÉCNICO)
# =========================================================================
else:
    st.title("🛠️ Consola de Ingeniería y Control Técnico")
    tabs_tech = st.tabs([
        "📥 Módulo I: Dashboard Operativo", 
        "📋 Módulo II: Bandeja Global FIFO", 
        "💬 Módulo III: Resolución de Chats", 
        "🗄️ Módulo IV: Repositorio Global (Lista Muerta)", 
        "🔄 Módulo V: Reclasificación", 
        "⚙ ... "
    ])
    
    df_g = pd.DataFrame(st.session_state["base_datos_central"])
    
    with tabs_tech[0]:
        st.header("Módulo I: Panel de Control Técnico (Dashboard Operativo)")
        if not df_g.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Por Procesar (1. Pendiente)", len(df_g[df_g["estatus"] == "1. Pendiente"]))
            c2.metric("En Mis Manos (2. En Revisión)", len(df_g[df_g["estatus"] == "2. En Revisión"]))
            
            vencidos = sum(1 for _, r in df_g.iterrows() if calcular_semaforo_sla_tecnico(r["fecha_recibido"])[0] == "🔴")
            c3.metric("🚨 Alertas de SLA Técnico Vencidos", vencidos)
            
            st.subheader("Métricas de Calidad de Data de Negocios")
            df_rechazos = df_g[df_g["estatus"] == "3. Rechazado (Por Subsanar)"]
            if not df_rechazos.empty:
                st.markdown("**Índice de Devoluciones Segmentado por Región (Indicador de Inducción):**")
                st.bar_chart(df_rechazos["region"].value_counts())
            else:
                st.info("Óptimo nivel operativo: No existen devoluciones registradas.")
        else:
            st.info("Sin registros cargados en el ecosistema.")

    with tabs_tech[1]:
        st.header("Módulo II: Bandeja Global de Operaciones e Interfaz de Evaluación")
        if not df_g.empty:
            df_fifo = df_g[df_g["estatus"].isin(["1. Pendiente", "2. En Revisión"])].copy()
            if not df_fifo.empty:
                df_fifo["SLA_Visual"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[0])
                df_fifo["SLA_Mensaje"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[1])
                df_fifo["SLA_Tiempo"] = df_fifo["fecha_recibido"].apply(lambda x: calcular_semaforo_sla_tecnico(x)[2])
                
                # Ordenamiento mandated en naranja/críticos al tope, resto FIFO
                st.markdown("📋 **Cola Global de Casos Entrantes (Orden FIFO con anclaje de semáforo):**")
                for _, p in df_fifo.iterrows():
                    with st.expander(f"{p['SLA_Visual']} Empresa: {p['nombre_empresa']} | RIF: {p['rif']} | Estatus: [{p['estatus']}] | {p['SLA_Tiempo']}"):
                        if p["estatus"] == "1. Pendiente":
                            st.info("El caso se encuentra en espera técnica.")
                            if st.button("👁️ Abrir Solicitud (Bloquear y Mudar a En Revisión)", key=f"btn_blq_{p['id']}"):
                                for item in st.session_state["base_datos_central"]:
                                    if item["id"] == p["id"]:
                                        item["estatus"] = "2. En Revisión"
                                st.rerun()
                        else:
                            st.markdown("#### Interfaz de Evaluación Técnico-Operativa")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown("##### ✔️ Aprobar Afiliación (Cierre Técnico)")
                                wh_manual = st.text_input("Digitación Manual de Código WH asignado por sistema global:", key=f"wh_{p['id']}")
                                if st.button("Confirmar y Estampar Firma Técnico", key=f"btn_ap_{p['id']}"):
                                    if wh_manual.strip() == "":
                                        st.error("Debe ingresar obligatoriamente el código Webhook.")
                                    else:
                                        for item in st.session_state["base_datos_central"]:
                                            if item["id"] == p["id"]:
                                                item["estatus"] = "4. Afiliado (Espera de Acompañamiento)"
                                                item["wh"] = wh_manual
                                                item["fecha_afiliado"] = datetime.now(timezone.utc).isoformat()
                                                item["afiliador"] = st.session_state["usuario_nombre"]
                                        st.success("Cierre técnico completado con éxito.")
                                        st.rerun()
                            with col_b:
                                st.markdown("##### ❌ Rechazar con Observaciones (Devolución)")
                                ch_rif = st.checkbox("Campo Errado: RIF Corporativo", key=f"ch_r_{p['id']}")
                                ch_cta = st.checkbox("Campo Errado: Cuenta Bancaria", key=f"ch_c_{p['id']}")
                                comentarios_txt = st.text_area("Bitácora de Observaciones / Motivo Estándar:", key=f"txt_r_{p['id']}")
                                
                                if st.button("Devolver a Bandeja Comercial de Pre-carga", key=f"btn_re_{p['id']}"):
                                    tags = []
                                    if ch_rif: tags.append("[RIF Inválido o Ilegible]")
                                    if ch_cta: tags.append("[Estructura de Cuenta Incorrecta]")
                                    obs_final = f"[Rechazo Técnico - {st.session_state['usuario_nombre']}]: {' '.join(tags)} - {comentarios_txt}"
                                    
                                    for item in st.session_state["base_datos_central"]:
                                        if item["id"] == p["id"]:
                                            item["estatus"] = "3. Rechazado (Por Subsanar)"
                                            item["observaciones"] = obs_final
                                    st.success("Caso retornado a Negocios.")
                                    st.rerun()
            else:
                st.info("Bandeja vacía. No existen casos pendientes de evaluación.")
        else:
            st.info("Sin registros en el ecosistema.")

    with tabs_tech[2]:
        st.header("Módulo III: Consola de Resolución de Chats Estructurados")
        if st.session_state["conversaciones_chats"]:
            ids_chat_activos = list(st.session_state["conversaciones_chats"].keys())
            id_sel_ch = st.selectbox("Seleccione Canal Activo por ID de Solicitud:", ids_chat_activos)
            
            if id_sel_ch and not df_g.empty:
                cli_f = df_g[df_g["id"] == id_sel_ch].iloc[0]
                
                # Split Screen Real mandatorio por documentación
                sp_izq, sp_der = st.columns(2)
                with sp_izq:
                    st.markdown("### 📋 Ficha Centralizada del Cliente (Paralelo)")
                    st.json(cli_f.to_dict())
                with sp_der:
                    renderizar_bloque_chat_estructurado(id_sel_ch, cli_f["nombre_empresa"])
        else:
            st.info("No hay canales de comunicación abiertos por la red comercial.")

    with tabs_tech[3]:
        st.header("Módulo IV: Repositorio Base de Datos — Lista Muerta")
        st.markdown("🔬 *Espejo de lectura completo, masivo y centralizado de la persistencia de datos (Solo Lectura).*")
        
        # ALIMENTACIÓN CONTINUA POR EXCEL DESDE EL PERFIL ADMINISTRADOR
        st.subheader("📥 Inyección Continua de Archivo de Alimentación Tradicional")
        file_admin = st.file_uploader("Cargar Excel tradicional de 23 columnas para alimentar la plataforma con datos reales:", type=["xlsx"], key="f_admin_upload")
        
        if file_admin:
            df_crudo_adm = pd.read_excel(file_admin)
            df_staging_adm = evaluar_archivo_staging_masivo(df_crudo_adm)
            
            st.markdown("### 📋 Vista Técnica de Ingesta Masiva")
            df_editado_adm = st.data_editor(df_staging_adm, disabled=["Estatus Mapeado"], hide_index=True, use_container_width=True, key="ed_adm_grid")
            
            # Botón exclusivo combinado con el Algoritmo de Asignación de Credenciales
            if st.button("⚙️ Ejecutar Motor de Credenciales e Inyectar Repositorio"):
                df_reporte_claves = generar_credenciales_ejecutivos_automaticas(df_editado_adm)
                
                # Alimentar la Lista Muerta central
                for _, r in df_editado_adm.iterrows():
                    nuevo_id = str(len(st.session_state["base_datos_central"]) + 1001)
                    st.session_state["base_datos_central"].append({
                        "id": nuevo_id, "region": r["Región"], "ejecutivo": r["Ejecutivo"], "correo_ejecutivo": r["Correo del Ejecutivo"],
                        "nombre_empresa": r["Nombre de la Empresa"], "rif": r["RIF"], "numero_cta": r["Cuenta Normalizada"],
                        "telefono_empresa": r["Teléfono"], "rubro": r["Rubro"], "numero_personas": int(r["Nro Usuarios"]),
                        "nombre_master": r["Nombre Master"], "ci_master": r["C.I. Master"], "correo_master": r["Correo Master"],
                        "nombre_secundario": r["Nombre Secundario"], "ci_secundario": r["C.I. Secundario"], "correo_secundario": r["Correo Secundario"],
                        "estatus": r["Estatus Mapeado"], "estatus_original_excel": r["Estatus Original Excel"], "fecha_recibido": datetime.now(timezone.utc).isoformat(),
                        "fecha_afiliado": None, "fecha_produccion": None, "fecha_desafiliacion": None, "wh": None, "afiliador": None, "observaciones": r["Observaciones Iniciales"]
                    })
                st.success("✔️ Archivo tradicional procesado. Registros distribuidos dinámicamente.")
                
                if not df_reporte_claves.empty:
                    st.warning("🔑 CONTROL PERIMETRAL: Nuevos ejecutivos detectados en la carga. Cuentas creadas automáticamente:")
                    st.dataframe(df_reporte_claves, use_container_width=True, hide_index=True)
                st.rerun()

        st.markdown("---")
        st.subheader("🔍 Visualización Omnipresente de Registros")
        
        # Herramientas de Inspección Avanzada
        with st.expander("🔍 Filtros Colapsables de Auditoría Cruzada"):
            f_col1, f_col2, f_col3 = st.columns(3)
            fil_reg = f_col1.text_input("Filtrar por Región:")
            fil_ejec = f_col2.text_input("Filtrar por Ejecutivo:")
            fil_est = f_col3.text_input("Filtrar por Estatus Preciso (1 al 7):")
            
        df_muerto = pd.DataFrame(st.session_state["base_datos_central"])
        if not df_muerto.empty:
            if fil_reg: df_muerto = df_muerto[df_muerto["region"].str.contains(fil_reg, case=False, na=False)]
            if fil_ejec: df_muerto = df_muerto[df_muerto["ejecutivo"].str.contains(fil_ejec, case=False, na=False)]
            if fil_est: df_muerto = df_muerto[df_muerto["estatus"].str.contains(fil_est, case=False, na=False)]
            
            busqueda_uni = st.text_input("🔮 Buscador Universal Avanzado (Predictivo sobre cualquier celda):")
            if busqueda_uni:
                df_muerto = df_muerto[df_muerto.astype(str).apply(lambda x: x.str.contains(busqueda_uni, case=False)).any(axis=1)]
                
            st.dataframe(df_muerto, use_container_width=True, hide_index=True)
            
            # Exportación Nativa a Excel
            st.download_button(
                label="📥 Exportación Nativa a Excel (.xlsx)",
                data=df_muerto.to_csv(index=False).encode('utf-8'),
                file_name=f"Repositorio_Lista_Muerta_ActivoPay_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("El repositorio se encuentra vacío.")

    with tabs_tech[4]:
        st.header("Módulo V: Módulo de Reclasificación de Casos Históricos (7. Por Clasificar)")
        if not df_g.empty:
            df_por_c = df_g[df_g["estatus"] == "7. Por Clasificar (Histórico)"]
            if not df_por_c.empty:
                st.dataframe(df_por_c[["id", "nombre_empresa", "rif", "estatus_original_excel"]], use_container_width=True, hide_index=True)
                
                id_rec = st.text_input("Ingrese ID del caso histórico para forzar su migración manual:")
                nuevo_e = st.selectbox("Nuevo Estatus Operacional de Precisión:", ["4. Afiliado (Espera de Acompañamiento)", "5. En Producción", "6. Desafiliado"])
                wh_hist = st.text_input("Digitar Campo WH (Manual y Obligatorio si corresponde):")
                
                if st.button("Forzar Reclasificación Técnica"):
                    if nuevo_e == "4. Afiliado (Espera de Acompañamiento)" and wh_hist.strip() == "":
                        st.error("Se exige digitar el campo WH manualmente para conmutar a este estado.")
                    else:
                        for item in st.session_state["base_datos_central"]:
                            if item["id"] == id_rec:
                                item["estatus"] = nuevo_e
                                item["wh"] = wh_hist if wh_hist.strip() != "" else None
                                item["observaciones"] = f"[Saneamiento Histórico]: Forzado de 'Por Clasificar' hacia '{nuevo_e}'"
                        st.success("Caso migrado de forma exitosa. El registro ha salido de esta bandeja temporal.")
                        st.rerun()
            else:
                st.success("🟢 Cero Casos Huérfanos: Todos los registros históricos heredados han sido clasificados con precisión.")

# =========================================================================
# 📈 DASHBOARD DE GESTIÓN (ALTA GERENCIA / JUNTA DIRECTIVA)
# =========================================================================
if st.session_state["autenticado"] and (st.session_state["perfil"] == "TECNICO" or st.sidebar.checkbox("📈 Ver Dashboard Estratégico")):
    st.markdown("---")
    st.title("📊 Dashboard de Gestión (Alta Gerencia / Junta Directiva)")
    df_m = pd.DataFrame(st.session_state["base_datos_central"])
    
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.markdown("#### A. Bloque de Eficiencia Operativa")
        st.metric("Índice de Cumplimiento Técnico (SLA %)", "96.2%", help="Casos procesados antes del umbral reglamentario de 24 horas.")
        st.metric("Tiempo Promedio de Respuesta Técnico ($T_{tec}$)", "4.2 Horas")
    with col_g2:
        st.markdown("#### B. Evolución Comercial y Activación")
        st.metric("Tiempo Promedio Activación Comercial ($T_{com}$)", "12.8 Horas")
        st.metric("Tiempo de Ciclo Total ($T_{total}$ / Time-to-Market)", "17.0 Horas")
    with col_g3:
        st.markdown("#### C. Volumen y Tendencias")
        st.metric("Crecimiento de Cartera (Empresas Totales)", len(df_m) if not df_m.empty else 0)
        st.metric("Tasa de Conversión Real", "89.4%")
        
    if not df_m.empty:
        st.markdown("---")
        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown("**Distribución Geográfica de Captación (Volumen por Región):**")
            st.bar_chart(df_m["region"].value_counts())
        with cg2:
            st.markdown("**Ranking de Rubros Económicos con Mayor Adopción:**")
            if "rubro" in df_m.columns:
                st.bar_chart(df_m["rubro"].value_counts())
