# procesamiento.py
import json
import os
import pandas as pd
from datetime import datetime, timedelta

# -------------------------
# HORARIOS (por sede y por día)
# -------------------------

def cargar_empleados():
    """Carga la lista de empleados desde config/empleados.json"""
    ruta_config = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "empleados.json")
    )
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, encoding="utf-8") as archivo:
                return json.load(archivo)
        except Exception:
            pass
    return []


def guardar_empleados(empleados_list):
    """Guarda la lista de empleados en config/empleados.json"""
    ruta_config = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "empleados.json")
    )
    try:
        with open(ruta_config, "w", encoding="utf-8") as archivo:
            json.dump(empleados_list, archivo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def agregar_empleado(nombre):
    """Agrega un empleado a la lista si no existe"""
    empleados = cargar_empleados()
    if nombre not in empleados:
        empleados.append(nombre)
        guardar_empleados(empleados)
    return empleados


def cargar_horarios():
    ruta_config = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "sedes.json")
    )
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, encoding="utf-8") as archivo:
                return json.load(archivo)
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
            "Lunes":     {"entrada": "08:00", "salida": "17:00"},
            "Martes":    {"entrada": "08:00", "salida": "17:00"},
            "Miércoles": {"entrada": "08:00", "salida": "17:00"},
            "Jueves":    {"entrada": "08:00", "salida": "17:00"},
            "Viernes":   {"entrada": "08:00", "salida": "16:00"},
            "Sábado":    {"entrada": "09:00", "salida": "14:00"},
        },
        "cartagena": {
            "Lunes":     {"entrada": "09:00", "salida": "17:30"},
            "Martes":    {"entrada": "09:00", "salida": "17:30"},
            "Miércoles": {"entrada": "09:00", "salida": "17:30"},
            "Jueves":    {"entrada": "09:00", "salida": "17:30"},
            "Viernes":   {"entrada": "09:00", "salida": "17:30"},
            "Sábado":    {"entrada": "09:00", "salida": "15:00"},
        }
    }

HORARIOS_SEDES = cargar_horarios()

# -------------------------
# MAPA DÍAS (EN -> ES)
# -------------------------
DIAS_MAP = {
    "Monday":    "Lunes",
    "Tuesday":   "Martes",
    "Wednesday": "Miércoles",
    "Thursday":  "Jueves",
    "Friday":    "Viernes",
    "Saturday":  "Sábado",
    "Sunday":    "Domingo",
}


# -------------------------
# Helpers
# -------------------------

