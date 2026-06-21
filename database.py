import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "restaurante.db"

def obtener_conexion():
    """Abre una conexion fisica y fuerza la activacion de llaves foraneas."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    return conn

def generar_hash_sha256(password: str) -> str:
    """Limpia espacios fantasmas, codifica a bytes y genera el hash hexadecimal."""
    password_limpia = password.strip()
    return hashlib.sha256(password_limpia.encode('utf-8')).hexdigest()

def inicializar_base_de_datos():
    """Construye las tablas iniciales y asegura el poblamiento seguro."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            correo_corporativo TEXT PRIMARY KEY,
            nombre_trabajador TEXT NOT NULL,
            hash_contrasena TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('recepcionista', 'garzon'))
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mesas (
            id TEXT PRIMARY KEY,
            capacidad INTEGER NOT NULL,
            zona TEXT NOT NULL,
            estado TEXT NOT NULL
        )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                cantidad_comensales INTEGER NOT NULL,
                mesa_id TEXT NOT NULL,
                fecha_hora_inicio TEXT NOT NULL,
                fecha_hora_fin TEXT NOT NULL,
                estado TEXT NOT NULL,
                costo_cortesia INTEGER DEFAULT 0,
                FOREIGN KEY (mesa_id) REFERENCES mesas(id) ON DELETE CASCADE
        )
        """)


        cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_estados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_id TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (mesa_id) REFERENCES mesas(id) ON DELETE CASCADE
        )
        """)
        
        # --- SEMILLAS (SEEDS) ---
        hash_tomas = generar_hash_sha256("123")
        hash_garzon = generar_hash_sha256("123")
        
        cursor.execute("""
        INSERT OR IGNORE INTO usuarios (correo_corporativo, nombre_trabajador, hash_contrasena, rol)
        VALUES ('tomas@restaurante.cl', 'Tomás', ?, 'recepcionista')
        """, (hash_tomas,))
        
        cursor.execute("""
        INSERT OR IGNORE INTO usuarios (correo_corporativo, nombre_trabajador, hash_contrasena, rol)
        VALUES ('garzon@restaurante.cl', 'Garzón Salón', ?, 'garzon')
        """, (hash_garzon,))
        
        mesas_iniciales = [
            ("Mesa 12", 6, "Interior", "OCUPADA"),
            ("Mesa 05", 2, "Interior", "DISPONIBLE"),
            ("Mesa 01", 4, "Interior", "DISPONIBLE"),
            ("Mesa 02", 4, "Interior", "DISPONIBLE"),
            ("Mesa 03", 2, "Terraza", "DISPONIBLE"),
            ("Mesa 04", 2, "Terraza", "DISPONIBLE")
        ]
        cursor.executemany("""
        INSERT OR IGNORE INTO mesas (id, capacidad, zona, estado) 
        VALUES (?, ?, ?, ?)
        """, mesas_iniciales)
        
        conn.commit()
    finally:
        conn.close()

def validar_identidad(correo: str, password_ingresada: str):
    """Valida el acceso contrastando los hashes generados. Protegido contra fuga de memoria."""
    correo_limpio = correo.strip().lower()
    hash_ingresado = generar_hash_sha256(password_ingresada)
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT nombre_trabajador, rol 
            FROM usuarios 
            WHERE correo_corporativo = ? AND hash_contrasena = ?
        """, (correo_limpio, hash_ingresado))
        return cursor.fetchone()
    finally:
        # SOLUCIÓN PUNTO 1: Garantiza el cierre del archivo descriptor pase lo que pase
        conn.close()


def obtener_usuario_por_correo(correo: str):
    """Devuelve nombre y rol para un correo existente."""
    correo_limpio = correo.strip().lower()
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT nombre_trabajador, rol
            FROM usuarios
            WHERE correo_corporativo = ?
            """,
            (correo_limpio,),
        )
        return cursor.fetchone()
    finally:
        conn.close()

