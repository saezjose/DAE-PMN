## Para hacer correr el proyecto
## python -m streamlit run PMN.py

import streamlit as st

st.set_page_config(layout="wide")
st.title("PMN - Control de Clústeres y Validación Cruzada (INFO1163)")

if "mesa_12" not in st.session_state:
    st.session_state.mesa_12 = "OCUPADA"
if "mesa_05" not in st.session_state:
    st.session_state.mesa_05 = "DISPONIBLE"
if "reserva_A" not in st.session_state:
    st.session_state.reserva_A = "CONFIRMA"
if "solicitud_flash" not in st.session_state:
    st.session_state.solicitud_flash = False
if "cluster_creado" not in st.session_state:
    st.session_state.cluster_creado = False
if "alerta_garzon" not in st.session_state:
    st.session_state.alerta_garzon = False
if "costo_cortesia" not in st.session_state:
    st.session_state.costo_cortesia = 0

st.markdown("### Indicadores de Control Financiero")
if st.session_state.costo_cortesia > 0:
    st.metric(
        label="Perdidas por Cortesias Incurridas (Retrasos)", 
        value=f"${st.session_state.costo_cortesia} CLP", 
        delta=f"+${st.session_state.costo_cortesia} CLP (Colision Critica)", 
        delta_color="inverse"
    )
else:
    st.metric(label="Perdidas por Cortesias Incurridas (Retrasos)", value="$0 CLP")

st.divider()

tag_m12 = "Mesa 12 [Cluster Alfa]" if st.session_state.cluster_creado else "Mesa 12"
tag_m05 = "Mesa 05 [Cluster Alfa]" if st.session_state.cluster_creado else "Mesa 05"

col1, col2 = st.columns(2)

with col1:
    st.header("Vista Recepcionista")
    st.subheader("Mapa Visual del Salon")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state.mesa_12 == "OCUPADA":
            st.error(f"**{tag_m12}** (Cap. 6)\n\nEstado: OCUPADA")
        elif st.session_state.mesa_12 == "EN LIMPIEZA":
            st.warning(f"**{tag_m12}** (Cap. 6)\n\nEstado: EN LIMPIEZA")
        else:
            st.success(f"**{tag_m12}** (Cap. 6)\n\nEstado: DISPONIBLE")
            
    with c2:
        if st.session_state.mesa_05 == "DISPONIBLE":
            st.success(f"**{tag_m05}** (Cap. 2)\n\nEstado: DISPONIBLE")
        elif st.session_state.mesa_05 == "BLOQUEADA_C":
            st.warning(f"**{tag_m05}** (Cap. 2)\n\nEstado: RESERVADA CLUSTER")
        else:
            st.success(f"**{tag_m05}** (Cap. 2)\n\nEstado: DISPONIBLE")

    st.markdown("---")
    st.write(f"**Estado Reserva A:** `{st.session_state.reserva_A}`")
    
    if st.session_state.reserva_A == "CONFIRMA":
        if st.button("Registrar Arribo Reserva A"):
            st.session_state.reserva_A = "Check-in: Esperando Mesa"
            st.rerun()
            
    elif st.session_state.reserva_A == "Check-in: Esperando Mesa":
        st.warning("Alerta: No hay mesas de capacidad 6 disponibles.")
        if st.button("Crear Cluster Logico (Mesa 12 + Mesa 05)"):
            st.session_state.cluster_creado = True
            st.session_state.mesa_05 = "BLOQUEADA_C"
            st.session_state.alerta_garzon = True
            st.session_state.reserva_A = "Asignada a Cluster"
            st.session_state.costo_cortesia = 5000
            st.rerun()

    if st.session_state.solicitud_flash:
        st.markdown("### Autorizacion Requerida")
        if st.button("Autorizar Habilitacion Flash Mesa 12"):
            st.session_state.mesa_12 = "DISPONIBLE"
            st.session_state.mesa_05 = "DISPONIBLE"
            st.session_state.cluster_creado = False
            st.session_state.solicitud_flash = False
            st.session_state.reserva_A = "Sentada"
            st.rerun()

with col2:
    st.header("Tablet del Garzon")
    
    if st.session_state.solicitud_flash:
        st.warning("Esperando confirmacion de recepcion por limpieza flash...")
        
    if st.session_state.alerta_garzon and st.session_state.mesa_12 == "OCUPADA":
        st.info("Alerta Prioridad Alta: Liberar Mesa 12 para Cluster")
        if st.button("Registrar Salida de Comensales (Checkout)", disabled=st.session_state.solicitud_flash):
            st.session_state.mesa_12 = "EN LIMPIEZA"
            st.rerun()
            
    if st.session_state.mesa_12 == "EN LIMPIEZA":
        st.write("Accion: Higienizando espacio fisico.")
        
        tiempo_ok = st.checkbox("¿Simular +120s de limpieza?", disabled=st.session_state.solicitud_flash)
        
        if st.button("Mesa Lista", disabled=st.session_state.solicitud_flash):
            if not tiempo_ok:
                st.session_state.solicitud_flash = True
                st.rerun()
            else:
                st.session_state.mesa_12 = "DISPONIBLE"
                st.session_state.mesa_05 = "DISPONIBLE"
                st.session_state.cluster_creado = False
                st.session_state.reserva_A = "Sentada"
                st.rerun()

if st.session_state.reserva_A == "Sentada":
    st.success("Recorrido principal completado con exito. El cluster se consolido y la Reserva A fue sentada.")
    if st.sidebar.button("Resetear Simulacion"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()