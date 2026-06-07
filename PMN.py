## Para hacer correr el proyecto
## python -m streamlit run PMN.py

from datetime import datetime, timedelta
import hashlib
import hmac
import random
import time

import streamlit as st
from database import inicializar_base_de_datos, validar_identidad, obtener_usuario_por_correo
from view_recepcionista import render_recepcionista_view
from view_garzon import render_garzon_view


AUTH_TOKEN_SECRET = "pmn-auth-secret-v1"
AUTH_TOKEN_TTL_SECONDS = 8 * 60 * 60


MESAS_CAPACIDAD = {
    "Mesa 12": 6,
    "Mesa 05": 2,
    "Mesa 01": 4,
    "Mesa 02": 4,
    "Mesa 03": 2,
    "Mesa 04": 2,
}

MESAS_ZONA = {
    "Mesa 12": "Interior",
    "Mesa 05": "Interior",
    "Mesa 01": "Interior",
    "Mesa 02": "Interior",
    "Mesa 03": "Terraza",
    "Mesa 04": "Terraza",
}

MESAS_FIJAS = list(MESAS_CAPACIDAD.keys())


def init_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    defaults = {
        "reloj_sim": now,
        "mesa_12": "OCUPADA",
        "mesa_05": "DISPONIBLE",
        "reserva_A": "CONFIRMA",
        "reserva_activa": "Reserva A",
        "reserva_pax": 4,
        "reserva_zona": random.choice(["Interior", "Terraza"]),
        "mesa_reservada": None,
        "next_reserva_idx": 2,
        "reservas_pendientes": [],
        "lista_espera_e1": [],
        "cluster_creado": False,
        "alerta_garzon": False,
        "costo_cortesia": 0,
        "duracion_bloque_min": 90,
        "reserva_inicio": None,
        "no_show_deadline": None,
        "checkin_time": None,
        "limpieza_inicio_sim": None,
        "alerta_e3_emitida": False,
        "alerta_colision": False,
        "mitigacion_step": 0,
        "mesa_objetivo_garzon": "Mesa 12",
        "limpieza_inicio_por_mesa": {
            "Mesa 12": None,
            "Mesa 05": None,
            "Mesa 01": None,
            "Mesa 02": None,
            "Mesa 03": None,
            "Mesa 04": None,
        },
        "mesas_adicionales": {},
        "nueva_mesa_nombre": "Mesa 07",
        "nueva_mesa_capacidad": 2,
        "nueva_mesa_zona": "Interior",
        "db_ready": False,
        "auth_ok": False,
        "auth_correo": "",
        "auth_nombre": "",
        "auth_rol": "",
        "auth_login_at": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def ensure_db_ready() -> None:
    if st.session_state.db_ready:
        return

    inicializar_base_de_datos()
    st.session_state.db_ready = True


def marcar_sesion_autenticada(correo: str, nombre: str, rol: str) -> None:
    st.session_state.auth_ok = True
    st.session_state.auth_correo = correo
    st.session_state.auth_nombre = nombre
    st.session_state.auth_rol = rol
    st.session_state.auth_login_at = datetime.now().isoformat(timespec="seconds")
    guardar_token_auth_url(correo, rol)


def esta_autenticado() -> bool:
    return bool(
        st.session_state.get("auth_ok")
        and st.session_state.get("auth_correo")
        and st.session_state.get("auth_rol")
    )


def resetear_simulacion_preservando_auth() -> None:
    claves_auth = {
        "db_ready",
        "auth_ok",
        "auth_correo",
        "auth_nombre",
        "auth_rol",
        "auth_login_at",
    }
    snapshot_auth = {k: st.session_state.get(k) for k in claves_auth}

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    init_state()
    for key, value in snapshot_auth.items():
        st.session_state[key] = value


def cerrar_sesion() -> None:
    st.session_state.auth_ok = False
    st.session_state.auth_correo = ""
    st.session_state.auth_nombre = ""
    st.session_state.auth_rol = ""
    st.session_state.auth_login_at = None
    limpiar_token_auth_url()


def crear_firma_token(correo: str, rol: str, issued_at: int) -> str:
    mensaje = f"{correo}|{rol}|{issued_at}".encode("utf-8")
    return hmac.new(AUTH_TOKEN_SECRET.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()


def guardar_token_auth_url(correo: str, rol: str) -> None:
    issued_at = int(time.time())
    firma = crear_firma_token(correo, rol, issued_at)
    st.query_params.update(
        {
            "auth_correo": correo,
            "auth_rol": rol,
            "auth_iat": str(issued_at),
            "auth_sig": firma,
        }
    )


def limpiar_token_auth_url() -> None:
    for key in ["auth_correo", "auth_rol", "auth_iat", "auth_sig"]:
        if key in st.query_params:
            del st.query_params[key]


def restaurar_sesion_desde_url() -> None:
    if esta_autenticado():
        return

    correo = st.query_params.get("auth_correo", "")
    rol = st.query_params.get("auth_rol", "")
    issued_at_txt = st.query_params.get("auth_iat", "")
    firma = st.query_params.get("auth_sig", "")

    if not correo or not rol or not issued_at_txt or not firma:
        return

    try:
        issued_at = int(issued_at_txt)
    except ValueError:
        limpiar_token_auth_url()
        return

    ahora = int(time.time())
    if ahora - issued_at > AUTH_TOKEN_TTL_SECONDS:
        limpiar_token_auth_url()
        return

    firma_esperada = crear_firma_token(correo, rol, issued_at)
    if not hmac.compare_digest(firma_esperada, firma):
        limpiar_token_auth_url()
        return

    usuario = obtener_usuario_por_correo(correo)
    if usuario is None:
        limpiar_token_auth_url()
        return

    nombre_db, rol_db = usuario
    if rol_db != rol:
        limpiar_token_auth_url()
        return

    st.session_state.auth_ok = True
    st.session_state.auth_correo = correo
    st.session_state.auth_nombre = nombre_db
    st.session_state.auth_rol = rol_db
    st.session_state.auth_login_at = datetime.now().isoformat(timespec="seconds")


def render_login() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 15% 20%, rgba(83, 146, 255, 0.18), transparent 30%),
                radial-gradient(circle at 85% 10%, rgba(255, 156, 79, 0.16), transparent 28%),
                linear-gradient(145deg, #0f172a 0%, #0b1220 60%, #0f1a2f 100%);
        }
        [data-testid="stHeader"] { background: transparent; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 1.25, 1])
    with col_center:
        st.markdown("## Acceso PMN")
        st.caption("Ingresa con tu correo corporativo y contrasena para usar el sistema.")

        with st.form("form_login", clear_on_submit=False):
            correo = st.text_input("Correo electronico", placeholder="usuario@restaurante.cl")
            password = st.text_input("Contrasena", type="password")
            submit_login = st.form_submit_button("Iniciar sesion", use_container_width=True)

            if submit_login:
                correo_limpio = correo.strip().lower()
                if not correo_limpio or not password.strip():
                    st.error("Completa correo y contrasena para continuar.")
                else:
                    registro = validar_identidad(correo_limpio, password)
                    if registro is None:
                        st.error("Credenciales invalidas. Verifica tus datos.")
                    else:
                        nombre, rol = registro
                        marcar_sesion_autenticada(correo_limpio, nombre, rol)
                        st.rerun()


def fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%H:%M")


def nombre_reserva(idx: int) -> str:
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if 1 <= idx <= len(letras):
        return f"Reserva {letras[idx - 1]}"
    return f"Reserva {idx}"


def crear_reserva_pendiente(idx: int) -> dict:
    return {
        "nombre": nombre_reserva(idx),
        "pax": random.randint(2, 6),
        "zona": random.choice(["Interior", "Terraza"]),
    }


def estado_flujo_actual() -> str:
    if st.session_state.reserva_A == "RESERVADA" and st.session_state.mesa_reservada:
        return f"{st.session_state.mesa_reservada} ({st.session_state.reserva_zona}) reservada para {st.session_state.reserva_pax} personas"
    estado = st.session_state.reserva_A
    mapping = {
        "CONFIRMA": "Solicitud recibida",
        "RESERVADA": "Mesa reservada y bloque configurado",
        "E1: Protocolo de Espera": "Protocolo de espera activo",
        "NO_SHOW": "No-Show aplicado",
        "Check-in: Esperando Mesa": "Protocolo de espera activo",
        "Asignada a Cluster": "Cluster creado y en espera de liberacion",
        "SENTADA": "Servicio en curso",
        "COMPLETADA": "Flujo principal completado",
    }
    return mapping.get(estado, estado)


