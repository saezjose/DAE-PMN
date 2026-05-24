# PMN - Prototipo Minimo Navegable: Gestion de Reservas con Contingencias

## Informacion del Proyecto
* **Asignatura:** Desarrollo de Aplicaciones Empresariales (INFO1163)
* **Institucion:** Universidad Catolica de Temuco (UCT), Departamento de Ingenieria Informatica
* **Integrantes:** Marcelo Matamala, Jose Saez
* **Profesor:** Gaston Marcelo Contreras Caro

---

## 1. Descripcion General
Este Prototipo Minimo Navegable (PMN) implementa de forma interactiva el flujo de control y gestion de contingencias desarrollado en el informe del Avance 3. La aplicacion simula el comportamiento logico de un sistema de reservas de restaurant en tiempo real, omitiendo la persistencia en bases de datos relacionales mediante el uso estrategico de gestion de estados en memoria de Streamlit (session_state).

El sistema aborda el escenario operativo mas complejo del negocio ("Sabado de Colision Critica"), donde el local opera al 95% de su capacidad. Centraliza la interaccion sincronizada entre dos actores principales de forma asincrona: el Recepcionista (consola central de asignacion con ingreso manual dinamico) y el Garzon (dispositivo tablet movil), eliminando la latencia fisica de comunicacion.

---

## 2. Arquitectura del Estado Simulado (Maquina de Estados)
El motor de la aplicacion funciona como una maquina de estados finitos que gobierna de forma estricta los recursos del salon (Mesas) y el progreso de los clientes (Reservas). Los datos persisten de forma volatil durante la sesion mediante las siguientes variables clave:

* `st.session_state.mesa_12` / `st.session_state.mesa_05`: Controlan la transicion estricta de estados de los activos tangibles (DISPONIBLE, OCUPADA, EN LIMPIEZA, BLOQUEADA_C).
* `st.session_state.reserva_A`: Realiza el seguimiento secuencial de la traza principal (CONFIRMA, RESERVADA, Check-in: Esperando Mesa, Asignada a Cluster, SENTADA, COMPLETADA).
* `st.session_state.reloj_sim`: Objeto de tiempo que permite adelantar el cronograma operativo de forma controlada (+5 min / +15 min) para disparar politicas de negocio asincronicas.
* `st.session_state.duracion_bloque_min`: Atributo temporal de la reserva que muta dinamicamente según la estimacion ingresada por el recepcionista en el front-end.
* `st.session_state.costo_cortesia`: Variable contable que acumula el impacto financiero negativo incurrido debido a ineficiencias, retrasos o sobre-estadia.

---

## 3. Mapeo de Reglas de Negocio y Excepciones
El sistema implementa de manera exacta las soluciones de resiliencia especificadas en la matriz de excepciones del diseño teorico:

### Excepcion 1 (E1) - Protocolo de Espera, Elasticidad de Zonas y Proyeccion
Cuando la Decision 1 (D1) valida que no hay mesas disponibles que cumplan con la capacidad requerida de forma inmediata, la reserva es derivada a la lista de espera activa. El sistema calcula algoritmicamente una proyeccion en segundos basada en el tiempo restante de higienizacion. Si el cliente selecciona preferencia de zona **"Cualquiera"**, el algoritmo levanta la restriccion espacial y evalua la disponibilidad tanto en Interior como en Terraza para acelerar la asignacion.

### Excepcion 2 (E2) - Regla Automatica de No-Show
El sistema compara la hora del reloj simulado con el limite de tolerancia parametrizado (15 minutos tras el inicio estimado del bloque). Si el comensal no registra check-in dentro de la ventana, el estado de la reserva muta a `NO_SHOW`, liberando preventivamente el recurso para proteger la rentabilidad por metro cuadrado.

### Excepcion 3 (E3) - Anticipacion Comercial con Bloque Dinamico y Mitigacion de Crisis
* **Aviso parametrizado:** Exactamente 15 minutos antes de que expire el tiempo estimado personalizado ingresado por el recepcionista para una mesa ocupada, la tablet del Garzon despliega una alerta preventiva obligatoria para incentivar la ultima orden (postre/cuenta).
* **Protocolo de crisis:** Si el cliente actual exige una extension de tiempo comercial y la simulacion activa una colision futura en esa mesa, el sistema bloquea el cambio automatico y fuerza al usuario a ejecutar los tres pasos secuenciales de mitigacion fisica declarados en el modelo (Entregar cuenta, Notificar Administrador, Registrar reubicacion).

