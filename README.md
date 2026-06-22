# PMN - Prototipo Mínimo Navegable: Gestión Relacional de Reservas con Contingencias

## Información del Proyecto
* **Asignatura:** Desarrollo de Aplicaciones Empresariales (INFO1163)
* **Institución:** Universidad Católica de Temuco (UCT), Departamento de Ingeniería Informática
* **Integrantes:** Marcelo Matamala, José Sáez
* **Profesor:** Gastón Marcelo Contreras Caro

---

## 1. Descripción General
Este Prototipo Mínimo Navegable (PMN) implementa de forma transaccional e interactiva el flujo de control, robustez de datos y gestión de contingencias operativas desarrollado para el ciclo de vida de un restaurante. A diferencia de las aproximaciones iniciales basadas únicamente en estados locales volátiles, esta arquitectura migra la inteligencia del negocio hacia un **backend relacional persistente en disco (SQLite3)**, garantizando el aislamiento de operaciones concurrentes y el cumplimiento estricto de las reglas lógicas del negocio.

El sistema aborda con éxito el escenario de estrés operativo más complejo del restaurante ("Sábado de Colisión Crítica"), controlando la interacción síncrona en tiempo real entre dos terminales de usuario corriendo de forma distribuida: la **Estación de Recepción** (para el control de asignaciones, gestión de excepciones y monitoreo financiero) y la **Estación Móvil de Salón** (tablet dedicada para el cuerpo de garzones), erradicando por completo los puntos ciegos de comunicación y la latencia física.

---

## 2. Arquitectura de Software y Modelo Físico
La aplicación se desvincula del acoplamiento blando y se estructura mediante una división de responsabilidades limpia (arquitectura multicapa):

* **`database.py` (Capa de Persistencia Relacional):** Inicializa y gobierna la base de datos física en disco (`restaurante.db`). Implementa un esquema de aislamiento transaccional duro mediante directivas explícitas (`PRAGMA foreign_keys = ON` y transacciones `BEGIN IMMEDIATE`). Controla las tablas de entidades rígidas: `usuarios`, `mesas`, `reservas` y la tabla intermedia Many-to-Many `reserva_mesas` necesaria para preservar la Primera Forma Normal (1NF).
* **`PMN.py` (Orquestador Central de Estados):** Gobierna el enrutamiento de la sesión del usuario mediante un token seguro (`AUTH_TOKEN`), maneja los privilegios basados en roles (SHA-256 criptográfico para credenciales) y centraliza el reloj simulado (`st.session_state.reloj_sim`) para acelerar de forma controlada el flujo del tiempo durante las auditorías de software.
* **`view_recepcionista.py` y `view_garzon.py` (Capa de Presentación):** Vistas dedicadas que renderizan la interfaz gráfica. Rompen de forma deliberada el aislamiento de memoria nativo de Streamlit al forzar a la interfaz de usuario (UI) a consultar datos directamente del motor SQLite mediante funciones agregadas y lecturas transaccionales directas del disco duro en cada ciclo de refresco.

---

## 3. Mapeo de Reglas de Negocio, Excepciones e Hitos
El sistema implementa de forma nativa e indexada en la base de datos las soluciones de resiliencia especificadas en la matriz de diseño:

* **Regla D1 (Filtro SQL Antipenetración - Hito 1):** Consulta indexada a nivel de motor que impide la sobreescritura de bloques horarios, impidiendo físicamente que una mesa sea reservada por dos clientes en el mismo intervalo de tiempo.
* **Regla D2 (Mecanismo No-Show Defensivo - Hito 2):** Barrido defensivo automatizado en el backend. Cada vez que el reloj avanza, el motor evalúa las reservas inactivas en disco. Si superan los 15 minutos de tolerancia, rescinde automáticamente el bloque, actualiza la auditoría y libera la mesa en la UI.
* **Excepción E1 (Sincronización Financiera - Hito 3):** Registro persistente y transaccional de costos por cortesía comercial (15,000 CLP) debido a retrasos gestionados con antelación, acoplado de forma directa a una métrica superior reactiva en la UI.
* **Excepción E2 (Extensión con Mitigación de Zona - Hito 4):** Valida la disponibilidad en disco del rango horario inmediatamente contiguo al checkout programado. Si el bloque posterior está ocupado, aborta la alteración en disco e instruye visualmente al personal en recepción a sugerir una reubicación de zona (ej: de *Interior* a *Terraza*).
* **Alerta E3 (Anticipación Comercial Visual - Hito 5):** Cálculo dinámico de diferenciales de tiempo decrecientes contra la estampa `fecha_hora_fin` guardada en disco. Al cruzar el umbral crítico, las tarjetas del plano en Streamlit alteran dinámicamente sus hojas de estilo CSS para parpadear, indicando una rotación inminente.
* **Clústeres Atómicos Transaccionales (Hito 6):** Permite la fusión lógica de múltiples mesas físicas para grupos grandes a través de la tabla intermedia Many-to-Many. Utiliza la propiedad nativa `cursor.rowcount` en Python para capturar fallas silenciosas y ejecutar un `ROLLBACK` manual si cualquiera de los recursos del grupo se encuentra comprometido de forma concurrente.
* **Validaciones Estadísticas y de Dominio (Hito 7):** Capa defensiva contra el error humano. Sanitiza textos vacíos (`.strip()`), impide nombres de mesas duplicadas cruzando la clave primaria y restringe comensales en negativo parametrizando el atributo `min_value=1` en los componentes numéricos.
* **Temporizador Autónomo de Sanitización (Hito 8):** Almacena de forma persistente la marca temporal de salida del cliente. La vista `view_garzon.py` calcula de manera decreciente el intervalo obligatorio de 3 minutos (180 segundos) de desinfección, inyectando la propiedad `disabled=True` en el botón de liberación por software para evitar omisiones humanas.

