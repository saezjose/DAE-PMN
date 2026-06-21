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
   
    st.header("Mapa Visual")
    st.caption("Panel operativo de reservas, estados y asignacion de mesas.")

    registro_mesas = obtener_registro_mesas()
    total_mesas = len(registro_mesas)
    disponibles = sum(1 for datos in registro_mesas.values() if datos["estado"] == "DISPONIBLE")
    ocupadas = sum(1 for datos in registro_mesas.values() if datos["estado"] == "OCUPADA")
    limpieza = sum(1 for datos in registro_mesas.values() if datos["estado"] == "EN LIMPIEZA")

    st.markdown(
        f"""
        <div class="pmn-chip-row">
            <span class="pmn-chip accent">Mesas Totales: {total_mesas}</span>
            <span class="pmn-chip ok">Disponibles: {disponibles}</span>
            <span class="pmn-chip bad">Ocupadas: {ocupadas}</span>
            <span class="pmn-chip warn">En Limpieza: {limpieza}</span>
            <span class="pmn-chip">Reservas en Espera: {len(st.session_state.lista_espera_e1)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tiempo_restante = "-"
    if st.session_state.reserva_A == "OCUPADA" and st.session_state.checkin_time is not None:
        transcurrido = int(
            (st.session_state.reloj_sim - st.session_state.checkin_time).total_seconds() // 60
        )
        restante = st.session_state.duracion_bloque_min - transcurrido
        tiempo_restante = f"{max(0, restante)} min"

    
  
    k1, k2, k3 = st.columns(3)
    import database as db
    total_cortesias_reales = db.obtener_total_cortesias_db()

    k1.metric("Estado Reserva", st.session_state.reserva_A)
    k2.metric("Tiempo restante bloque", tiempo_restante)
    k3.metric("Costo cortesia acumulado", f"${total_cortesias_reales:,} CLP")

    st.info(f"Estado del flujo actual: {estado_flujo_actual()}")

    st.markdown("### Leyenda visual")
    st.markdown(
        """
        <div class="pmn-chip-row">
            <span class="pmn-chip ok">Disponible</span>
            <span class="pmn-chip bad">Ocupada</span>
            <span class="pmn-chip warn">En limpieza</span>
            <span class="pmn-chip accent">Reservada / Cluster</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Mapa visual del salon")
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

    st.markdown("#### Interior")
    for fila in range(0, len(mesas_interior), 3):
        columnas = st.columns(3)
        for idx, mesa in enumerate(mesas_interior[fila:fila + 3]):
            with columnas[idx]:
                render_mesa_card(mesa[0], mesa[1], mesa[2])

    st.markdown("#### Terraza")
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
    
                import database as db
                
                
                reserva_inicio_dt = st.session_state.reloj_sim + timedelta(minutes=10)
                reserva_fin_dt = reserva_inicio_dt + timedelta(minutes=st.session_state.duracion_bloque_min)
                
                
                inicio_iso = reserva_inicio_dt.strftime("%Y-%m-%d %H:%M:%S")
                fin_iso = reserva_fin_dt.strftime("%Y-%m-%d %H:%M:%S")
                
                exito_registro = db.registrar_reserva_db(
                    cliente=reserva_label,
                    cantidad=st.session_state.reserva_pax,
                    mesa_id=mesa_asignada,
                    inicio_str=inicio_iso,
                    fin_str=fin_iso
                )
                
                if exito_registro:
                    st.session_state.mesa_reservada = mesa_asignada
                    estado_actual = get_estado_mesa(mesa_asignada)
                    if estado_actual != "OCUPADA":
                        set_estado_mesa(mesa_asignada, "RESERVADA")
                    st.session_state.reserva_A = "RESERVADA"
                    st.session_state.reserva_inicio = reserva_inicio_dt
                    st.session_state.no_show_deadline = reserva_inicio_dt + timedelta(minutes=15)
                    st.success(f"¡Reserva grabada con éxito en {mesa_asignada} de forma persistente!")
                    st.rerun()
                else:
                    st.error(f" Choque de Horarios (Regla D1): La {mesa_asignada} ya está comprometida en el rango {inicio_iso[-8:-3]} - {fin_iso[-8:-3]} en SQLite. Registro rechazado.")

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
        
        # 🔥 SOLUCIÓN: El botón transaccional ahora vive en el estado correcto de tu flujo
        if st.button("Crear Cluster Logico (Mesa 12 + Mesa 05)", use_container_width=True):
            import database as db
            
            exito, mensaje = db.crear_reserva_cluster_db(
                st.session_state.reserva_activa, 
                ["Mesa 12", "Mesa 05"]
            )
            
            if exito:
                st.session_state.cluster_creado = True
                st.session_state.mesa_05 = "BLOQUEADA_C"
                st.session_state.alerta_garzon = True
                st.session_state.reserva_A = "Asignada a Cluster"
                st.session_state.costo_cortesia += 5000
                st.success(f"🚨 {mensaje}")
                st.rerun()
            else:
                st.error(f"❌ Fallo de Atomicidad ACID: {mensaje}")

    if st.session_state.reserva_A == "RESERVADA":
        st.info("Paso 5: al llegar el grupo, se intenta Check-in.")
        if st.button(f"Marcar llegada de {reserva_label} (Check-in)"):
            mesa_asignada = st.session_state.mesa_reservada
            if mesa_asignada and get_estado_mesa(mesa_asignada) == "RESERVADA":
                import database as db
                db.marcar_reserva_ocupada_db(st.session_state.reserva_activa, mesa_asignada)
                st.session_state.reserva_A = "OCUPADA"
                set_estado_mesa(mesa_asignada, "OCUPADA")
                st.session_state.checkin_time = st.session_state.reloj_sim
                st.session_state.no_show_deadline = None
            else:
                st.session_state.reserva_A = "Check-in: Esperando Mesa"
                st.session_state.no_show_deadline = None
            st.rerun()

        st.markdown("---")
        st.markdown("##### 📞 ¿El cliente llamó para avisar un retraso? (Excepción E1)")
        
        with st.expander("Registrar Aviso de Retraso / Cortesía Financiera"):
            col_min, col_costo = st.columns(2)
            with col_min:
                minutos_atraso = st.number_input("Minutos de postergación:", min_value=5, max_value=45, value=15, step=5)
            with col_costo:
                monto_cortesia = st.number_input("Costo de la cortesía (CLP):", min_value=0, value=15000, step=5000)
                
            if st.button("Aplicar Excepción E1 y Postergar Bloque", use_container_width=True):
                import database as db
                exito, mensaje = db.registrar_retraso_cortesia_db(
                    st.session_state.reserva_activa, 
                    minutos_atraso, 
                    monto_cortesia
                )
                if exito:
                    if st.session_state.reserva_inicio is not None:
                        st.session_state.reserva_inicio += timedelta(minutes=minutos_atraso)
                    if st.session_state.no_show_deadline is not None:
                        st.session_state.no_show_deadline += timedelta(minutes=minutos_atraso)
                    st.success(f"✅ {mensaje}")
                    st.toast("💰 Control Financiero: Pérdida por cortesía registrada en disco.", icon="🚨")
                    st.rerun()
                else:
                    st.error(f"🚨 Operación Abortada: {mensaje}")

    if st.session_state.reserva_A == "NO_SHOW":
        st.error("E2 - Regla No-Show activada: se supero la tolerancia de 15 min.")

    if st.session_state.reserva_A == "Asignada a Cluster":
        st.info("Cluster creado. Esperando liberacion fisica para sentar la reserva.")
        st.caption(f"La reserva activa sigue siendo {reserva_label} ({st.session_state.reserva_pax} personas).")
        if st.session_state.mesa_12 == "DISPONIBLE" and st.button(f"Sentar {reserva_label}"):
            st.session_state.reserva_A = "OCUPADA"
            st.session_state.mesa_12 = "OCUPADA"
            st.session_state.checkin_time = st.session_state.reloj_sim
            st.rerun()