def obtener_registro_mesas_db():
    """Recupera el diccionario de estados desde el disco. Protegido contra fuga de memoria."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, capacidad, zona, estado FROM mesas")
        filas = cursor.fetchall()
        
        registro = {}
        for id_m, cap, zona, est in filas:
            registro[id_m] = {"capacidad": cap, "zona": zona, "estado": est}
        return registro
    finally:
        # SOLUCIÓN PUNTO 1: Evita conexiones flotantes por errores en hilos concurrentes
        conn.close()

def actualizar_estado_mesa_db(mesa_id: str, nuevo_estado: str) -> bool:
    """Modifica el estado de forma atomica. Evita redundancia y spam en auditoria."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT estado FROM mesas WHERE id = ?", (mesa_id,))
        fila = cursor.fetchone()
        
        if fila is None:
            return False
            
        estado_anterior = fila[0]
        
        # SOLUCIÓN PUNTO 2: Evita insertar basura si el estado nuevo es idéntico al actual (lag del Garzón)
        if estado_anterior == nuevo_estado:
            return True
        
        cursor.execute("UPDATE mesas SET estado = ? WHERE id = ?", (nuevo_estado, mesa_id))
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO historial_estados (mesa_id, estado_anterior, estado_nuevo, timestamp)
            VALUES (?, ?, ?, ?)
        """, (mesa_id, estado_anterior, nuevo_estado, now_str))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def registrar_retraso_cortesia_db(cliente_nombre, minutos_retraso, costo) -> tuple[bool, str]:
    """
    PASO 1 al 5: Aplica la Excepción E1 con validación transaccional estricta (BEGIN IMMEDIATE).
    Calcula el desplazamiento, valida solapamientos futuros (Regla D1) y, si hay choque,
    aplica un ROLLBACK para proteger la integridad del sistema.
    """
    import sqlite3
    from datetime import datetime, timedelta
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Asegurar defensivamente que existan las columnas del modelo de tiempo real
    for columna, tipo in [("fecha_hora_inicio", "TEXT"), ("fecha_hora_fin", "TEXT"), ("mesa_id", "TEXT"), ("costo_cortesia", "INTEGER DEFAULT 0")]:
        try:
            cursor.execute(f"ALTER TABLE reservas ADD COLUMN {columna} {tipo}")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Si la columna ya existe, SQLite la ignora de forma segura
            
    try:
        # 1. Iniciar Transacción Inmediata (Bloqueo de escrituras concurrentes)
        cursor.execute("BEGIN IMMEDIATE TRANSACTION;")
        
        # Obtener los datos actuales del intervalo comprometido
        cursor.execute("""
            SELECT id, mesa_id, fecha_hora_inicio, fecha_hora_fin 
            FROM reservas 
            WHERE cliente = ? AND estado = 'RESERVADA'
            LIMIT 1
        """, (cliente_nombre,))
        reserva = cursor.fetchone()
        
        if not reserva:
            cursor.execute("ROLLBACK;")
            return False, "No se encontró una reserva activa y confirmada para este cliente."
            
        res_id, mesa_id, inicio_str, fin_str = reserva
        
        # Validar que la reserva no tenga ya campos nulos por un error previo
        if not inicio_str or not fin_str:
            cursor.execute("ROLLBACK;")
            return False, "La reserva no contiene un intervalo de tiempo válido para desplazar."

        # 2. Calcular nuevo intervalo (Opción A: Desplazar el bloque completo)
        fmt = "%Y-%m-%d %H:%M:%S"
        inicio_dt = datetime.strptime(inicio_str, fmt)
        fin_dt = datetime.strptime(fin_str, fmt)
        
        nuevo_inicio_dt = inicio_dt + timedelta(minutes=minutos_retraso)
        nuevo_fin_dt = fin_dt + timedelta(minutes=minutos_retraso)
        
        nuevo_inicio_str = nuevo_inicio_dt.strftime(fmt)
        nuevo_fin_str = nuevo_fin_dt.strftime(fmt)
        
        # 3. Validar Solapamiento (Reutilizar Regla D1 contra OTRAS reservas de la misma mesa)
        cursor.execute("""
            SELECT cliente 
            FROM reservas 
            WHERE mesa_id = ? 
              AND id != ? 
              AND estado = 'RESERVADA'
              AND (fecha_hora_inicio < ? AND fecha_hora_fin > ?)
            LIMIT 1
        """, (mesa_id, res_id, nuevo_fin_str, nuevo_inicio_str))
        
        colision = cursor.fetchone()
        
        if colision:
            # 5. Condición de Fallo: Abortar de inmediato y proteger reservas futuras
            cursor.execute("ROLLBACK;")
            return False, f"Peligro de sobreventa: El retraso colisiona con la reserva futura de '{colision[0]}'."
            
        # 4. Condición de Éxito: Sentar el cambio y guardar la pérdida en el disco
        cursor.execute("""
            UPDATE reservas 
            SET fecha_hora_inicio = ?,
                fecha_hora_fin = ?,
                costo_cortesia = ?
            WHERE id = ?
        """, (nuevo_inicio_str, nuevo_fin_str, costo, res_id))
        
        cursor.execute("COMMIT;")
        return True, "Cortesía procesada. El bloque horario se desplazó de manera segura."
        
    except sqlite3.Error as e:
        try:
            cursor.execute("ROLLBACK;")
        except:
            pass
        return False, f"Error transaccional en SQLite: {str(e)}"
    finally:
        conn.close()


def obtener_total_cortesias_db() -> int:
    """
    Suma el costo total de cortesías monetarias registradas directamente en el disco duro.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT SUM(costo_cortesia) FROM reservas")
        resultado = cursor.fetchone()[0]
        return resultado if resultado is not None else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()

