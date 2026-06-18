from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
import os
import io
import json
from openpyxl.styles import PatternFill, Alignment, Font
from openpyxl.worksheet.table import Table, TableStyleInfo

from utils.procesamiento import procesar_registros, HORARIOS_SEDES, agregar_empleado, cargar_empleados, guardar_empleados

app = Flask(__name__)
app.secret_key = "clave-ultra-secreta"

# Contraseña para acceder a configuraciones
CONFIG_PASSWORD = "admin123"

MEMORY = {"permisos": []}

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html", sedes=list(HORARIOS_SEDES.keys()))

@app.route("/horarios")
def horaios():
    return render_template("horarios.html", horarios=HORARIOS_SEDES)

@app.route("/subir", methods=["POST"])
def subir():
    archivo = request.files.get("archivo_csv")
    sede = request.form.get("sede")

    if not archivo or not archivo.filename:
        return render_template("index.html", mensaje_error="No se seleccionó archivo",
                               sedes=list(HORARIOS_SEDES.keys()))

    if sede not in HORARIOS_SEDES:
        return render_template("index.html", mensaje_error="Seleccione una sede válida",
                               sedes=list(HORARIOS_SEDES.keys()))

    ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
    archivo.save(ruta)

    extension = archivo.filename.lower().split(".")[-1]

    try:
        if extension in ["xlsx", "xls"]:
            df = pd.read_excel(ruta)
        elif extension == "csv":
            try:
                df = pd.read_csv(ruta, encoding="utf-8", sep=None, engine="python", on_bad_lines="skip")
            except:
                df = pd.read_csv(ruta, encoding="latin-1", sep=None, engine="python", on_bad_lines="skip")
        else:
            return render_template("index.html",
                                   mensaje_error="Formato no soportado. Use CSV o Excel.",
                                   sedes=list(HORARIOS_SEDES.keys()))
    except Exception as e:
        return render_template("index.html",
                               mensaje_error=f"Error leyendo el archivo: {str(e)}",
                               sedes=list(HORARIOS_SEDES.keys()))

    procesado = procesar_registros(df, sede)
    procesado = attach_permissions(procesado)
    
    # Guardar empleados encontrados
    nombres_empleados = procesado["Nombre"].unique()
    for nombre in nombres_empleados:
        if "TOTAL" not in str(nombre).upper():
            agregar_empleado(nombre)
    
    MEMORY["df"] = procesado

    return redirect(url_for("vista_previa"))


@app.route("/vista_previa", methods=["GET", "POST"])
def vista_previa():
    df = MEMORY.get("df")
    if df is None:
        return "No hay datos cargados"

    nombres = sorted([
        n for n in df["Nombre"].unique()
        if "TOTAL" not in n.upper()
    ])

    if request.method == "GET":
        return render_template(
            "vista_previa.html",
            tabla=df.to_dict(orient="records"),
            nombres=nombres,
            empleado_seleccionado=None
        )

    empleado = request.form.get("empleado")

    if not empleado or empleado == "":
        filtrado = df.copy()
        return render_template(
            "vista_previa.html",
            tabla=filtrado.to_dict(orient="records"),
            nombres=nombres,
            empleado_seleccionado=empleado
        )

    # Filtrar solo esa persona
    filtrado = df[df["Nombre"] == empleado].copy()
    filas_normales = filtrado[~filtrado["Nombre"].str.contains("TOTAL")].copy()

    def to_minutes(x):
        if isinstance(x, str) and "h" in x:
            partes = x.replace("h", "").replace("m", "").split()
            try:
                return int(partes[0]) * 60 + int(partes[1])
            except:
                return 0
        return 0

    total_min = filas_normales["Horas extras"].apply(to_minutes).sum()
    total_str = f"{total_min // 60:02d}h {total_min % 60:02d}m"

    fila_total = {
        "Nombre":           f"TOTAL HORAS EXTRAS ({empleado})",
        "Fecha":            "",
        "Día":              "",
        "Entrada":          "",
        "Sal. Almuerzo":    "",
        "Reg. Almuerzo":    "",
        "Salida":           "",
        "T. Almuerzo":      "",
        "Horas trabajadas": "",
        "Tardanza":         "TOTAL",
        "Horas extras":     total_str,
    }

    filtrado = filas_normales.to_dict("records")
    filtrado.append(fila_total)

    return render_template(
        "vista_previa.html",
        tabla=filtrado,
        nombres=nombres,
        empleado_seleccionado=empleado
    )


