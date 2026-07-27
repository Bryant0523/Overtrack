# procesamiento.py
import json
import os
import re
import pandas as pd
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────
# EMPLEADOS (JSON — se mantiene para compatibilidad)
# ─────────────────────────────────────────────────────────────

def es_nombre_valido(nombre):
    if not isinstance(nombre, str):
        return False
    valor = nombre.strip()
    if not valor:
        return False
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", valor):
        return False
    if re.match(r"^\d{4}-\d{2}-\d{2}$", valor):
        return False
    if re.match(r"^\d+$", valor):
        return False
    return bool(re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]", valor))


def cargar_empleados():
    ruta = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "empleados.json")
    )
    if os.path.exists(ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                empleados = json.load(f)
            if not isinstance(empleados, list):
                return []
            empleados_validos = []
            vistos = set()
            for nombre in empleados:
                if not isinstance(nombre, str):
                    continue
                nombre_limpio = nombre.strip()
                if not es_nombre_valido(nombre_limpio):
                    continue
                clave = nombre_limpio.lower()
                if clave in vistos:
                    continue
                vistos.add(clave)
                empleados_validos.append(nombre_limpio)
            if len(empleados_validos) != len(empleados):
                guardar_empleados(empleados_validos)
            return empleados_validos
        except Exception:
            pass
    return []


def guardar_empleados(empleados_list):
    ruta = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "empleados.json")
    )
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(empleados_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def agregar_empleado(nombre):
    nombre_limpio = nombre.strip() if isinstance(nombre, str) else ""
    if not es_nombre_valido(nombre_limpio):
        return cargar_empleados()

    empleados = cargar_empleados()
    if nombre_limpio not in empleados:
        empleados.append(nombre_limpio)
        guardar_empleados(empleados)
    return empleados


# ─────────────────────────────────────────────────────────────
# HORARIOS DE SEDES (desde JSON o hardcoded como fallback)
# ─────────────────────────────────────────────────────────────

def cargar_horarios():
    ruta = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "sedes.json")
    )
    if os.path.exists(ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "medellin": {
            "Lunes":     {"entrada": "08:00", "salida": "17:00"},
            "Martes":    {"entrada": "08:00", "salida": "17:00"},
            "Miércoles": {"entrada": "08:00", "salida": "17:00"},
            "Jueves":    {"entrada": "08:00", "salida": "17:00"},
            "Viernes":   {"entrada": "08:00", "salida": "17:00"},
            "Sábado":    {"entrada": "08:00", "salida": "17:00"},
        },
        "barranquilla": {
            "Lunes":     {"entrada": "08:00", "salida": "16:30"},
            "Martes":    {"entrada": "08:00", "salida": "16:30"},
            "Miércoles": {"entrada": "08:00", "salida": "17:00"},
            "Jueves":    {"entrada": "08:00", "salida": "17:00"},
            "Viernes":   {"entrada": "08:00", "salida": "16:00"},
            "Sábado":    {"entrada": "08:00", "salida": "12:00"},
        },
        "cartagena": {
            "Lunes":     {"entrada": "09:00", "salida": "17:30"},
            "Martes":    {"entrada": "09:00", "salida": "17:30"},
            "Miércoles": {"entrada": "09:00", "salida": "17:30"},
            "Jueves":    {"entrada": "09:00", "salida": "17:30"},
            "Viernes":   {"entrada": "09:00", "salida": "17:30"},
            "Sábado":    {"entrada": "09:00", "salida": "15:00"},
        },
    }

HORARIOS_SEDES = cargar_horarios()

DIAS_MAP = {
    "Monday":    "Lunes",
    "Tuesday":   "Martes",
    "Wednesday": "Miércoles",
    "Thursday":  "Jueves",
    "Friday":    "Viernes",
    "Saturday":  "Sábado",
    "Sunday":    "Domingo",
}

