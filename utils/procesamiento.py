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


# ─────────────────────────────────────────────────────────────
# VALIDACIÓN INDEPENDIENTE
# ─────────────────────────────────────────────────────────────
# IMPORTANTE: esta función YA NO vuelve a llamar calcular_extras() para
# "comprobar" el resultado contra sí mismo (eso era tautológico: si la
# fórmula tenía un error, la revisión SIEMPRE daba "OK" porque comparaba
# un número contra sí mismo). En su lugar valida sobre los datos crudos
# de marcación con reglas de sentido común, independientes de la fórmula
# de cálculo de extras.

def validar_calculo(entrada_dt, salida_dt, entrada_oficial_dt, salida_oficial_dt, tardanza_td,
                     tiempo_almuerzo_td, horas_trab_td, extras_td,
                     marcas_dia=None, salida_almuerzo_t=None, regreso_almuerzo_t=None, fecha=None,
                     umbral_extras_minutos=30, permiso_salida_temprana=False):
    """Valida el cálculo de un día con reglas independientes de la fórmula de extras."""
    alertas = []

    # ── Reglas de negocio sobre permisos / salida temprana ──
    if permiso_salida_temprana and salida_dt < salida_oficial_dt:
        alertas.append(
            "Salida temprana con permiso detectada; verificar que corresponda a un "
            "cambio de turno o ajuste especial autorizado."
        )
    elif salida_dt < salida_oficial_dt and entrada_dt <= entrada_oficial_dt:
        alertas.append("Salida anticipada respecto al horario oficial, sin permiso registrado.")

    # ── Chequeo aritmético básico (detecta bugs de código, no de marcación) ──
    horas_esperadas = max((salida_dt - entrada_dt) - tiempo_almuerzo_td, timedelta(0))
    if abs((horas_trab_td - horas_esperadas).total_seconds()) > 60:
        alertas.append(
            f"Horas trabajadas esperadas {formatear_hhmm(horas_esperadas)} vs. "
            f"registradas {formatear_hhmm(horas_trab_td)} (inconsistencia interna)."
        )

    # ── Jornada bruta con sentido físico ──
    jornada_bruta = salida_dt - entrada_dt
    if jornada_bruta.total_seconds() <= 0:
        alertas.append("Salida registrada antes o igual que la entrada (marcación corrupta).")
    elif jornada_bruta > timedelta(hours=14):
        alertas.append(
            f"Jornada bruta de {formatear_hhmm(jornada_bruta)} supera 14 horas; "
            f"revisar si falta una marcación o se mezcló con otro día."
        )

    # ── Almuerzo con sentido físico ──
    if salida_almuerzo_t and regreso_almuerzo_t and fecha:
        alm = datetime.combine(fecha, regreso_almuerzo_t) - datetime.combine(fecha, salida_almuerzo_t)
        if alm.total_seconds() < 0:
            alertas.append("Regreso de almuerzo marcado antes que la salida a almuerzo.")
        elif alm < timedelta(minutes=15):
            alertas.append(
                f"Almuerzo de solo {formatear_hhmm(alm)}; posible marcación duplicada o error del lector."
            )
        elif alm > timedelta(hours=3):
            alertas.append(f"Almuerzo de {formatear_hhmm(alm)} inusualmente largo; revisar marcaciones.")

    # ── Marcaciones muy próximas entre sí (doble lectura del huellero) ──
    if marcas_dia and fecha:
        for i in range(len(marcas_dia) - 1):
            delta = datetime.combine(fecha, marcas_dia[i + 1]) - datetime.combine(fecha, marcas_dia[i])
            if delta < timedelta(minutes=2):
                alertas.append(
                    f"Marcaciones {marcas_dia[i].strftime('%H:%M')} y "
                    f"{marcas_dia[i + 1].strftime('%H:%M')} con menos de 2 min de diferencia; "
                    f"posible doble lectura del huellero."
                )

        # El sistema solo usa 1ra, 2da, 3ra y última marca del día (ver asignar_marcaciones).
        # Si hay más de 4, se están descartando marcaciones intermedias en silencio.
        if len(marcas_dia) > 4:
            descartadas = len(marcas_dia) - 4
            alertas.append(
                f"Se registraron {len(marcas_dia)} marcaciones en el día; el sistema solo usa la "
                f"1ra, 2da, 3ra y última — hay {descartadas} marcación(es) intermedia(s) descartada(s), "
                f"revisar manualmente."
            )

    # ── Imposibilidad matemática ──
    if extras_td > horas_trab_td:
        alertas.append("Las horas extra calculadas superan las horas trabajadas totales (imposible).")

    if alertas:
        return "Revisar", " | ".join(alertas)
    return "OK", "Cálculo consistente y sin anomalías detectadas en los datos crudos."