def render_mesa_card(nombre: str, capacidad: int, estado: str) -> None:
    zona = MESAS_ZONA.get(nombre, "Interior")
    etiqueta = f"**{nombre}** (Cap. {capacidad})\n\nZona: {zona}\n\nEstado: {estado}"
    if estado == "OCUPADA":
        st.error(etiqueta)
    elif estado in {"EN LIMPIEZA", "BLOQUEADA_C", "RESERVADA"}:
        st.warning(etiqueta)
    else:
        st.success(etiqueta)


def card_style_for_estado(estado: str, selected: bool = False) -> str:
    base = {
        "DISPONIBLE": "background: rgba(16, 75, 47, 0.95); color: #47f08c; border: 1px solid rgba(71, 240, 140, 0.25);",
        "OCUPADA": "background: rgba(76, 37, 45, 0.95); color: #ff6464; border: 1px solid rgba(255, 100, 100, 0.25);",
        "EN LIMPIEZA": "background: rgba(80, 79, 22, 0.95); color: #fff08a; border: 1px solid rgba(255, 240, 138, 0.25);",
        "RESERVADA CLUSTER": "background: rgba(80, 79, 22, 0.95); color: #fff08a; border: 1px solid rgba(255, 240, 138, 0.25);",
        "RESERVADA": "background: rgba(120, 82, 18, 0.95); color: #ffd36a; border: 1px solid rgba(255, 211, 106, 0.25);",
    }.get(estado, "background: rgba(40, 40, 40, 0.95); color: white; border: 1px solid rgba(255,255,255,0.12);")

    if selected:
        base += " box-shadow: 0 0 0 2px #2f8cff inset; transform: translateY(-1px);"
    return base


def obtener_registro_mesas() -> dict:
    registro = {}
    for nombre in MESAS_FIJAS:
        registro[nombre] = {
            "capacidad": MESAS_CAPACIDAD[nombre],
            "zona": MESAS_ZONA[nombre],
            "estado": get_estado_mesa(nombre),
        }

    for nombre, datos in st.session_state.mesas_adicionales.items():
        registro[nombre] = {
            "capacidad": datos["capacidad"],
            "zona": datos["zona"],
            "estado": datos["estado"],
        }

    return registro