SEDES_SIN_ALMUERZO_SABADO = {"barranquilla"}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def formatear_hhmm(td: timedelta) -> str:
    if td is None or td <= timedelta(0):
        return "00h 00m"
    total_min = int(td.total_seconds() // 60)
    return f"{total_min // 60:02d}h {total_min % 60:02d}m"

def calcular_tardanza(entrada_dt, entrada_oficial_dt):
    diff = entrada_dt - entrada_oficial_dt
    return diff if diff > timedelta(0) else timedelta(0)

def calcular_extras(entrada_dt, salida_dt, entrada_oficial_dt, salida_oficial_dt, tardanza_td,
                    umbral_extras_minutos=30, permiso_salida_temprana=False):
    if permiso_salida_temprana and salida_dt < salida_oficial_dt:
        return timedelta(0)

    if salida_dt < salida_oficial_dt:
        extras_antes = timedelta(0)
    else:
        extras_antes = max(entrada_oficial_dt - entrada_dt, timedelta(0))

    extras_despues = max(salida_dt - salida_oficial_dt - tardanza_td, timedelta(0))
    total_extras = extras_antes + extras_despues
    if total_extras < timedelta(minutes=umbral_extras_minutos):
        return timedelta(0)
    return total_extras


def validar_calculo(entrada_dt, salida_dt, entrada_oficial_dt, salida_oficial_dt, tardanza_td,
                    tiempo_almuerzo_td, horas_trab_td, extras_td, umbral_extras_minutos=30,
                    permiso_salida_temprana=False):
    """Valida si el cálculo de horas extras y trabajadas es coherente."""
    horas_esperadas = (salida_dt - entrada_dt) - tiempo_almuerzo_td
    horas_esperadas = max(horas_esperadas, timedelta(0))

    extras_esperados = calcular_extras(
        entrada_dt, salida_dt, entrada_oficial_dt, salida_oficial_dt,
        tardanza_td, umbral_extras_minutos=umbral_extras_minutos,
        permiso_salida_temprana=permiso_salida_temprana
    )

    horas_ok = abs((horas_trab_td - horas_esperadas).total_seconds()) <= 60
    extras_ok = abs((extras_td - extras_esperados).total_seconds()) <= 60

    if permiso_salida_temprana and salida_dt < salida_oficial_dt:
        return "Revisar", "Salida temprana con permiso detectada; revisar si no corresponde a un cambio de turno o ajuste especial."

    if salida_dt < salida_oficial_dt and entrada_dt <= entrada_oficial_dt:
        return "Revisar", "Salida anticipada respecto al horario oficial; revisar permiso o ajuste especial."

    if horas_ok and extras_ok:
        return "OK", "Cálculo consistente con las marcaciones y el horario oficial."

    detalle = []
    if not horas_ok:
        detalle.append(
            f"Horas trabajadas esperado {formatear_hhmm(horas_esperadas)} pero se registró {formatear_hhmm(horas_trab_td)}"
        )
    if not extras_ok:
        detalle.append(
            f"Horas extras esperado {formatear_hhmm(extras_esperados)} pero se registró {formatear_hhmm(extras_td)}"
        )
    return "Revisar", " | ".join(detalle)


def asignar_marcaciones(horas_ordenadas: list, fecha) -> dict:
    n = len(horas_ordenadas)
    r = {"entrada": None, "salida_almuerzo": None, "regreso_almuerzo": None, "salida": None}
    if n == 0: return r
    if n == 1:
        h = horas_ordenadas[0]
        r["entrada" if h.hour < 13 else "salida"] = h
        return r
    if n == 2:
        r["entrada"] = horas_ordenadas[0]
        r["salida"]  = horas_ordenadas[-1]
        return r
    if n == 3:
        r["entrada"]         = horas_ordenadas[0]
        r["salida_almuerzo"] = horas_ordenadas[1]
        r["salida"]          = horas_ordenadas[-1]
        return r
    # n >= 4
    r["entrada"]          = horas_ordenadas[0]
    r["salida_almuerzo"]  = horas_ordenadas[1]
    r["regreso_almuerzo"] = horas_ordenadas[2]
    r["salida"]           = horas_ordenadas[-1]
    return r


# ─────────────────────────────────────────────────────────────
# PROCESAR REGISTROS
# ─────────────────────────────────────────────────────────────

def procesar_registros(df: pd.DataFrame, sede_or_horario, resolver_horario_fn=None, umbral_extras_minutos=30) -> pd.DataFrame:
    """
    Procesa marcaciones del huellero.

    Parámetros:
      df                 : DataFrame crudo del huellero
      sede_or_horario    : str (nombre de sede) o dict de horarios
      resolver_horario_fn: función opcional (nombre, sede) -> dict {dia: {entrada, salida}}
                           Si se pasa, permite horarios individuales por empleado (BD SQLite).
                           Si no, todos usan el horario de la sede.
      umbral_extras_minutos: int minutos mínimos para considerar horas extras.
    """
    df = df.copy()
    df.columns = df.columns.str.strip()

    if df.shape[1] <= 3:
        raise ValueError("El archivo no tiene suficientes columnas (se esperan al menos 4).")

    col_nombre = df.columns[1]  # columna B
    col_fecha  = df.columns[3]  # columna D
    df = df.rename(columns={col_nombre: "nombre", col_fecha: "fecha_hora"})

    df["__dt"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
    df = df.dropna(subset=["__dt"])
    df["fecha"] = df["__dt"].dt.date
    df["hora"]  = df["__dt"].dt.time

    # Horario base (sede)
    if isinstance(sede_or_horario, str):
        sede_nombre    = sede_or_horario
        horario_global = HORARIOS_SEDES.get(sede_or_horario, {})
    else:
        sede_nombre    = ""
        horario_global = sede_or_horario

    filas_result = []

    for (nombre, fecha), grupo in df.groupby(["nombre", "fecha"]):
        dia_ing = datetime.strptime(str(fecha), "%Y-%m-%d").strftime("%A")
        dia_es  = DIAS_MAP.get(dia_ing, dia_ing)

        if dia_es == "Domingo":
            continue

        # ── Resolver horario: BD > sede ──
        if resolver_horario_fn:
            horario_por_dia = resolver_horario_fn(nombre, sede_nombre)
        else:
            horario_por_dia = horario_global

        horario_dia = horario_por_dia.get(dia_es)
        if not horario_dia:
            continue

        horas_dia = sorted(grupo["hora"].dropna().tolist())
        marcas    = asignar_marcaciones(horas_dia, fecha)

        entrada_t          = marcas["entrada"]
        salida_almuerzo_t  = marcas["salida_almuerzo"]
        regreso_almuerzo_t = marcas["regreso_almuerzo"]
        salida_t           = marcas["salida"]

        base = {
            "Nombre": nombre,
            "Fecha":  fecha.strftime("%d/%m/%Y"),
            "Día":    dia_es,
        }

        # ── Sin ninguna marcación ──
        if entrada_t is None and salida_t is None:
            filas_result.append({**base,
                "Entrada": "--:--", "Sal. Almuerzo": "--:--",
                "Reg. Almuerzo": "--:--", "Salida": "--:--",
                "T. Almuerzo": "--:--", "Horas trabajadas": "no marcó",
                "Tardanza": "no marcó", "Horas extras": "no marcó"})
            continue

        # ── Solo entrada ──
        if entrada_t is not None and salida_t is None:
            filas_result.append({**base,
                "Entrada": entrada_t.strftime("%H:%M"),
                "Sal. Almuerzo": salida_almuerzo_t.strftime("%H:%M") if salida_almuerzo_t else "--:--",
                "Reg. Almuerzo": regreso_almuerzo_t.strftime("%H:%M") if regreso_almuerzo_t else "--:--",
                "Salida": "--:--", "T. Almuerzo": "--:--",
                "Horas trabajadas": "no marcó salida",
                "Tardanza": "no marcó salida", "Horas extras": "no marcó salida"})
            continue

        # ── Solo salida ──
        if entrada_t is None and salida_t is not None:
            filas_result.append({**base,
                "Entrada": "--:--", "Sal. Almuerzo": "--:--",
                "Reg. Almuerzo": "--:--", "Salida": salida_t.strftime("%H:%M"),
                "T. Almuerzo": "--:--",
                "Horas trabajadas": "no marcó entrada",
                "Tardanza": "no marcó entrada", "Horas extras": "no marcó entrada"})
            continue

        # ── Caso normal ──
        entrada_dt      = datetime.combine(fecha, entrada_t)
        salida_dt       = datetime.combine(fecha, salida_t)
        entrada_oficial = datetime.combine(fecha, datetime.strptime(horario_dia["entrada"], "%H:%M").time())
        salida_oficial  = datetime.combine(fecha, datetime.strptime(horario_dia["salida"],  "%H:%M").time())

        try:
            from database import db_obtener_permisos
            permisos_dia = db_obtener_permisos(nombre, fecha.strftime("%d/%m/%Y")) or {}
        except Exception:
            permisos_dia = {}

        permiso_salida_temprana = bool(permisos_dia.get("salida_temprana"))

        tardanza = calcular_tardanza(entrada_dt, entrada_oficial)

        # Tiempo de almuerzo
        tiempo_almuerzo = timedelta(0)
        almuerzo_str    = "--:--"

        if salida_almuerzo_t and regreso_almuerzo_t:
            t = datetime.combine(fecha, regreso_almuerzo_t) - datetime.combine(fecha, salida_almuerzo_t)
            tiempo_almuerzo = max(t, timedelta(0))
            almuerzo_str    = formatear_hhmm(tiempo_almuerzo)
        else:
            # Usar flag descontar_almuerzo del JSON si existe, sino lógica por sede/día
            bandera = horario_dia.get("descontar_almuerzo", None)
            if bandera is not None:
                descuenta = bool(bandera)
            else:
                descuenta = not (dia_es == "Sábado" and sede_nombre in SEDES_SIN_ALMUERZO_SABADO)

            if descuenta:
                tiempo_almuerzo = timedelta(hours=1)
                almuerzo_str    = "01h 00m (est.)"

        horas_trab = max((salida_dt - entrada_dt) - tiempo_almuerzo, timedelta(0))
        extras     = calcular_extras(
            entrada_dt, salida_dt,
            entrada_oficial, salida_oficial,
            tardanza, umbral_extras_minutos
        )

        estado_validacion, detalle_validacion = validar_calculo(
            entrada_dt=entrada_dt,
            salida_dt=salida_dt,
            entrada_oficial_dt=entrada_oficial,
            salida_oficial_dt=salida_oficial,
            tardanza_td=tardanza,
            tiempo_almuerzo_td=tiempo_almuerzo,
            horas_trab_td=horas_trab,
            extras_td=extras,
            umbral_extras_minutos=umbral_extras_minutos,
            permiso_salida_temprana=permiso_salida_temprana,
        )

        filas_result.append({**base,
            "Entrada":          entrada_t.strftime("%H:%M"),
            "Sal. Almuerzo":    salida_almuerzo_t.strftime("%H:%M") if salida_almuerzo_t else "--:--",
            "Reg. Almuerzo":    regreso_almuerzo_t.strftime("%H:%M") if regreso_almuerzo_t else "--:--",
            "Salida":           salida_t.strftime("%H:%M"),
            "T. Almuerzo":      almuerzo_str,
            "Horas trabajadas": formatear_hhmm(horas_trab),
            "Tardanza":         formatear_hhmm(tardanza),
            "Horas extras":     formatear_hhmm(extras),
            "Validación":      estado_validacion,
            "Detalle validación": detalle_validacion,
        })

    df_res = pd.DataFrame(filas_result)
    if df_res.empty:
        return df_res

    def to_min(x):
        if isinstance(x, str) and "h" in x:
            p = x.replace("h", "").replace("m", "").split()
            try: return int(p[0]) * 60 + int(p[1])
            except: return 0
        return 0

    df_res["_min"] = df_res["Horas extras"].apply(to_min)
    filas_finales  = []

    for nombre, grp in df_res.groupby("Nombre", sort=False):
        filas_finales.extend(grp.drop(columns=["_min"]).to_dict("records"))
        total_min = grp["_min"].sum()
        filas_finales.append({
            "Nombre":           f"TOTAL HORAS EXTRAS ({nombre})",
            "Fecha": "", "Día": "", "Entrada": "",
            "Sal. Almuerzo": "", "Reg. Almuerzo": "", "Salida": "",
            "T. Almuerzo": "", "Horas trabajadas": "", "Tardanza": "",
            "Horas extras": f"{total_min // 60:02d}h {total_min % 60:02d}m",
        })

    return pd.DataFrame(filas_finales)