import streamlit as st


def render_garzon_view(
    *,
    obtener_registro_mesas,
    render_selectable_mesa,
    get_estado_mesa,
    get_limpieza_restante,
    set_estado_mesa,
) -> None:
    st.header("Garzon (Tablet)")

    st.markdown("### Seleccion visual de mesa")
    mesas_control = list(obtener_registro_mesas().keys())

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
