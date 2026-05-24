## Para hacer correr el proyecto
## python -m streamlit run PMN.py

from datetime import datetime, timedelta
import random

import streamlit as st


MESAS_CAPACIDAD = {
    "Mesa 12": 6,
    "Mesa 05": 2,
    "Mesa 01": 4,
    "Mesa 02": 4,
    "Mesa 03": 2,
    "Mesa 04": 2,
}


def init_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    defaults = {
        "reloj_sim": now,
        "mesa_12": "OCUPADA",
        "mesa_05": "DISPONIBLE",
        "reserva_A": "CONFIRMA",
        "reserva_activa": "Reserva A",
        "reserva_pax": 4,
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
        "mesas_extra": {
            "Mesa 01": "DISPONIBLE",
            "Mesa 02": "OCUPADA",
            "Mesa 03": "DISPONIBLE",
            "Mesa 04": "EN LIMPIEZA",
        },
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
    }


def estado_flujo_actual() -> str:
    if st.session_state.reserva_A == "RESERVADA" and st.session_state.mesa_reservada:
        return f"{st.session_state.mesa_reservada} reservada para {st.session_state.reserva_pax} personas"
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
    etiqueta = f"**{nombre}** (Cap. {capacidad})\n\nEstado: {estado}"
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

    st.session_state.mesas_extra[nombre] = estado
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
    return st.session_state.mesas_extra[nombre]


def get_capacidad_mesa(nombre: str) -> int:
    return MESAS_CAPACIDAD[nombre]


def asignar_mesa_por_capacidad(pax: int) -> str | None:
    candidatas = []
    for nombre, capacidad in MESAS_CAPACIDAD.items():
        if capacidad >= pax and get_estado_mesa(nombre) == "DISPONIBLE":
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


def sugerir_mesa_para_pax(pax: int) -> tuple[str, int] | None:
    candidatos: list[tuple[int, int, str]] = []
    for nombre, capacidad in MESAS_CAPACIDAD.items():
        if capacidad >= pax:
            tiempo = tiempo_proyeccion_mesa(nombre)
            if tiempo is not None:
                candidatos.append((tiempo, capacidad, nombre))

    if not candidatos:
        return None

    candidatos.sort(key=lambda item: (item[0], item[1], item[2]))
    mejor = candidatos[0]
    return mejor[2], mejor[0]


def mesa_disponible_para_pax(pax: int) -> str | None:
    sugerida = sugerir_mesa_para_pax(pax)
    if sugerida is None:
        return None
    nombre_mesa, tiempo = sugerida
    return nombre_mesa if tiempo == 0 else None


def agregar_a_lista_espera(reserva_nombre: str, pax: int) -> None:
    sugerencia = sugerir_mesa_para_pax(pax)
    mesa_sugerida = sugerencia[0] if sugerencia else None
    espera_segundos = sugerencia[1] if sugerencia else None
    st.session_state.lista_espera_e1.append(
        {
            "reserva": reserva_nombre,
            "pax": pax,
            "mesa_sugerida": mesa_sugerida,
            "espera_segundos": espera_segundos,
        }
    )


def intentar_asignar_desde_espera() -> bool:
    for indice, entrada in enumerate(st.session_state.lista_espera_e1):
        mesa = mesa_disponible_para_pax(entrada["pax"])
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
    st.session_state.mesa_reservada = None
    st.session_state.reserva_A = "CONFIRMA"
    st.session_state.reserva_inicio = None
    st.session_state.no_show_deadline = None
    st.session_state.checkin_time = None
    st.session_state.duracion_bloque_min = 90
    st.session_state.cluster_creado = False
    st.session_state.alerta_garzon = False
    st.session_state.alerta_colision = False
    st.session_state.alerta_e3_emitida = False
    st.session_state.mitigacion_step = 0
    if st.session_state.mesa_05 == "BLOQUEADA_C":
        st.session_state.mesa_05 = "DISPONIBLE"


st.set_page_config(layout="wide")
init_state()

st.title("PMN - Prototipo Navegable de Gestion de Reservas (INFO1163)")
st.caption(
    "Simulacion academica: flujo navegable sin BD, con reglas de no-show, colision y limpieza controlada."
)