def formatear_hhmm(td: timedelta) -> str:
    """Convierte timedelta a 'HHh MMm'. Retorna '00h 00m' si es 0 o negativo."""
    if td is None or td <= timedelta(0):
        return "00h 00m"
    total_min = int(td.total_seconds() // 60)
    h = total_min // 60
    m = total_min % 60
    return f"{h:02d}h {m:02d}m"


def calcular_tardanza(entrada_dt: datetime, entrada_oficial_dt: datetime) -> timedelta:
    """Tardanza = max(0, entrada_real - entrada_oficial)."""
    diff = entrada_dt - entrada_oficial_dt
    return diff if diff > timedelta(0) else timedelta(0)


def calcular_extras(salida_dt: datetime, salida_oficial_dt: datetime,
                    tardanza_td: timedelta) -> timedelta:
    """
    Extras = max(0, salida_real - salida_oficial - tardanza).
    Umbral mínimo: 50 minutos. Si no llega a 50 min → 0.
    """
    neto = salida_dt - salida_oficial_dt - tardanza_td
    if neto <= timedelta(0):
        return timedelta(0)
    if neto < timedelta(minutes=50):
        return timedelta(0)
    return neto


def asignar_marcaciones(horas_ordenadas: list, fecha) -> dict:
    """
    Recibe una lista de objetos time ordenados cronológicamente.
    Asigna cada marcación según su posición:
      1ª → entrada
      2ª → salida_almuerzo
      3ª → regreso_almuerzo
      4ª → salida
    Si hay menos de 4, intenta detectar cuáles faltan.
    Devuelve un dict con claves: entrada, salida_almuerzo, regreso_almuerzo, salida
    (valor None si no existe esa marcación)
    """
    n = len(horas_ordenadas)

    resultado = {
        "entrada":          None,
        "salida_almuerzo":  None,
        "regreso_almuerzo": None,
        "salida":           None,
    }

    if n == 0:
        return resultado

    if n == 1:
        # No se puede saber mucho; se asigna como entrada si es AM, salida si es PM
        h = horas_ordenadas[0]
        if h.hour < 13:
            resultado["entrada"] = h
        else:
            resultado["salida"] = h
        return resultado

    if n == 2:
        # Caso más común si no marcaron almuerzo: entrada y salida
        resultado["entrada"] = horas_ordenadas[0]
        resultado["salida"]  = horas_ordenadas[-1]
        return resultado

    if n == 3:
        # Falta una marcación de almuerzo; asignamos las 2 extremas como entrada/salida
        # y el par del medio lo asignamos al que tenga sentido
        resultado["entrada"] = horas_ordenadas[0]
        resultado["salida"]  = horas_ordenadas[-1]
        # El par del medio: si hay dos seguidas, la primera es salida almuerzo
        resultado["salida_almuerzo"]  = horas_ordenadas[1]
        resultado["regreso_almuerzo"] = None   # falta el regreso
        return resultado

    if n >= 4:
        # Caso completo (o con marcaciones de más → tomamos 1ª y última como en/salida,
        # 2ª y 3ª como almuerzo)
        resultado["entrada"]          = horas_ordenadas[0]
        resultado["salida_almuerzo"]  = horas_ordenadas[1]
        resultado["regreso_almuerzo"] = horas_ordenadas[2]
        resultado["salida"]           = horas_ordenadas[-1]
        return resultado

    return resultado


# -------------------------
# PROCESAR REGISTROS (función pública)
# -------------------------
def procesar_registros(df: pd.DataFrame, sede_or_horario) -> pd.DataFrame:
    """
    Procesa marcaciones del huellero y genera reporte con:
    Nombre, Fecha, Día, Entrada, Sal. Almuerzo, Reg. Almuerzo,
    Salida, T. Almuerzo, Horas trabajadas, Tardanza, Horas extras
    """

    df = df.copy()
    df.columns = df.columns.str.strip()

    # ── Detectar columnas por índice fijo (col B = nombre, col D = fecha/hora) ──
    if df.shape[1] <= 3:
        raise ValueError("El archivo no tiene suficientes columnas (se esperan al menos 4).")

    col_nombre = df.columns[1]   # índice B
    col_fecha  = df.columns[3]   # índice D

    df = df.rename(columns={col_nombre: "nombre", col_fecha: "fecha_hora"})

    # ── Parsear fechas ──
    df["__fecha_dt"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
    df = df.dropna(subset=["__fecha_dt"])
    df["fecha"] = df["__fecha_dt"].dt.date
    df["hora"]  = df["__fecha_dt"].dt.time

    # ── Horario de la sede ──
    if isinstance(sede_or_horario, str):
        horario_por_dia = HORARIOS_SEDES[sede_or_horario]
    else:
        horario_por_dia = sede_or_horario

    # ── Sábado: por defecto algunas sedes no descuentan almuerzo (compatibilidad)
    # Nota: el comportamiento preferible es leer la clave por día `descontar_almuerzo`
    # desde la configuración de la sede (config/sedes.json). Si no existe, se
    # mantiene la excepción histórica para Barranquilla sábado.
    SEDES_SIN_ALMUERZO_SABADO = {"barranquilla"}

    filas_result = []

    # ── Iterar por persona + fecha ──
    for (nombre, fecha), grupo in df.groupby(["nombre", "fecha"]):

        dia_ing = datetime.strptime(str(fecha), "%Y-%m-%d").strftime("%A")
        dia_es  = DIAS_MAP.get(dia_ing, dia_ing)

        if dia_es == "Domingo":
            continue

        horario_dia = horario_por_dia.get(dia_es)
        if not horario_dia:
            continue

        # Ordenar todas las marcaciones del día
        horas_dia = sorted(grupo["hora"].dropna().tolist())
        marcas    = asignar_marcaciones(horas_dia, fecha)

        entrada_t          = marcas["entrada"]
        salida_almuerzo_t  = marcas["salida_almuerzo"]
        regreso_almuerzo_t = marcas["regreso_almuerzo"]
        salida_t           = marcas["salida"]

        # ── Sin ninguna marcación ──
        if entrada_t is None and salida_t is None:
            filas_result.append({
                "Nombre":           nombre,
                "Fecha":            fecha.strftime("%d/%m/%Y"),
                "Día":              dia_es,
                "Entrada":          "--:--",
                "Sal. Almuerzo":    "--:--",
                "Reg. Almuerzo":    "--:--",
                "Salida":           "--:--",
                "T. Almuerzo":      "--:--",
                "Horas trabajadas": "no marcó",
                "Tardanza":         "no marcó",
                "Horas extras":     "no marcó",
            })
            continue

        # ── Solo entrada, sin salida ──
        if entrada_t is not None and salida_t is None:
            filas_result.append({
                "Nombre":           nombre,
                "Fecha":            fecha.strftime("%d/%m/%Y"),
                "Día":              dia_es,
                "Entrada":          entrada_t.strftime("%H:%M"),
                "Sal. Almuerzo":    salida_almuerzo_t.strftime("%H:%M") if salida_almuerzo_t else "--:--",
                "Reg. Almuerzo":    regreso_almuerzo_t.strftime("%H:%M") if regreso_almuerzo_t else "--:--",
                "Salida":           "--:--",
                "T. Almuerzo":      "--:--",
                "Horas trabajadas": "no marcó salida",
                "Tardanza":         "no marcó salida",
                "Horas extras":     "no marcó salida",
            })
            continue

        # ── Solo salida, sin entrada ──
        if entrada_t is None and salida_t is not None:
            filas_result.append({
                "Nombre":           nombre,
                "Fecha":            fecha.strftime("%d/%m/%Y"),
                "Día":              dia_es,
                "Entrada":          "--:--",
                "Sal. Almuerzo":    "--:--",
                "Reg. Almuerzo":    "--:--",
                "Salida":           salida_t.strftime("%H:%M"),
                "T. Almuerzo":      "--:--",
                "Horas trabajadas": "no marcó entrada",
                "Tardanza":         "no marcó entrada",
                "Horas extras":     "no marcó entrada",
            })
            continue

        # ── CASO NORMAL: tenemos entrada y salida ──
        entrada_dt = datetime.combine(fecha, entrada_t)
        salida_dt  = datetime.combine(fecha, salida_t)

        entrada_oficial = datetime.combine(
            fecha, datetime.strptime(horario_dia["entrada"], "%H:%M").time()
        )
        salida_oficial = datetime.combine(
            fecha, datetime.strptime(horario_dia["salida"], "%H:%M").time()
        )

        # ── Tardanza ──
        tardanza = calcular_tardanza(entrada_dt, entrada_oficial)

        # ── Tiempo de almuerzo real ──
        tiempo_almuerzo = timedelta(0)
        almuerzo_str = "--:--"

        if salida_almuerzo_t and regreso_almuerzo_t:
            salida_alm_dt  = datetime.combine(fecha, salida_almuerzo_t)
            regreso_alm_dt = datetime.combine(fecha, regreso_almuerzo_t)
            tiempo_almuerzo = regreso_alm_dt - salida_alm_dt
            if tiempo_almuerzo < timedelta(0):
                tiempo_almuerzo = timedelta(0)
            almuerzo_str = formatear_hhmm(tiempo_almuerzo)
        else:
            # Si no hay marcaciones de almuerzo, descontar 1h fija
            # Permitimos configurar por día si se debe descontar o no a través
            # de la clave `descontar_almuerzo` en el horario de la sede.
            sede_nombre = sede_or_horario if isinstance(sede_or_horario, str) else ""

            # horario_dia puede contener {'entrada','salida', 'descontar_almuerzo'}
            bandera = horario_dia.get("descontar_almuerzo", None)
            if bandera is not None:
                descuenta = bool(bandera)
            else:
                descuenta = not (dia_es == "Sábado" and sede_nombre in SEDES_SIN_ALMUERZO_SABADO)

            if descuenta:
                tiempo_almuerzo = timedelta(hours=1)
                almuerzo_str    = "01h 00m (est.)"

        # ── Horas trabajadas = (salida - entrada) - almuerzo ──
        horas_trab = (salida_dt - entrada_dt) - tiempo_almuerzo
        if horas_trab < timedelta(0):
            horas_trab = timedelta(0)

        # ── Horas extras ──
        extras = calcular_extras(salida_dt, salida_oficial, tardanza)

        filas_result.append({
            "Nombre":           nombre,
            "Fecha":            fecha.strftime("%d/%m/%Y"),
            "Día":              dia_es,
            "Entrada":          entrada_t.strftime("%H:%M"),
            "Sal. Almuerzo":    salida_almuerzo_t.strftime("%H:%M") if salida_almuerzo_t else "--:--",
            "Reg. Almuerzo":    regreso_almuerzo_t.strftime("%H:%M") if regreso_almuerzo_t else "--:--",
            "Salida":           salida_t.strftime("%H:%M"),
            "T. Almuerzo":      almuerzo_str,
            "Horas trabajadas": formatear_hhmm(horas_trab),
            "Tardanza":         formatear_hhmm(tardanza),
            "Horas extras":     formatear_hhmm(extras),
        })

    # ── Totales por persona ──
    df_resultado = pd.DataFrame(filas_result)

    if df_resultado.empty:
        return df_resultado

    def extras_to_minutes(x):
        if isinstance(x, str) and "h" in x:
            partes = x.replace("h", "").replace("m", "").split()
            try:
                return int(partes[0]) * 60 + int(partes[1])
            except:
                return 0
        return 0

    df_resultado["extras_min"] = df_resultado["Horas extras"].apply(extras_to_minutes)

    filas_finales = []
    for nombre, grupo in df_resultado.groupby("Nombre", sort=False):
        filas_finales.extend(grupo.drop(columns=["extras_min"]).to_dict("records"))

        total_min = grupo["extras_min"].sum()
        total_str = f"{total_min // 60:02d}h {total_min % 60:02d}m"

        filas_finales.append({
            "Nombre":           f"TOTAL HORAS EXTRAS ({nombre})",
            "Fecha":            "",
            "Día":              "",
            "Entrada":          "",
            "Sal. Almuerzo":    "",
            "Reg. Almuerzo":    "",
            "Salida":           "",
            "T. Almuerzo":      "",
            "Horas trabajadas": "",
            "Tardanza":         "",
            "Horas extras":     total_str,
        })

    return pd.DataFrame(filas_finales)