def parse_hhmm(valor):
    if isinstance(valor, str) and "h" in valor:
        partes = valor.replace("h", "").replace("m", "").split()
        try:
            return int(partes[0]) * 60 + int(partes[1])
        except Exception:
            return 0
    return 0


def attach_permissions(df):
    permisos = MEMORY.get("permisos", [])
    if df is None or df.empty or not permisos:
        return df

    df = df.copy()
    df["Permiso"] = ""
    for permiso in permisos:
        nombre_perm = permiso["nombre"].strip().lower()
        fecha_perm = permiso["fecha"]
        texto_perm = f"{permiso['tipo']} ({permiso['minutos']}m)"
        if permiso.get("motivo"):
            texto_perm += f" - {permiso['motivo']}"

        for idx, row in df.iterrows():
            if str(row["Nombre"]).strip().lower() == nombre_perm and row["Fecha"] == fecha_perm:
                existente = df.at[idx, "Permiso"]
                df.at[idx, "Permiso"] = (
                    f"{existente}; {texto_perm}" if existente else texto_perm
                )

    return df


@app.route('/permisos', methods=['GET', 'POST'])
def permisos():
    permisos = MEMORY.setdefault("permisos", [])
    mensaje = None
    mensaje_error = None

    if request.method == 'POST':
        nombre = request.form.get("nombre", "").strip()
        fecha = request.form.get("fecha", "").strip()
        tipo = request.form.get("tipo", "").strip()
        minutos = request.form.get("minutos", "").strip()
        motivo = request.form.get("motivo", "").strip()

        if not nombre or not fecha or not tipo or not minutos:
            mensaje_error = "Complete todos los campos obligatorios."
        else:
            try:
                minutos_val = int(minutos)
                permiso = {
                    "nombre": nombre,
                    "fecha": fecha,
                    "tipo": tipo,
                    "minutos": minutos_val,
                    "motivo": motivo,
                }
                permisos.append(permiso)
                MEMORY["df"] = attach_permissions(MEMORY.get("df"))
                mensaje = "Permiso guardado correctamente."
            except ValueError:
                mensaje_error = "Los minutos deben ser un número entero."

    return render_template(
        "permisos.html",
        permisos=permisos,
        mensaje=mensaje,
        mensaje_error=mensaje_error,
        sedes=list(HORARIOS_SEDES.keys()),
    )


@app.route('/ajustes')
def ajustes():
    return render_template(
        "ajustes.html",
        horarios=HORARIOS_SEDES,
        permisos=len(MEMORY.get("permisos", [])),
        sedes=list(HORARIOS_SEDES.keys()),
    )


