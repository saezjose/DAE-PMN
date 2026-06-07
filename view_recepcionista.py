import streamlit as st
from datetime import timedelta


def render_recepcionista_view(
    *,
    estado_flujo_actual,
    obtener_registro_mesas,
    render_mesa_card,
    fmt_dt,
    asignar_mesa_por_capacidad,
    agregar_a_lista_espera,
    set_estado_mesa,
    get_estado_mesa,
) -> None:
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
    registro_mesas = obtener_registro_mesas()
    mesas_interior = [
        (nombre, datos["capacidad"], datos["estado"])
        for nombre, datos in registro_mesas.items()
        if datos["zona"] == "Interior"
    ]
    mesas_terraza = [
        (nombre, datos["capacidad"], datos["estado"])
        for nombre, datos in registro_mesas.items()
        if datos["zona"] == "Terraza"
    ]

    st.markdown("### Interior")
    for fila in range(0, len(mesas_interior), 3):
        columnas = st.columns(3)
        for idx, mesa in enumerate(mesas_interior[fila:fila + 3]):
            with columnas[idx]:
                render_mesa_card(mesa[0], mesa[1], mesa[2])

    st.markdown("### Terraza")
    for fila in range(0, len(mesas_terraza), 3):
        columnas = st.columns(3)
        for idx, mesa in enumerate(mesas_terraza[fila:fila + 3]):
            with columnas[idx]:
                render_mesa_card(mesa[0], mesa[1], mesa[2])

    st.markdown("---")
    reserva_label = st.session_state.reserva_activa
    st.write(f"**Estado {reserva_label}:** `{st.session_state.reserva_A}`")
    st.write(f"Inicio bloque: **{fmt_dt(st.session_state.reserva_inicio)}**")
    st.write(f"Duracion bloque: **{st.session_state.duracion_bloque_min} min**")
    st.write(f"Limite No-Show: **{fmt_dt(st.session_state.no_show_deadline)}**")

    if st.session_state.lista_espera_e1:
        st.markdown("**Lista de Espera E1**")
        for entrada in st.session_state.lista_espera_e1:
            espera_txt = f"{entrada['espera_segundos']} s" if entrada["espera_segundos"] is not None else "sin proyeccion exacta"
            st.write(
                f"- {entrada['reserva']} ({entrada['pax']} pers., {entrada['zona']}) -> {entrada['mesa_sugerida'] or 'sin mesa sugerida'} | espera estimada: {espera_txt}"
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
        st.caption(f"{reserva_label} es para {st.session_state.reserva_pax} personas y pide zona {st.session_state.reserva_zona}.")
        if st.button(f"Registrar {reserva_label} (asignar bloque)"):
            mesa_asignada = asignar_mesa_por_capacidad(st.session_state.reserva_pax, st.session_state.reserva_zona)
            if mesa_asignada is None:
                agregar_a_lista_espera(reserva_label, st.session_state.reserva_pax, st.session_state.reserva_zona)
                st.session_state.reserva_A = "E1: Protocolo de Espera"
                st.session_state.mesa_reservada = None
                st.warning("No hay mesa disponible con capacidad y zona suficientes. La reserva paso a lista de espera E1.")
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
        st.warning("E1 - Protocolo de Espera activo: la reserva quedo en lista de espera hasta que exista una mesa adecuada.")
        if st.session_state.lista_espera_e1:
            entrada = next((item for item in st.session_state.lista_espera_e1 if item["reserva"] == reserva_label), None)
            if entrada:
                espera_txt = (
                    f"{entrada['espera_segundos']} s" if entrada["espera_segundos"] is not None else "sin proyeccion exacta"
                )
                st.caption(
                    f"Sugerencia: {entrada['mesa_sugerida'] or 'sin sugerencia'} | zona: {entrada['zona']} | espera estimada: {espera_txt}"
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