def asignar_marcaciones(horas_ordenadas: list, fecha) -> dict:
    """
    Asigna cada marcación cruda a un rol (entrada / salida almuerzo / regreso
    almuerzo / salida). Con 2 o 4+ marcaciones la asignación es prácticamente
    segura (primera=entrada, última=salida, y con 4+ las dos de en medio son
    almuerzo). Con 1 o 3 marcaciones es una SUPOSICIÓN, porque no hay forma
    de saber con solo la hora si a la persona le faltó marcar algo o si
    marcó de más — por eso estos casos se devuelven marcados como
    "ambiguo" para que procesar_registros los mande a revisión manual en
    vez de darlos por buenos silenciosamente.
    """
    r = {
        "entrada": None, "salida_almuerzo": None, "regreso_almuerzo": None, "salida": None,
        "ambiguo": False, "motivo_ambiguo": None,
    }
    n = len(horas_ordenadas)
    if n == 0:
        return r
    if n == 1:
        h = horas_ordenadas[0]
        r["entrada" if h.hour < 13 else "salida"] = h
        r["ambiguo"] = True
        r["motivo_ambiguo"] = (
            "Solo hay 1 marcación en el día; se asumió entrada o salida según la "
            "hora, pero pudo faltar marcar el resto de la jornada."
        )
        return r
    if n == 2:
        r["entrada"] = horas_ordenadas[0]
        r["salida"]  = horas_ordenadas[-1]
        return r
    if n == 3:
        r["entrada"]         = horas_ordenadas[0]
        r["salida_almuerzo"] = horas_ordenadas[1]
        r["salida"]          = horas_ordenadas[-1]
        r["ambiguo"] = True
        r["motivo_ambiguo"] = (
            "Hay 3 marcaciones en el día; se asumió que la marca del medio es "
            "'salida a almuerzo', pero pudo ser en realidad el 'regreso de "
            "almuerzo' (si la persona olvidó marcar la salida) — confirmar con "
            "la persona o el jefe directo."
        )
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
                "Tardanza": "no marcó", "Horas extras": "no marcó",
                "Validación": "Revisar", "Detalle validación": "Día sin ninguna marcación registrada."})
            continue

        # ── Solo entrada ──
        if entrada_t is not None and salida_t is None:
            filas_result.append({**base,
                "Entrada": entrada_t.strftime("%H:%M"),
                "Sal. Almuerzo": salida_almuerzo_t.strftime("%H:%M") if salida_almuerzo_t else "--:--",
                "Reg. Almuerzo": regreso_almuerzo_t.strftime("%H:%M") if regreso_almuerzo_t else "--:--",
                "Salida": "--:--", "T. Almuerzo": "--:--",
                "Horas trabajadas": "no marcó salida",
                "Tardanza": "no marcó salida", "Horas extras": "no marcó salida",
                "Validación": "Revisar", "Detalle validación": "Falta marcación de salida."})
            continue

        # ── Solo salida ──
        if entrada_t is None and salida_t is not None:
            filas_result.append({**base,
                "Entrada": "--:--", "Sal. Almuerzo": "--:--",
                "Reg. Almuerzo": "--:--", "Salida": salida_t.strftime("%H:%M"),
                "T. Almuerzo": "--:--",
                "Horas trabajadas": "no marcó entrada",
                "Tardanza": "no marcó entrada", "Horas extras": "no marcó entrada",
                "Validación": "Revisar", "Detalle validación": "Falta marcación de entrada."})
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
            marcas_dia=horas_dia,
            salida_almuerzo_t=salida_almuerzo_t,
            regreso_almuerzo_t=regreso_almuerzo_t,
            fecha=fecha,
            umbral_extras_minutos=umbral_extras_minutos,
            permiso_salida_temprana=permiso_salida_temprana,
        )

        # La asignación de marcaciones (1 o 3 marcas) es una suposición, no un
        # hecho verificado: si fue ambigua, el día pasa a "Revisar" sin importar
        # lo que haya dado el resto de los chequeos.
        if marcas.get("ambiguo"):
            estado_validacion = "Revisar"
            motivo_asignacion = marcas["motivo_ambiguo"]
            detalle_validacion = (
                f"{motivo_asignacion} | {detalle_validacion}"
                if detalle_validacion and detalle_validacion != "Cálculo consistente y sin anomalías detectadas en los datos crudos."
                else motivo_asignacion
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