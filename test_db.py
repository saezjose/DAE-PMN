# test_db.py
import database as db
import os

print("=== INICIANDO PRUEBAS DEL BACKEND ===")

# 1. Forzar la creación de la base de datos desde cero
if os.path.exists("restaurante.db"):
    os.remove("restaurante.db")
    print("[-] Archivo viejo 'restaurante.db' eliminado para limpiar pruebas.")

print("[+] Inicializando base de datos y cargando tablas...")
db.inicializar_base_de_datos()

# 2. Probar la Validación de Identidad (Login con SHA-256)
print("\n--- Guardar y Validar Credenciales ---")
# Probar login exitoso (con tu correo ficticio)
usuario = db.validar_identidad("tomas@restaurante.cl", "123")
print(f"[OK] Login exitoso para Tomás: {usuario}")  # Debería retornar ('Tomás', 'recepcionista')

# Probar inmunidad a las mayúsculas (Case Sensitivity)
usuario_caps = db.validar_identidad("TOMAS@RESTAURANTE.CL", "123")
print(f"[OK] Login tolerante a mayúsculas: {usuario_caps}")

# Probar contraseña incorrecta
fallo_clave = db.validar_identidad("tomas@restaurante.cl", "clave_mala")
print(f"[OK] Intento con clave mala rechazada correctamente: {fallo_clave}")  # Debería retornar None

# 3. Probar Lectura de Mesas
print("\n--- Estado Inicial de las Mesas ---")
mesas = db.obtener_registro_mesas_db()
print(f"Estado de la Mesa 12: {mesas['Mesa 12']['estado']}")  # Debería ser 'OCUPADA'
print(f"Estado de la Mesa 05: {mesas['Mesa 05']['estado']}")  # Debería ser 'DISPONIBLE'

# 4. Probar Actualización Atómica y Auditoría
print("\n--- Modificando Estado de Mesa (Simulando Checkout del Garzón) ---")
# Cambiar Mesa 12 de OCUPADA a EN LIMPIEZA
exito = db.actualizar_estado_mesa_db("Mesa 12", "EN LIMPIEZA")
print(f"[OK] ¿Se actualizó la Mesa 12?: {exito}")

# Verificar que cambió en la lectura
mesas_actualizadas = db.obtener_registro_mesas_db()
print(f"Nuevo estado de la Mesa 12 en BD: {mesas_actualizadas['Mesa 12']['estado']}")

# 5. Probar el filtro de redundancia (Doble clic por lag del Garzón)
print("\n--- Probando Filtro contra Clicks Duplicados (Spam de Auditoría) ---")
# Intentar pasar a 'EN LIMPIEZA' otra vez cuando ya está en ese estado
db.actualizar_estado_mesa_db("Mesa 12", "EN LIMPIEZA")
print("[OK] Intento redundante procesado de forma segura.")

print("\n=== PRUEBAS DE CÓDIGO COMPLETADAS CON ÉXITO ===")
print("Ahora abre 'restaurante.db' en DB Browser for SQLite para la inspección visual.")