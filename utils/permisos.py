from datetime import date


# 🔴 Luego esto irá a base de datos
PERMISOS = []

# utils/permisos.py
def agregar_permiso(permisos, nombre, fecha, tipo):
    """
    tipo: 'tardanza' o 'salida'
    """
    permisos.append({
        "nombre": nombre,
        "fecha": str(fecha),
        "tipo": tipo
    })



def obtener_permiso(nombre, fecha, tipo):
    """
    Devuelve minutos de permiso si existe, si no 0
    """
    for p in PERMISOS:
        if (
            p['nombre'].lower() == nombre.lower()
            and p['fecha'] == fecha
            and p['tipo'] == tipo
        ):
            return p['minutos']
    return 0