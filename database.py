# database.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overtrack.db")

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            sede           TEXT    NOT NULL,
            horario_custom INTEGER NOT NULL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS horarios_empleado (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,
            dia         TEXT    NOT NULL,
            entrada     TEXT    NOT NULL,
            salida      TEXT    NOT NULL,
            UNIQUE(empleado_id, dia)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS permisos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            fecha       TEXT    NOT NULL,
            motivo      TEXT,
            tipo        TEXT    NOT NULL,
            creado_en   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nombre, fecha, tipo)
        )
    """)
    conn.commit()
    conn.close()

# ── EMPLEADOS ──────────────────────────────────────────────

def db_get_all():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM empleados ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_get_by_nombre(nombre: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM empleados WHERE nombre = ? COLLATE NOCASE", (nombre.strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def db_get_by_id(eid: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM empleados WHERE id = ?", (eid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def db_crear(nombre: str, sede: str) -> int:
    """Devuelve el id creado o -1 si ya existe."""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO empleados (nombre, sede) VALUES (?, ?)", (nombre.strip(), sede)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return -1
    finally:
        conn.close()

def db_upsert(nombre: str, sede: str) -> int:
    """Inserta si no existe; si existe, actualiza la sede. Devuelve id."""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO empleados (nombre, sede) VALUES (?, ?)", (nombre.strip(), sede)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        row = conn.execute(
            "SELECT id FROM empleados WHERE nombre = ? COLLATE NOCASE", (nombre.strip(),)
        ).fetchone()
        conn.close()
        return row["id"] if row else -1
    finally:
        conn.close()

def db_eliminar(eid: int):
    conn = get_conn()
    conn.execute("DELETE FROM empleados WHERE id = ?", (eid,))
    conn.commit()
    conn.close()

def db_actualizar(eid: int, sede: str, horario_custom: int):
    conn = get_conn()
    conn.execute(
        "UPDATE empleados SET sede = ?, horario_custom = ? WHERE id = ?",
        (sede, horario_custom, eid)
    )
    conn.commit()
    conn.close()

# ── HORARIOS PERSONALIZADOS ────────────────────────────────

def db_get_horario(eid: int) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT dia, entrada, salida FROM horarios_empleado WHERE empleado_id = ?", (eid,)
    ).fetchall()
    conn.close()
    return {r["dia"]: {"entrada": r["entrada"], "salida": r["salida"]} for r in rows}

def db_guardar_horario(eid: int, horario: dict):
    conn = get_conn()
    conn.execute("DELETE FROM horarios_empleado WHERE empleado_id = ?", (eid,))
    for dia, horas in horario.items():
        if horas.get("entrada") and horas.get("salida"):
            conn.execute(
                "INSERT INTO horarios_empleado (empleado_id, dia, entrada, salida) VALUES (?,?,?,?)",
                (eid, dia, horas["entrada"], horas["salida"])
            )
    conn.commit()
    conn.close()

# ── RESOLVER HORARIO EFECTIVO ──────────────────────────────

def resolver_horario(nombre: str, sede: str, horarios_sedes: dict) -> dict:
    """
    Devuelve el horario {dia: {entrada, salida}} que aplica a este empleado.
    Prioridad: horario propio en BD > horario de sede.
    """
    emp = db_get_by_nombre(nombre)
    if emp and emp["horario_custom"]:
        horario = db_get_horario(emp["id"])
        if horario:
            return horario
    return horarios_sedes.get(sede, {})

# ── PERMISOS ───────────────────────────────────────────────

def db_guardar_permiso(nombre: str, fecha: str, motivo: str, tipo: str):
    """Guarda o actualiza un permiso (tardanza/salida_temprana)"""
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO permisos (nombre, fecha, motivo, tipo) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(nombre, fecha, tipo) DO UPDATE SET motivo = excluded.motivo""",
            (nombre, fecha, motivo, tipo)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def db_obtener_permisos(nombre: str, fecha: str) -> dict:
    """Obtiene permisos de un empleado en una fecha específica"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT tipo, motivo FROM permisos WHERE nombre = ? AND fecha = ?",
        (nombre, fecha)
    ).fetchall()
    conn.close()
    return {r["tipo"]: r["motivo"] for r in rows}

def db_obtener_todos_permisos(nombre: str) -> list:
    """Obtiene todos los permisos de un empleado"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT fecha, tipo, motivo FROM permisos WHERE nombre = ? ORDER BY fecha DESC",
        (nombre,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_eliminar_permiso(nombre: str, fecha: str, tipo: str):
    """Elimina un permiso específico"""
    conn = get_conn()
    conn.execute(
        "DELETE FROM permisos WHERE nombre = ? AND fecha = ? AND tipo = ?",
        (nombre, fecha, tipo)
    )
    conn.commit()
    conn.close()