def verificar_colision_db(mesa_id: str, inicio_str: str, fin_str: str) -> bool:
    """
    Aplica el teorema del solapamiento de intervalos directamente en SQL.
    Retorna True si hay choque de horarios en la misma mesa, False si está libre.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # Regla: Nueva_Inicio < Existente_Fin Y Nueva_Fin > Existente_Inicio
        cursor.execute("""
            SELECT COUNT(*) FROM reservas
            WHERE mesa_id = ? 
              AND estado NOT IN ('CANCELADA', 'COMPLETADA')
              AND fecha_hora_inicio < ?
              AND fecha_hora_fin > ?
        """, (mesa_id, fin_str, inicio_str))
        conteo = cursor.fetchone()[0]
        return conteo > 0
    finally:
        conn.close()

def registrar_reserva_db(cliente: str, cantidad: int, mesa_id: str, inicio_str: str, fin_str: str) -> bool:
    """
    Valida la colisión horaria. Si no hay tope, inserta la reserva
    de forma persistente en disco y retorna True. Si está ocupada, aborta (False).
    """
    # 1. Ejecutar el filtro defensivo en SQL antes de meter datos
    if verificar_colision_db(mesa_id, inicio_str, fin_str):
        return False  # Bloqueado por colisión horaria
        
    # 2. Si el bloque está limpio, se guarda de verdad en el archivo .db
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reservas (cliente, cantidad_comensales, mesa_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (?, ?, ?, ?, ?, 'RESERVADA')
        """, (cliente, cantidad, mesa_id, inicio_str, fin_str))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def verificar_y_limpiar_no_shows_db(reloj_sim_actual_dt) -> list:
    """
    Busca reservas en estado 'RESERVADA' que superaron los 15 minutos de tolerancia
    respecto al reloj simulado. Las cancela y libera las mesas directamente en disco.
    Retorna una lista con los nombres de clientes penalizados para actualizar la UI.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    no_shows_detectados = []
    try:
        # Convertimos el reloj actual a string ISO para compararlo en SQLite
        reloj_str = reloj_sim_actual_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Query defensiva: ¿La hora de inicio + 15 minutos es menor o igual al reloj actual?
        cursor.execute("""
            SELECT id, cliente, mesa_id 
            FROM reservas 
            WHERE estado = 'RESERVADA' 
              AND datetime(fecha_hora_inicio, '+15 minutes') <= ?
        """, (reloj_str,))
        
        filas = cursor.fetchall()
        for res_id, cliente, mesa_id in filas:
            no_shows_detectados.append((cliente, mesa_id))
            
            # 1. Cambiar el estado de la reserva a NO_SHOW
            cursor.execute("UPDATE reservas SET estado = 'NO_SHOW' WHERE id = ?", (res_id,))
            
            # 2. Liberar la mesa físicamente en la tabla mesas
            cursor.execute("UPDATE mesas SET estado = 'DISPONIBLE' WHERE id = ?", (mesa_id,))
            
            # 3. Registrar el movimiento en el historial de auditoría
            cursor.execute("""
                INSERT INTO historial_estados (mesa_id, estado_anterior, estado_nuevo, timestamp)
                VALUES (?, 'RESERVADA', 'DISPONIBLE', ?)
            """, (mesa_id, reloj_str))
            
        conn.commit()
        return no_shows_detectados
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()