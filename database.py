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
            bloque_horario TEXT NOT NULL,
            estado TEXT NOT NULL,
            costo_cortesia INTEGER DEFAULT 0
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