def set_estado_mesa(nombre: str, estado: str) -> None:
    estado_actual = get_estado_mesa(nombre)

    if estado == "RESERVADA" and estado_actual != "DISPONIBLE":
        return

    if estado == "EN LIMPIEZA" and estado_actual not in {"OCUPADA"}:
        return

    if estado == "DISPONIBLE" and estado_actual not in {"EN LIMPIEZA"}:
        return

    if nombre == "Mesa 12":
        st.session_state.mesa_12 = estado
        if estado == "EN LIMPIEZA":
            st.session_state.limpieza_inicio_por_mesa["Mesa 12"] = st.session_state.reloj_sim
        elif estado == "DISPONIBLE":
            st.session_state.limpieza_inicio_por_mesa["Mesa 12"] = None
            procesar_lista_espera_si_hay_mesa_disponible()
        return

    if nombre == "Mesa 05":
        st.session_state.mesa_05 = estado
        if estado == "EN LIMPIEZA":
            st.session_state.limpieza_inicio_por_mesa["Mesa 05"] = st.session_state.reloj_sim
        elif estado == "DISPONIBLE":
            st.session_state.limpieza_inicio_por_mesa["Mesa 05"] = None
            procesar_lista_espera_si_hay_mesa_disponible()
        return

    if nombre not in st.session_state.mesas_adicionales:
        st.session_state.mesas_adicionales[nombre] = {
            "capacidad": MESAS_CAPACIDAD.get(nombre, 2),
            "zona": MESAS_ZONA.get(nombre, "Interior"),
            "estado": "DISPONIBLE",
        }

    st.session_state.mesas_adicionales[nombre]["estado"] = estado
    if estado == "EN LIMPIEZA":
        st.session_state.limpieza_inicio_por_mesa[nombre] = st.session_state.reloj_sim
    elif estado == "DISPONIBLE":
        st.session_state.limpieza_inicio_por_mesa[nombre] = None
        procesar_lista_espera_si_hay_mesa_disponible()


def get_estado_mesa(nombre: str) -> str:
    if nombre == "Mesa 12":
        return st.session_state.mesa_12
    if nombre == "Mesa 05":
        if st.session_state.mesa_05 == "BLOQUEADA_C":
            return "RESERVADA CLUSTER"
        return st.session_state.mesa_05
    if nombre in st.session_state.mesas_adicionales:
        return st.session_state.mesas_adicionales[nombre]["estado"]
    return "DISPONIBLE"


def get_capacidad_mesa(nombre: str) -> int:
    if nombre in MESAS_CAPACIDAD:
        return MESAS_CAPACIDAD[nombre]
    return st.session_state.mesas_adicionales[nombre]["capacidad"]


def get_zona_mesa(nombre: str) -> str:
    if nombre in MESAS_ZONA:
        return MESAS_ZONA[nombre]
    return st.session_state.mesas_adicionales[nombre]["zona"]


def asignar_mesa_por_capacidad(pax: int, zona_preferida: str) -> str | None:
    candidatas = []
    for nombre, datos in obtener_registro_mesas().items():
        capacidad = datos["capacidad"]
        # Filtro corregido: si es "Cualquiera", ignora la restriccion espacial
        match_zona = (zona_preferida == "Cualquiera" or datos["zona"] == zona_preferida)
        
        if capacidad >= pax and datos["estado"] == "DISPONIBLE" and match_zona:
            candidatas.append((capacidad, nombre))

    if not candidatas:
        return None

    candidatas.sort(key=lambda item: (item[0], item[1]))
    return candidatas[0][1]


def get_limpieza_inicio(nombre: str):
    return st.session_state.limpieza_inicio_por_mesa.get(nombre)


def get_limpieza_restante(nombre: str) -> int:
    inicio = get_limpieza_inicio(nombre)
    if inicio is None:
        return 0
    elapsed = int((st.session_state.reloj_sim - inicio).total_seconds())
    return max(0, 180 - elapsed)


def tiempo_proyeccion_mesa(nombre: str) -> int | None:
    estado = get_estado_mesa(nombre)
    if estado == "DISPONIBLE":
        return 0
    if estado == "EN LIMPIEZA":
        return get_limpieza_restante(nombre)
    return None


def sugerir_mesa_para_pax(pax: int, zona_preferida: str) -> tuple[str, int] | None:
    candidatos = []
    for nombre, datos in obtener_registro_mesas().items():
        capacidad = datos["capacidad"]
        # Filtro corregido: si es "Cualquiera", ignora la restriccion espacial
        match_zona = (zona_preferida == "Cualquiera" or datos["zona"] == zona_preferida)
        
        if capacidad >= pax and match_zona:
            tiempo = tiempo_proyeccion_mesa(nombre)
            if tiempo is not None:
                candidatos.append((tiempo, capacidad, nombre))

    if not candidatos:
        return None

    candidatos.sort(key=lambda item: (item[0], item[1], item[2]))
    mejor = candidatos[0]
    return mejor[2], mejor[0]