---

## 4. Estructura de la Interfaz y UX
* **Barra Lateral (Control Maestro):** Centraliza la manipulación del reloj simulado corporativo (+5 min / +15 min) y los formularios defensivos de captura de datos sanitizados.
* **Panel de Control Financiero Superior:** Métrica gerencial de alto nivel acoplada en tiempo real al disco duro que calcula el impacto financiero acumulado de las cortesías por demoras de la noche.
* **Mapa Interactivo del Salón:** Representación visual estructurada y dividida espacialmente por zonas reales (*Interior* y *Terraza*). Las tarjetas de las mesas utilizan lógica condicional y códigos de color corporativos basados en los estados transaccionales recuperados directamente desde la base de datos (Verde: Disponible, Rojo: Ocupado, Naranja/Gris: En Limpieza / Bloqueado).

---

## 5. Instrucciones de Instalación y Ejecución

### Requisitos Previos
* Python 3.9 o superior.
* Administrador de paquetes `pip`.

### Instalación de Dependencias
Instale el framework web necesario ejecutando en su terminal:
```bash
pip install streamlit

### Ejecución de la Aplicación
Navegue con su terminal hacia la carpeta donde clonó o descargó los archivos del proyecto y ejecute el comando del orquestador central:
```bash
python -m streamlit run PMN.py

La aplicación web se desplegará de forma automática en su navegador predeterminado bajo el puerto de desarrollo local: `http://localhost:8501`.

---

## 6. Guía de Trazabilidad para la Demostración del "Caso Narrado"
Para validar de forma empírica el comportamiento defensivo del software ante el profesor evaluador, ejecute paso a paso la siguiente ruta crítica durante la simulación del turno de "Sábado de Colisión Crítica":

1. **Alineación de Terminales distribuidos:** Divida su pantalla en dos ventanas de navegador independientes colocadas lado a lado. En la ventana izquierda inicie sesión con credenciales de **Recepcionista** (`view_recepcionista.py`) y en la ventana derecha con rol de **Garzón** (`view_garzon.py`). Verifique que el reloj simulado comience su marcha síncrona en la barra superior.

2. **Simulación de la Excepción E1 (Sincronización Financiera en Vivo):** En el panel de la izquierda (Recepción), localice un cliente que se encuentre retrasado y ejecute la acción de prórroga horaria por contingencia. Presione confirmar y observe cómo el panel superior de control financiero **suma de manera instantánea los 15,000 CLP** asignados a la cortesía. Esta métrica no se apoya en memoria volátil; se calcula reactivamente interrogando funciones agregadas directo en el archivo `restaurante.db`.

3. **Auditoría de la Regla D2 (Mecanismo No-Show Autónomo):** Utilice los controles de la barra lateral para avanzar el tiempo simulado en bloques de +15 minutos. En el momento en que una reserva inactiva supere su ventana límite de tolerancia sin haber registrado el check-in correspondiente, el motor de backend ejecutará un barrido relacional que rescindirá el bloque en disco duro. Observe cómo la mesa asociada **cambia de forma automática a color Verde (Disponible)** en el mapa del recepcionista sin intervención del usuario.

4. **Activación del Protocolo Sanitario Poka-Yoke (Checkout y Bloqueo Técnico):** Traslade la atención a la ventana derecha (**Tablet del Garzón**). Seleccione una mesa activa cuyo servicio haya concluido y presione el botón de *Checkout*. El sistema asentará la estampa de tiempo actual en SQLite y la mesa cambiará inmediatamente al estado `EN LIMPIEZA`. Intente forzar la disponibilidad de la mesa haciendo clic en el botón de habilitación; notará que **el botón se inyecta de color gris e inhabilitado (`disabled=True`)**, desplegando de forma dinámica la cuenta regresiva estricta de 180 segundos. Avance el tiempo simulado desde la barra lateral para agotar el contador y observe cómo solo al cumplir el tiempo de sanitización física el botón se desbloquea para regresar la mesa al estado `DISPONIBLE`.