with st.sidebar:
    st.markdown("### Control de Simulacion")
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

    st.markdown("### Reservas")
    if st.button("Agregar reserva pendiente"):
        nueva = crear_reserva_pendiente(st.session_state.next_reserva_idx)
        st.session_state.reservas_pendientes.append(nueva)
        st.session_state.next_reserva_idx += 1
        st.rerun()

    st.write(f"Reserva activa: **{st.session_state.reserva_activa}**")
    st.write(f"Personas de la reserva activa: **{st.session_state.reserva_pax}**")
    st.write(f"Mesa reservada: **{st.session_state.mesa_reservada or '-'}**")
    st.write(f"Pendientes: **{len(st.session_state.reservas_pendientes)}**")
    if st.session_state.reservas_pendientes:
        pendientes = [f'{reserva["nombre"]} ({reserva["pax"]} pers.)' for reserva in st.session_state.reservas_pendientes]
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

    if st.button("Resetear Simulacion"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
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

tag_m12 = "Mesa 12 [Cluster Alfa]" if st.session_state.cluster_creado else "Mesa 12"
tag_m05 = "Mesa 05 [Cluster Alfa]" if st.session_state.cluster_creado else "Mesa 05"
reserva_label = st.session_state.reserva_activa

tab_recepcionista, tab_garzon = st.tabs(["Recepcionista", "Garzon"])

with tab_recepcionista:
    st.header("Recepcionista (Mapa Visual)")
    st.subheader("Mapa Visual del Salon")

    tiempo_restante = "-"
    if st.session_state.reserva_A == "SENTADA" and st.session_state.checkin_time is not None:
        transcurrido = int(
            (st.session_state.reloj_sim - st.session_state.checkin_time).total_seconds() // 60
        )
        restante = st.session_state.duracion_bloque_min - transcurrido
        tiempo_restante = f"{max(0, restante)} min"

    k1, k2, k3 = st.columns(3)
    k1.metric("Estado Reserva", st.session_state.reserva_A)
    k2.metric("Tiempo restante bloque", tiempo_restante)
    k3.metric("Costo cortesia acumulado", f"${st.session_state.costo_cortesia} CLP")

    st.info(f"Estado del flujo actual: {estado_flujo_actual()}")

    st.markdown("**Leyenda visual**")
    l1, l2, l3, l4 = st.columns(4)
    l1.success("Disponible")
    l2.error("Ocupada")
    l3.warning("En limpieza")
    l4.warning("Reservada / Cluster")

    st.markdown("**Todas las mesas del salon**")

    estado_m05 = "RESERVADA CLUSTER" if st.session_state.mesa_05 == "BLOQUEADA_C" else st.session_state.mesa_05
    mesas_mapa = [
        (tag_m12, 6, st.session_state.mesa_12),
        (tag_m05, 2, estado_m05),
        ("Mesa 01", 4, st.session_state.mesas_extra["Mesa 01"]),
        ("Mesa 02", 4, st.session_state.mesas_extra["Mesa 02"]),
        ("Mesa 03", 2, st.session_state.mesas_extra["Mesa 03"]),
        ("Mesa 04", 2, st.session_state.mesas_extra["Mesa 04"]),
    ]

    row1 = st.columns(3)
    for idx, mesa in enumerate(mesas_mapa[:3]):
        with row1[idx]:
            render_mesa_card(mesa[0], mesa[1], mesa[2])

    row2 = st.columns(3)
    for idx, mesa in enumerate(mesas_mapa[3:]):
        with row2[idx]:
            render_mesa_card(mesa[0], mesa[1], mesa[2])

    st.markdown("---")
    st.write(f"**Estado {reserva_label}:** `{st.session_state.reserva_A}`")
    st.write(f"Inicio bloque: **{fmt_dt(st.session_state.reserva_inicio)}**")
    st.write(f"Duracion bloque: **{st.session_state.duracion_bloque_min} min**")
    st.write(f"Limite No-Show: **{fmt_dt(st.session_state.no_show_deadline)}**")

    if st.session_state.lista_espera_e1:
        st.markdown("**Lista de Espera E1**")
        for entrada in st.session_state.lista_espera_e1:
            espera_txt = f"{entrada['espera_segundos']} s" if entrada["espera_segundos"] is not None else "sin proyeccion exacta"
            st.write(
                f"- {entrada['reserva']} ({entrada['pax']} pers.) -> {entrada['mesa_sugerida'] or 'sin mesa sugerida'} | espera estimada: {espera_txt}"
            )

    if st.session_state.reserva_A == "RESERVADA" and st.session_state.no_show_deadline is not None:
        mins_to_no_show = int(
            (st.session_state.no_show_deadline - st.session_state.reloj_sim).total_seconds() // 60
        )
        if mins_to_no_show > 0:
            st.info(f"Faltan {mins_to_no_show} min para activar No-Show.")
        else:
            st.warning("Se cumplio la ventana de tolerancia de No-Show.")

    if st.session_state.reserva_A == "CONFIRMA":
        st.info("Paso 1-4: se registra reserva y se asigna bloque en estado RESERVADA.")
        st.caption(f"{reserva_label} es para {st.session_state.reserva_pax} personas.")
        if st.button(f"Registrar {reserva_label} (asignar bloque)"):
            mesa_asignada = asignar_mesa_por_capacidad(st.session_state.reserva_pax)
            if mesa_asignada is None:
                agregar_a_lista_espera(reserva_label, st.session_state.reserva_pax)
                st.session_state.reserva_A = "E1: Protocolo de Espera"
                st.session_state.mesa_reservada = None
                st.warning("No hay mesa disponible con capacidad suficiente. La reserva pasó a lista de espera E1.")
                st.rerun()
            else:
                st.session_state.mesa_reservada = mesa_asignada
                set_estado_mesa(mesa_asignada, "RESERVADA")
                st.session_state.reserva_A = "RESERVADA"
                st.session_state.reserva_inicio = st.session_state.reloj_sim + timedelta(minutes=10)
                st.session_state.no_show_deadline = st.session_state.reserva_inicio + timedelta(
                    minutes=15
                )
                st.rerun()

    if st.session_state.reserva_A == "E1: Protocolo de Espera":
        st.warning("E1 - Protocolo de Espera activo: la reserva quedó en lista de espera hasta que exista una mesa adecuada.")
        if st.session_state.lista_espera_e1:
            entrada = next((item for item in st.session_state.lista_espera_e1 if item["reserva"] == reserva_label), None)
            if entrada:
                st.caption(
                    f"Sugerencia: {entrada['mesa_sugerida'] or 'sin sugerencia'} | espera estimada: "
                    f"{entrada['espera_segundos']} s" if entrada["espera_segundos"] is not None else "sin proyeccion exacta"
                )
        st.caption("Usa 'Revisar lista de espera E1' en el sidebar cuando haya una mesa disponible.")

    if st.session_state.reserva_A == "RESERVADA":
        st.info("Paso 5: al llegar el grupo, se intenta Check-in.")
        if st.button(f"Marcar llegada de {reserva_label} (Check-in)"):
            mesa_asignada = st.session_state.mesa_reservada
            if mesa_asignada and get_estado_mesa(mesa_asignada) == "RESERVADA":
                st.session_state.reserva_A = "SENTADA"
                set_estado_mesa(mesa_asignada, "OCUPADA")
                st.session_state.checkin_time = st.session_state.reloj_sim
                st.session_state.no_show_deadline = None
            else:
                st.session_state.reserva_A = "Check-in: Esperando Mesa"
                st.session_state.no_show_deadline = None
            st.rerun()

    if st.session_state.reserva_A == "NO_SHOW":
        st.error("E2 - Regla No-Show activada: se supero la tolerancia de 15 min.")

    if st.session_state.reserva_A == "Check-in: Esperando Mesa":
        st.warning("E1 - Protocolo de espera activo: no hay mesa adecuada disponible.")
        if st.button("Crear Cluster Logico (Mesa 12 + Mesa 05)"):
            st.session_state.cluster_creado = True
            st.session_state.mesa_05 = "BLOQUEADA_C"
            st.session_state.alerta_garzon = True
            st.session_state.reserva_A = "Asignada a Cluster"
            st.session_state.costo_cortesia += 5000
            st.rerun()

    if st.session_state.reserva_A == "Asignada a Cluster":
        st.info("Cluster creado. Esperando liberacion fisica para sentar la reserva.")
        st.caption(f"La reserva activa sigue siendo {reserva_label} ({st.session_state.reserva_pax} personas).")
        if st.session_state.mesa_12 == "DISPONIBLE" and st.button(
            f"Sentar {reserva_label}"
        ):
            st.session_state.reserva_A = "SENTADA"
            st.session_state.mesa_12 = "OCUPADA"
            st.session_state.checkin_time = st.session_state.reloj_sim
            st.rerun()

with tab_garzon:
    st.header("Garzon (Tablet)")

    st.markdown("### Seleccion visual de mesa")
    mesas_control = ["Mesa 12", "Mesa 05", *st.session_state.mesas_extra.keys()]

    s_row1 = st.columns(3)
    for idx, mesa_nombre in enumerate(mesas_control[:3]):
        with s_row1[idx]:
            render_selectable_mesa(mesa_nombre)

    s_row2 = st.columns(3)
    for idx, mesa_nombre in enumerate(mesas_control[3:]):
        with s_row2[idx]:
            render_selectable_mesa(mesa_nombre)

    mesa_objetivo = st.session_state.mesa_objetivo_garzon
    st.info(f"Mesa seleccionada: {mesa_objetivo}")

    st.markdown("### Control directo de mesas")
    st.caption("Checkout = se retira el cliente y la mesa pasa a limpieza. Mesa lista = termino la limpieza y se habilita la mesa.")
    g1 = st.columns(1)[0]
    estado_seleccionado = get_estado_mesa(mesa_objetivo)
    restante_limpieza = get_limpieza_restante(mesa_objetivo)
    puede_disponible = estado_seleccionado == "EN LIMPIEZA" and restante_limpieza == 0

    if st.button("Marcar MESA LISTA / DISPONIBLE", disabled=not puede_disponible):
            set_estado_mesa(mesa_objetivo, "DISPONIBLE")
            st.rerun()

    if estado_seleccionado == "EN LIMPIEZA" and restante_limpieza > 0:
        st.caption(f"Bloqueo activo: faltan {restante_limpieza} s para poder marcarla disponible.")
    elif estado_seleccionado not in {"OCUPADA", "EN LIMPIEZA"}:
        st.caption("Solo puedes pasar de OCUPADA a limpieza con Checkout, y de limpieza a disponible con Mesa lista.")

    if st.session_state.alerta_garzon and st.session_state.mesa_12 == "OCUPADA":
        st.info("Prioridad Alta: liberar Mesa 12 para cluster.")

    # Monitoreo de estadia (E3)
    if st.session_state.reserva_A == "SENTADA" and st.session_state.checkin_time is not None:
        transcurrido = int(
            (st.session_state.reloj_sim - st.session_state.checkin_time).total_seconds() // 60
        )
        restante = st.session_state.duracion_bloque_min - transcurrido

        st.write(f"Tiempo transcurrido: **{max(0, transcurrido)} min**")
        st.write(f"Tiempo restante bloque: **{restante} min**")

        if restante <= 15 and not st.session_state.alerta_e3_emitida:
            st.warning("E3 - Alerta preventiva: ofrecer ultimo trago/postre.")
            if st.button("Registrar aviso preventivo E3"):
                st.session_state.alerta_e3_emitida = True
                st.rerun()

        if st.session_state.alerta_e3_emitida:
            st.markdown("### Decision de Extension")
            if st.button("Cliente solicita extender +30 min"):
                if st.session_state.simular_colision_futura:
                    st.session_state.alerta_colision = True
                    st.session_state.costo_cortesia += 5000
                else:
                    st.session_state.duracion_bloque_min += 30
                    st.session_state.alerta_e3_emitida = False
                st.rerun()

    # Mitigacion de colision critica
    if st.session_state.alerta_colision:
        st.error("Colision critica: no se puede extender por reserva futura.")
        if st.session_state.mitigacion_step == 0:
            if st.button("Entregar cuenta al comensal"):
                st.session_state.mitigacion_step = 1
                st.rerun()
        elif st.session_state.mitigacion_step == 1:
            if st.button("Avisar al Administrador"):
                st.session_state.mitigacion_step = 2
                st.rerun()
        elif st.session_state.mitigacion_step == 2:
            if st.button("Registrar reubicacion (barra/terraza)"):
                st.session_state.mitigacion_step = 3
                st.rerun()
        else:
            st.success("Mitigacion completada. Listo para registrar salida.")

    can_checkout = estado_seleccionado == "OCUPADA"
    if st.button(
        f"Registrar salida de comensales (Checkout) de {mesa_objetivo}",
        disabled=not can_checkout,
    ):
        set_estado_mesa(mesa_objetivo, "EN LIMPIEZA")
        st.rerun()

    if get_estado_mesa(mesa_objetivo) == "EN LIMPIEZA":
        st.write(f"Accion: Higienizando {mesa_objetivo} (bloqueo real de 3 minutos).")
        remaining = get_limpieza_restante(mesa_objetivo)
        st.write(f"Tiempo restante para habilitar: **{remaining} s**")

        if remaining > 0:
            st.info("Todavia no se puede habilitar la mesa.")

        if st.button(f"Mesa lista para {mesa_objetivo}", disabled=remaining > 0):
            set_estado_mesa(mesa_objetivo, "DISPONIBLE")
            if mesa_objetivo == "Mesa 12":
                if st.session_state.reserva_A in {"Asignada a Cluster", "Check-in: Esperando Mesa"}:
                    st.session_state.reserva_A = "SENTADA"
                    st.session_state.mesa_12 = "OCUPADA"
                    st.session_state.checkin_time = st.session_state.reloj_sim
                elif st.session_state.reserva_A == "SENTADA":
                    st.session_state.reserva_A = "COMPLETADA"
            st.rerun()


if st.session_state.reserva_A == "COMPLETADA":
    st.success("Recorrido principal completado con exito.")
    if st.session_state.reservas_pendientes:
        if st.button("Iniciar siguiente reserva pendiente"):
            cargar_siguiente_reserva()
            st.rerun()