def mesa_disponible_para_pax(pax: int, zona_preferida: str) -> str | None:
    sugerida = sugerir_mesa_para_pax(pax, zona_preferida)
    if sugerida is None:
        return None
    nombre_mesa, tiempo = sugerida
    return nombre_mesa if tiempo == 0 else None


def agregar_a_lista_espera(reserva_nombre: str, pax: int, zona_preferida: str) -> None:
    sugerencia = sugerir_mesa_para_pax(pax, zona_preferida)
    mesa_sugerida = sugerencia[0] if sugerencia else None
    espera_segundos = sugerencia[1] if sugerencia else None
    st.session_state.lista_espera_e1.append(
        {
            "reserva": reserva_nombre,
            "pax": pax,
            "zona": zona_preferida,
            "mesa_sugerida": mesa_sugerida,
            "espera_segundos": espera_segundos,
        }
    )


def intentar_asignar_desde_espera() -> bool:
    for indice, entrada in enumerate(st.session_state.lista_espera_e1):
        mesa = mesa_disponible_para_pax(entrada["pax"], entrada["zona"])
        if mesa is None:
            continue

        st.session_state.lista_espera_e1.pop(indice)
        st.session_state.reserva_activa = entrada["reserva"]
        st.session_state.reserva_pax = entrada["pax"]
        st.session_state.mesa_reservada = mesa
        set_estado_mesa(mesa, "RESERVADA")
        st.session_state.reserva_A = "RESERVADA"
        st.session_state.reserva_inicio = st.session_state.reloj_sim + timedelta(minutes=10)
        st.session_state.no_show_deadline = st.session_state.reserva_inicio + timedelta(minutes=15)
        st.session_state.checkin_time = None
        return True

    return False


def procesar_lista_espera_si_hay_mesa_disponible() -> bool:
    if not st.session_state.lista_espera_e1:
        return False

    return intentar_asignar_desde_espera()