@app.route('/tabla_resultados')
def tabla_resultados():
    df = MEMORY.get("df")
    if df is None or df.empty:
        return render_template(
            "tabla_resultados.html",
            columnas=[],
            filas=[],
            mensaje="No hay datos cargados.",
            sedes=list(HORARIOS_SEDES.keys()),
        )

    df_resultados = df[~df["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)].copy()
    filas = []

    for nombre, grupo in df_resultados.groupby("Nombre", sort=False):
        total_trab = sum(parse_hhmm(valor) for valor in grupo["Horas trabajadas"])
        total_extras = sum(parse_hhmm(valor) for valor in grupo["Horas extras"])
        permisos_list = [
            p for p in MEMORY.get("permisos", [])
            if p["nombre"].strip().lower() == nombre.strip().lower()
        ]
        permisos_text = "; ".join(
            f"{p['tipo']} {p['minutos']}m" for p in permisos_list
        )

        filas.append({
            "Nombre": nombre,
            "Días registrados": len(grupo),
            "Horas trabajadas totales": f"{total_trab // 60:02d}h {total_trab % 60:02d}m",
            "Horas extras totales": f"{total_extras // 60:02d}h {total_extras % 60:02d}m",
            "Permisos": permisos_text,
        })

    columnas = [
        "Nombre",
        "Días registrados",
        "Horas trabajadas totales",
        "Horas extras totales",
        "Permisos",
    ]

    return render_template(
        "tabla_resultados.html",
        columnas=columnas,
        filas=filas,
        mensaje=None,
        sedes=list(HORARIOS_SEDES.keys()),
    )


@app.route('/descargar_resumen')
def descargar_resumen():
    df = MEMORY.get("df")
    if df is None or df.empty:
        return "No hay datos cargados para descargar", 400

    df_resultados = df[~df["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)].copy()
    resumen = []

    for nombre, grupo in df_resultados.groupby("Nombre", sort=False):
        total_trab = sum(parse_hhmm(valor) for valor in grupo["Horas trabajadas"])
        total_extras = sum(parse_hhmm(valor) for valor in grupo["Horas extras"])

        resumen.append({
            "Nombre": nombre,
            "Días registrados": len(grupo),
            "Horas trabajadas totales": f"{total_trab // 60:02d}h {total_trab % 60:02d}m",
            "Horas extras totales": f"{total_extras // 60:02d}h {total_extras % 60:02d}m",
        })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(resumen).to_excel(writer, index=False, sheet_name="Resumen")

        hoja = writer.sheets["Resumen"]
        last_row = len(resumen) + 1
        last_col = len(resumen[0].keys()) if resumen else 1
        ref = f"A1:{chr(64 + last_col)}{last_row}"
        tabla = Table(displayName="TablaResumen", ref=ref)
        tabla.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False, showLastColumn=False,
            showRowStripes=True, showColumnStripes=False
        )
        hoja.add_table(tabla)

        for col in hoja.columns:
            max_length = max((len(str(cell.value or "")) for cell in col), default=0)
            hoja.column_dimensions[col[0].column_letter].width = max_length + 3

    output.seek(0)
    return send_file(output, download_name="resumen_horas.xlsx", as_attachment=True)


@app.route('/limpiar')
def limpiar():
    MEMORY["df"] = None
    MEMORY["permisos"] = []
    return redirect(url_for("index"))


@app.route('/config/login', methods=['GET', 'POST'])
def config_login():
    if request.method == 'POST':
        password = request.form.get("password", "")
        if password == CONFIG_PASSWORD:
            session['config_auth'] = True
            return redirect(url_for("configuraciones"))
        else:
            return render_template("config_login.html", error="Contraseña incorrecta")
    return render_template("config_login.html")


@app.route('/config/logout')
def config_logout():
    session.pop('config_auth', None)
    return redirect(url_for("index"))


def require_config_auth(f):
    """Decorador para requerir autenticación en configuraciones"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('config_auth'):
            return redirect(url_for('config_login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/configuraciones')
@require_config_auth
def configuraciones():
    """Panel principal de configuraciones"""
    sedes_list = list(HORARIOS_SEDES.keys())
    empleados = cargar_empleados()
    return render_template(
        "configuraciones.html",
        sedes=sedes_list,
        horarios=HORARIOS_SEDES,
        empleados=empleados,
        total_sedes=len(sedes_list),
        total_empleados=len(empleados)
    )


@app.route('/config/dashboard')
@require_config_auth
def config_dashboard():
    permisos = MEMORY.get("permisos", [])
    sedes_list = list(HORARIOS_SEDES.keys())
    empleados = cargar_empleados()

    df = MEMORY.get("df")
    empleados_totales = len(empleados)
    if df is None or df.empty:
        resumen = {
            "registros": 0,
            "empleados_presentes": 0,
            "tardanzas": 0,
            "horas_extras": 0,
            "top_tardanzas": [],
            "top_extras": [],
            "chart_asistencia": {
                "labels": ["Presentes", "Sin registro"],
                "data": [0, empleados_totales],
            },
            "chart_tardanzas": {
                "labels": [],
                "data": [],
            },
            "chart_extras": {
                "labels": [],
                "data": [],
            },
        }
    else:
        df_activo = df[~df["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)].copy()
        df_activo["tardanza_min"] = df_activo["Tardanza"].apply(parse_hhmm)
        df_activo["extras_min"] = df_activo["Horas extras"].apply(parse_hhmm)

        empleados_presentes = df_activo[df_activo["Entrada"] != "--:--"]["Nombre"].nunique()
        tardanzas = df_activo[df_activo["tardanza_min"] > 0]
        extras = df_activo[df_activo["extras_min"] > 0]

        top_tardanzas = (
            tardanzas.sort_values("tardanza_min", ascending=False)
            .head(5)[["Nombre", "Fecha", "Día", "Tardanza"]]
            .to_dict("records")
        )
        top_extras = (
            extras.sort_values("extras_min", ascending=False)
            .head(5)[["Nombre", "Fecha", "Día", "Horas extras"]]
            .to_dict("records")
        )

        tardanzas_por_empleado = (
            tardanzas.groupby("Nombre")["tardanza_min"].sum()
            .sort_values(ascending=False)
            .head(5)
        )
        extras_por_empleado = (
            extras.groupby("Nombre")["extras_min"].sum()
            .sort_values(ascending=False)
            .head(5)
        )

        resumen = {
            "registros": len(df_activo),
            "empleados_presentes": empleados_presentes,
            "tardanzas": tardanzas["Nombre"].nunique(),
            "horas_extras": extras["Nombre"].nunique(),
            "top_tardanzas": top_tardanzas,
            "top_extras": top_extras,
            "chart_asistencia": {
                "labels": ["Presentes", "Sin registro"],
                "data": [empleados_presentes, max(empleados_totales - empleados_presentes, 0)],
            },
            "chart_tardanzas": {
                "labels": tardanzas_por_empleado.index.tolist(),
                "data": tardanzas_por_empleado.tolist(),
            },
            "chart_extras": {
                "labels": extras_por_empleado.index.tolist(),
                "data": extras_por_empleado.tolist(),
            },
        }

    return render_template(
        "config_dashboard.html",
        total_permisos=len(permisos),
        total_sedes=len(sedes_list),
        total_empleados=len(empleados),
        permisos=permisos,
        resumen=resumen,
    )


@app.route('/config/sedes', methods=['GET', 'POST'])
@require_config_auth
def config_sedes():
    """CRUD de sedes"""
    sedes_config = HORARIOS_SEDES
    
    if request.method == 'POST':
        accion = request.form.get("accion")
        nombre_sede = request.form.get("nombre_sede", "").strip().lower()
        
        if accion == "crear" and nombre_sede:
            if nombre_sede not in sedes_config:
                sedes_config[nombre_sede] = {
                    "Lunes": {"entrada": "08:00", "salida": "17:00", "descontar_almuerzo": True},
                    "Martes": {"entrada": "08:00", "salida": "17:00", "descontar_almuerzo": True},
                    "Miércoles": {"entrada": "08:00", "salida": "17:00", "descontar_almuerzo": True},
                    "Jueves": {"entrada": "08:00", "salida": "17:00", "descontar_almuerzo": True},
                    "Viernes": {"entrada": "08:00", "salida": "17:00", "descontar_almuerzo": True},
                    "Sábado": {"entrada": "08:00", "salida": "17:00", "descontar_almuerzo": True},
                }
                guardar_config_sedes(sedes_config)
        
        elif accion == "eliminar" and nombre_sede:
            if nombre_sede in sedes_config and len(sedes_config) > 1:
                del sedes_config[nombre_sede]
                guardar_config_sedes(sedes_config)
    
    return render_template(
        "config_sedes.html",
        sedes=list(sedes_config.keys())
    )


@app.route('/config/horarios/<sede>', methods=['GET', 'POST'])
@require_config_auth
def config_horarios(sede):
    """CRUD de horarios por sede"""
    if sede not in HORARIOS_SEDES:
        return "Sede no encontrada", 404
    
    horario_sede = HORARIOS_SEDES[sede]
    
    if request.method == 'POST':
        for dia in list(horario_sede.keys()):
            entrada = request.form.get(f"{dia}_entrada", "")
            salida = request.form.get(f"{dia}_salida", "")
            descontar = request.form.get(f"{dia}_descontar")
            # Si checkbox está presente -> True, si no -> False
            descontar_flag = True if descontar is not None else False
            if entrada and salida:
                horario_sede[dia] = {
                    "entrada": entrada,
                    "salida": salida,
                    "descontar_almuerzo": descontar_flag,
                }
        guardar_config_sedes(HORARIOS_SEDES)
    
    return render_template(
        "config_horarios.html",
        sede=sede,
        horario=horario_sede
    )


def guardar_config_sedes(config_dict):
    """Guarda las sedes actualizadas en config/sedes.json"""
    ruta_config = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "config", "sedes.json")
    )
    try:
        with open(ruta_config, "w", encoding="utf-8") as archivo:
            json.dump(config_dict, archivo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


@app.route('/descargar_extras')
def descargar_extras():
    nombre = request.args.get("nombre", "todos")

    df = MEMORY.get("df")
    if df is None or df.empty:
        return "No hay datos cargados para exportar", 400

    df = df[~df["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)].copy()
    if nombre != "todos":
        df = df[df["Nombre"] == nombre].copy()

    columnas = [
        "Nombre", "Fecha", "Día",
        "Entrada", "Sal. Almuerzo", "Reg. Almuerzo", "Salida",
        "T. Almuerzo", "Horas trabajadas", "Tardanza", "Horas extras"
    ]
    df = df[columnas]

    def parse_horas_extras(valor):
        if isinstance(valor, str) and "h" in valor:
            partes = valor.replace("h", "").replace("m", "").split()
            try:
                return int(partes[0]) * 60 + int(partes[1])
            except:
                return 0
        return 0

    df["extra_min"] = df["Horas extras"].apply(parse_horas_extras)
    total_min = df["extra_min"].sum()
    total_horas = f"{total_min // 60:02d}h {total_min % 60:02d}m"

    fila_total = {
        "Nombre":           "",
        "Fecha":            "",
        "Día":              "",
        "Entrada":          "",
        "Sal. Almuerzo":    "",
        "Reg. Almuerzo":    "",
        "Salida":           "",
        "T. Almuerzo":      "",
        "Horas trabajadas": "",
        "Tardanza":         "TOTAL",
        "Horas extras":     total_horas,
        "extra_min":        total_min,
    }

    df_total = pd.concat([df, pd.DataFrame([fila_total])], ignore_index=True)
    df_total = df_total.drop(columns=["extra_min"])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_total.to_excel(writer, index=False, sheet_name="Horas Extras")

        hoja = writer.sheets["Horas Extras"]
        last_row = len(df_total) + 1
        last_col = len(df_total.columns)

        ref = f"A1:{chr(64 + last_col)}{last_row}"
        tabla = Table(displayName="TablaExtras", ref=ref)
        tabla.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False, showLastColumn=False,
            showRowStripes=True, showColumnStripes=False
        )
        hoja.add_table(tabla)

        for col in hoja.columns:
            max_length = max((len(str(cell.value or "")) for cell in col), default=0)
            hoja.column_dimensions[col[0].column_letter].width = max_length + 3

        for i in range(1, last_row + 1):
            hoja.row_dimensions[i].height = 22

        fill_total = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        bold_font  = Font(bold=True)
        for cell in hoja[last_row]:
            cell.fill      = fill_total
            cell.font      = bold_font
            cell.alignment = Alignment(horizontal="center")

    output.seek(0)
    return send_file(output, download_name=f"horas_extras_{nombre}.xlsx", as_attachment=True)


@app.route('/descargar_llegadas')
def descargar_llegadas():
    nombre = request.args.get("nombre", "todos")

    df = MEMORY.get("df")
    if df is None or df.empty:
        return "No hay datos cargados para exportar", 400

    df = df[~df["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)].copy()
    if nombre != "todos":
        df = df[df["Nombre"] == nombre].copy()

    # Llegadas incluye entrada y también almuerzo para referencia
    columnas = ["Nombre", "Fecha", "Día", "Entrada", "Sal. Almuerzo", "Reg. Almuerzo", "T. Almuerzo"]
    df = df[columnas]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Llegadas")

        hoja = writer.sheets["Llegadas"]
        last_row = len(df) + 1
        last_col = len(df.columns)

        ref = f"A1:{chr(64 + last_col)}{last_row}"
        tabla = Table(displayName="TablaLlegadas", ref=ref)
        tabla.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False, showLastColumn=False,
            showRowStripes=True, showColumnStripes=False
        )
        hoja.add_table(tabla)

        for col in hoja.columns:
            max_length = max((len(str(cell.value or "")) for cell in col), default=0)
            hoja.column_dimensions[col[0].column_letter].width = max_length + 3

        for i in range(1, last_row + 1):
            hoja.row_dimensions[i].height = 22

    output.seek(0)
    return send_file(output, download_name=f"llegadas_{nombre}.xlsx", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)