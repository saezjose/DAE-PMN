# PMN - Prototipo Minimo Navegable: Gestion de Reservas con Contingencias

## Informacion del Proyecto
* **Asignatura:** Desarrollo de Aplicaciones Empresariales (INFO1163)
* **Institucion:** Universidad Catolica de Temuco (UCT), Departamento de Ingenieria Informatica
* **Integrantes:** Marcelo Matamala, Jose Saez
* **Profesor:** Gaston Marcelo Contreras Caro

---

## 1. Descripcion General
Este Prototipo Minimo Navegable (PMN) implementa de forma interactiva el flujo de control y gestion de contingencias desarrollado en el informe del Avance 3. La aplicacion simula el comportamiento logico de un sistema de reservas de restaurant en tiempo real, omitiendo la persistencia en bases de datos relacionales mediante el uso estrategico de gestion de estados en memoria de Streamlit (session_state).

El sistema aborda implicitamente el peor escenario operativo ("Sabado de Colision Critica"), donde el local opera al 95% de su capacidad. Centraliza la interaccion sincronizada entre dos actores principales: el Recepcionista (consola central de asignacion) y el Garzon (dispositivo tablet movil), eliminando la latencia fisica de comunicacion.

---

## 2. Arquitectura del Estado Simulado (Maquina de Estados)
El motor de la aplicacion funciona como una maquina de estados finitos que gobierna de forma estricta los recursos del salon (Mesas) y el progreso de los clientes (Reservas). Los datos persisten de forma volatil durante la sesion mediante las siguientes variables clave:

* `st.session_state.mesa_12` / `st.session_state.mesa_05`: Controlan la transicion estricta de estados de los activos tangibles (DISPONIBLE, OCUPADA, EN LIMPIEZA, BLOQUEADA_C).
* `st.session_state.reserva_A`: Realiza el seguimiento secuencial de la traza principal (CONFIRMA, RESERVADA, Check-in: Esperando Mesa, Asignada a Cluster, SENTADA, COMPLETADA).
* `st.session_state.reloj_sim`: Objeto de tiempo que permite adelantar el cronograma operativo de forma controlada (+5 min / +15 min) para disparar politicas de negocio asincronicas.
* `st.session_state.costo_cortesia`: Variable contable que acumula el impacto financiero negativo incurrido debido a ineficiencias o sobre-estadia.

---

## 3. Mapeo de Reglas de Negocio y Excepciones
El sistema implementa de manera exacta las soluciones de resiliencia especificadas en la matriz de excepciones del diseño teorico:

### Excepcion 1 (E1) - Protocolo de Espera y Calculo de Proyeccion
Cuando la Decision 1 (D1) valida que no hay mesas disponibles que cumplan con la capacidad requerida de forma inmediata, la reserva es derivada a la lista de espera activa (`lista_espera_e1`). El sistema calcula algoritmicamente una proyeccion en segundos basada en el tiempo restante de higienizacion del salon.

### Excepcion 2 (E2) - Regla Automatica de No-Show
El sistema compara de forma asincrona la hora del reloj simulado con el limite de tolerancia parametrizado (15 minutos tras el inicio estimado del bloque). Si el comensal no registra check-in dentro de la ventana, el estado de la reserva muta a `NO_SHOW`, levantando restricciones y liberando preventivamente el recurso para proteger la rentabilidad por metro cuadrado.

### Excepcion 3 (E3) - Anticipacion Comercial y Mitigacion de Colision Critica
* **Aviso sutil:** 15 minutos antes del vencimiento teorico del bloque horario de una mesa ocupada, la tablet del Garzon despliega una alerta preventiva obligatoria para incentivar la ultima orden.
* **Protocolo de crisis:** Si el cliente actual exige una extension de tiempo comercial y la simulacion activa una colision futura en esa mesa, el sistema bloquea el cambio automatico y fuerza al usuario a ejecutar los tres pasos secuenciales de mitigacion fisica declarados en el modelo:
  1. Entregar la cuenta de forma presencial.
  2. Notificar al Administrador de Salon.
  3. Registrar la reubicacion fisica (barra o terraza) del cliente antiguo para liberar el recurso logico.

### Transaccionalidad ACID y Elasticidad de Clusteres
La creacion de un cluster unifica mesas fisicas separadas (Mesa 12 de capacidad 6 y Mesa 05 de capacidad 2) bajo una unica identidad logica temporal denominada `[Cluster Alfa]`. El acoplamiento se procesa de forma atomica: si se produce una falla logica, el sistema aplica un Rollback de memoria inmediato, devolviendo las mesas a sus valores iniciales.

---

## 4. Estructura de la Interfaz y UX
La aplicacion utiliza un diseño de pestañas unificadas (`st.tabs`) sincronizadas por un mismo nucleo de memoria central. Esto elude el punto ciego de aislamiento de Streamlit entre diferentes pestañas del navegador.

* **Barra Lateral (Control Maestro):** Agrupa el control del reloj simulado, la adicion dinamica de nuevas mesas con definicion de capacidad/zona y los cargadores manuales de contingencias secuenciales.
* **Cabecera de Control Financiero:** Despliega una metrica de alto nivel (`st.metric`) con un delta inverso de color rojo. Visibiliza el impacto economico directo en tiempo real de las decisiones operativas, actuando como un panel gerencial.
* **Pestaña Recepcionista:** Contiene el Mapa Visual del salon segmentado espacialmente (Interior y Terraza). Utiliza codigos de colores nativos e inmutables (Verde: Disponible, Rojo: Ocupada, Amarillo/Naranja: Limpieza o Bloqueo) para facilitar el escaneo visual directo del supervisor.
* **Pestaña Garzon:** Replica la interfaz movil de la tablet en salon. Permite seleccionar de forma interactiva que mesa procesar, ejecutar el checkout y controlar el bloqueo pasivo de seguridad (180 segundos).

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

* ** Estado Inicial: ** Verifique que el panel financiero inicia en $0 CLP, la Mesa 12 figura como OCUPADA (Interior) y la Mesa 05 como DISPONIBLE.
* ** Registro de Arribo: ** En la pestaña Recepcionista, presione el boton Registrar Reserva A (asignar bloque). Al no detectar colision inicial directa, la reserva pasa a estado RESERVADA.
* ** Provocar la Colision: ** En la barra lateral, avance el tiempo presionando los botones de adicion horaria hasta superar el tiempo estimado. Al presionar Marcar llegada de Reserva A (Check-in), el sistema detectara que la Mesa 12 sigue ocupada por sobre-estadia. La reserva cambiara automaticamente al estado Check-in: Esperando Mesa.

* ** Activacion de Contingencia: ** Presione el boton Crear Cluster Logico (Mesa 12 + Mesa 05). Verifique que:
* **  **
* **  **
* **  **
* **  **