---

## 4. Estructura de la Interfaz y UX
La aplicacion utiliza un diseño de pestañas unificadas (`st.tabs`) sincronizadas por un mismo nucleo de memoria central, eludiendo el punto ciego de aislamiento de Streamlit entre diferentes pestañas del navegador.

* **Barra Lateral (Control Maestro):** Agrupa el control del reloj simulado y un formulario de **Ingreso Manual (Walk-in / Reserva)** que permite definir de forma dinamica la cantidad de personas, preferencia de zona (con opcion flexible Cualquiera) y el tiempo estimado de estadia.
* **Cabecera de Control Financiero:** Despliega una metrica de alto nivel (`st.metric`) con un delta inverso de color rojo. Visibiliza el impacto economico directo en tiempo real de las decisiones operativas, actuando como un panel gerencial.
* **Pestaña Recepcionista:** Contiene el Mapa Visual del salon segmentado espacialmente (Interior y Terraza). Utiliza codigos de colores nativos (Verde: Disponible, Rojo: Ocupada, Amarillo/Naranja: Limpieza o Bloqueo) para facilitar el escaneo visual directo del supervisor.
* **Pestaña Garzon:** Replica la interfaz movil de la tablet en salon. Permite seleccionar de forma interactiva que mesa procesar, monitorear el tiempo transcurrido, atender la alerta E3 y controlar el bloqueo pasivo de desinfeccion (180 segundos).

---

## 5. Instrucciones de Instalacion y Ejecucion

### Requisitos Previos
* Python 3.9 o superior.
* Administrador de paquetes pip instalado.

### Instalacion de Dependencias
Instale el framework Streamlit ejecutando el siguiente comando en la terminal de su sistema operativo:
```bash
pip install streamlit
```


### Ejecucion de la Aplicacion

Descargue el archivo de codigo fuente PMN.py en su directorio local, navegue hacia la ruta correspondiente mediante la terminal y ejecute el servidor de desarrollo:
```bash
python -m streamlit run PMN.py
```
La interfaz se desplegara de forma automatica en su navegador web predeterminado en la direccion local http://localhost:8501.

## 6. Guia de Trazabilidad del Recorrido Principal 


Para demostrar el correcto funcionamiento de las nuevas reglas dinámicas de tiempo y zona al evaluador durante la defensa presencial, siga esta secuencia exacta:

* **Ingreso Personalizado (Caso Corto):** En el panel de la barra lateral, configure un ingreso manual para 4 personas, zona Cualquiera y baje el tiempo estimado a 30 minutos. Presione Registrar Ingreso al Sistema.

* **Asignacion e Inicio de Bloque:** Presione Cargar siguiente reserva en la barra lateral. Vaya a la pestaña Recepcionista y haga clic en Registrar Reserva B (asignar bloque). Note como el sistema remueve la restriccion de zona por elegir "Cualquiera" y configura dinamicamente el bloque central en 30 minutos.
  
* **Activacion de Consumo:** Haga clic en Marcar llegada de Reserva B (Check-in). La mesa seleccionada pasara al estado OCUPADA y comenzara el cronometro de estadia indexado.
  
* **Verificacion de Alerta E3 Automatica:** Dirijase a la pestaña Garzon. Avance el reloj de la barra lateral presionando los botones de tiempo simulado (ej. presione +15 min dos veces). En el momento exacto en que el indicador "Tiempo restante bloque" marque 15 min, la interfaz redibujara la pantalla haciendo saltar el cuadro amarillo obligatorio: "E3 - Alerta preventiva: ofrecer ultimo trago/postre". Esto demuestra la eliminacion de latencia entre el front-end y las reglas de negocio temporales.
  
* **Checkout y Bloqueo de Seguridad (Poka-Yoke):** Presione Registrar salida de comensales (Checkout). La mesa mutara a EN LIMPIEZA levantando un bloqueo real de 180 segundos. Intente presionar Mesa lista de inmediato; vera que el sistema bloquea visualmente el boton grisaceo. Avance el tiempo simulado en el sidebar para simular la higienizacion fisica completa y proceda a habilitar la mesa para dejarla nuevamente DISPONIBLE.