def render_selectable_mesa(nombre: str) -> None:
    estado_mesa = get_estado_mesa(nombre)
    selected = st.session_state.mesa_objetivo_garzon == nombre
    estado_label = estado_mesa

    html_label = f"<div style='font-size: 1.05rem; font-weight: 700;'>{nombre}</div><div style='margin-top: 0.6rem; font-size: 0.95rem; opacity: 0.95;'>Estado: {estado_label}</div>"
    st.markdown(
        f"""
        <div style="padding: 0.9rem 1rem; border-radius: 0.8rem; {card_style_for_estado(estado_mesa, selected)}">
            {html_label}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(f"Seleccionar {nombre}", key=f"sel_{nombre}", use_container_width=True):
        st.session_state.mesa_objetivo_garzon = nombre
        st.rerun()


def limpiar_y_liberar_mesas() -> None:
    st.session_state.mesa_12 = "DISPONIBLE"
    st.session_state.mesa_05 = "DISPONIBLE"
    st.session_state.cluster_creado = False
    st.session_state.alerta_garzon = False
    st.session_state.alerta_colision = False
    st.session_state.mitigacion_step = 0
    st.session_state.alerta_e3_emitida = False


def cargar_siguiente_reserva() -> None:
    if not st.session_state.reservas_pendientes:
        return

    siguiente = st.session_state.reservas_pendientes.pop(0)
    st.session_state.reserva_activa = siguiente["nombre"]
    st.session_state.reserva_pax = siguiente["pax"]
    st.session_state.reserva_zona = siguiente["zona"]
    st.session_state.duracion_bloque_min = siguiente.get("tiempo", 90)
    st.session_state.mesa_reservada = None
    st.session_state.reserva_A = "CONFIRMA"
    st.session_state.reserva_inicio = None
    st.session_state.no_show_deadline = None
    st.session_state.checkin_time = None
    st.session_state.cluster_creado = False
    st.session_state.alerta_garzon = False
    st.session_state.alerta_colision = False
    st.session_state.alerta_e3_emitida = False
    st.session_state.mitigacion_step = 0
    if st.session_state.mesa_05 == "BLOQUEADA_C":
        st.session_state.mesa_05 = "DISPONIBLE"


st.set_page_config(layout="wide")
init_state()
ensure_db_ready()
restaurar_sesion_desde_url()

if not esta_autenticado():
    render_login()
    st.stop()

st.title("PMN - Prototipo Navegable de Gestion de Reservas (INFO1163)")
st.caption(
    "Simulacion academica: flujo navegable sin BD, con reglas de no-show, colision y limpieza controlada."
)

header_left, header_right = st.columns([5, 1])
with header_right:
    if st.button("Cerrar Sesion", use_container_width=True):
        cerrar_sesion()
        st.rerun()

rol_actual = st.session_state.auth_rol

with st.sidebar:
    st.markdown("### Control de Simulacion")
    st.caption(f"Usuario: {st.session_state.auth_nombre} | Rol: {rol_actual}")

    st.write(f"Hora simulada: **{fmt_dt(st.session_state.reloj_sim)}**")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("+5 min"):
            st.session_state.reloj_sim += timedelta(minutes=5)
            st.rerun()
    with c2:
        if st.button("+15 min"):
            st.session_state.reloj_sim += timedelta(minutes=15)
            st.rerun()

    st.session_state.simular_colision_futura = st.checkbox(
        "Simular reserva futura en Mesa 12 (colision)", value=True
    )

    if rol_actual == "recepcionista":
        st.markdown("### Agregar mesas")
        nueva_mesa_nombre = st.text_input("Nombre de la mesa", value=st.session_state.nueva_mesa_nombre)
        nueva_mesa_capacidad = st.number_input(
            "Capacidad", min_value=1, max_value=12, value=st.session_state.nueva_mesa_capacidad, step=1
        )
        nueva_mesa_zona = st.selectbox(
            "Zona", options=["Interior", "Terraza"], index=0 if st.session_state.nueva_mesa_zona == "Interior" else 1
        )
        if st.button("Agregar mesa nueva"):
            if nueva_mesa_nombre in MESAS_FIJAS or nueva_mesa_nombre in st.session_state.mesas_adicionales:
                st.warning("Ya existe una mesa con ese nombre.")
            else:
                st.session_state.mesas_adicionales[nueva_mesa_nombre] = {
                    "capacidad": int(nueva_mesa_capacidad),
                    "zona": nueva_mesa_zona,
                    "estado": "DISPONIBLE",
                }
                st.session_state.limpieza_inicio_por_mesa[nueva_mesa_nombre] = None
                st.session_state.nueva_mesa_nombre = f"Mesa {int(nueva_mesa_capacidad) + len(st.session_state.mesas_adicionales):02d}"
                st.session_state.nueva_mesa_capacidad = int(nueva_mesa_capacidad)
                st.session_state.nueva_mesa_zona = nueva_mesa_zona
                st.rerun()

        st.markdown("### Ingreso Manual (Walk-in / Reserva)")
        with st.form("form_ingreso"):
            pax_ingreso = st.number_input("Cantidad de personas", min_value=1, max_value=12, value=2)
            zona_ingreso = st.selectbox("Preferencia de Zona", ["Cualquiera", "Interior", "Terraza"])
            tiempo_ingreso = st.number_input("Tiempo estimado (minutos)", min_value=30, max_value=180, value=90, step=15)
            submit_ingreso = st.form_submit_button("Registrar Ingreso al Sistema")

            if submit_ingreso:
                nueva = {
                    "nombre": nombre_reserva(st.session_state.next_reserva_idx),
                    "pax": pax_ingreso,
                    "zona": zona_ingreso,
                    "tiempo": tiempo_ingreso
                }
                st.session_state.reservas_pendientes.append(nueva)
                st.session_state.next_reserva_idx += 1
                st.rerun()

        st.write(f"Reserva activa: **{st.session_state.reserva_activa}**")
        st.write(f"Personas de la reserva activa: **{st.session_state.reserva_pax}**")
        st.write(f"Zona solicitada: **{st.session_state.reserva_zona}**")
        st.write(f"Mesa reservada: **{st.session_state.mesa_reservada or '-'}**")
        st.write(f"Pendientes: **{len(st.session_state.reservas_pendientes)}**")
        if st.session_state.reservas_pendientes:
            pendientes = [f'{reserva["nombre"]} ({reserva["pax"]} pers., {reserva["zona"]})' for reserva in st.session_state.reservas_pendientes]
            st.caption(" | ".join(pendientes))

        if st.button(
            "Cargar siguiente reserva", disabled=not st.session_state.reservas_pendientes
        ):
            cargar_siguiente_reserva()
            st.rerun()

        if st.button("Revisar lista de espera E1", disabled=not st.session_state.lista_espera_e1):
            if intentar_asignar_desde_espera():
                st.rerun()
            st.rerun()
    else:
        st.caption("Modo garzon: interfaz tablet habilitada.")

    if st.button("Resetear Simulacion"):
        resetear_simulacion_preservando_auth()
        st.rerun()


# Regla automatica de No-Show (D2)
if (
    st.session_state.reserva_A == "RESERVADA"
    and st.session_state.reserva_inicio is not None
    and st.session_state.no_show_deadline is None
):
    st.session_state.no_show_deadline = st.session_state.reserva_inicio + timedelta(minutes=15)

if (
    st.session_state.reserva_A == "RESERVADA"
    and st.session_state.no_show_deadline is not None
    and st.session_state.reloj_sim >= st.session_state.no_show_deadline
):
    st.session_state.reserva_A = "NO_SHOW"
    st.session_state.alerta_garzon = False

if rol_actual == "recepcionista":
    if st.session_state.reserva_A == "NO_SHOW":
        st.warning("No-Show activo: la reserva no llego dentro de la tolerancia.")

    st.markdown("### Indicadores de Control Financiero")
    if st.session_state.costo_cortesia > 0:
        st.metric(
            label="Perdidas por Cortesias Incurridas (Retrasos)",
            value=f"${st.session_state.costo_cortesia} CLP",
            delta=f"+${st.session_state.costo_cortesia} CLP (Colision Critica)",
            delta_color="inverse",
        )
    else:
        st.metric(label="Perdidas por Cortesias Incurridas (Retrasos)", value="$0 CLP")

    st.divider()

    render_recepcionista_view(
        estado_flujo_actual=estado_flujo_actual,
        obtener_registro_mesas=obtener_registro_mesas,
        render_mesa_card=render_mesa_card,
        fmt_dt=fmt_dt,
        asignar_mesa_por_capacidad=asignar_mesa_por_capacidad,
        agregar_a_lista_espera=agregar_a_lista_espera,
        set_estado_mesa=set_estado_mesa,
        get_estado_mesa=get_estado_mesa,
    )

    if st.session_state.reserva_A == "COMPLETADA":
        st.success("Recorrido principal completado con exito.")
        if st.session_state.reservas_pendientes:
            if st.button("Iniciar siguiente reserva pendiente"):
                cargar_siguiente_reserva()
                st.rerun()
elif rol_actual == "garzon":
    render_garzon_view(
        obtener_registro_mesas=obtener_registro_mesas,
        render_selectable_mesa=render_selectable_mesa,
        get_estado_mesa=get_estado_mesa,
        get_limpieza_restante=get_limpieza_restante,
        set_estado_mesa=set_estado_mesa,
    )
else:
    st.error(f"Rol no soportado: {rol_actual}")