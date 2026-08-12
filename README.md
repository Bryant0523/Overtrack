# Overtrack

Overtrack es una aplicación web desarrollada en Flask para procesar registros de marcaciones de un huellero y generar reportes de asistencia, tardanzas, horas extras y almuerzos.

## Funcionalidad principal

- Cargar archivos CSV o Excel con datos de marcaciones.
- Seleccionar la sede de trabajo y procesar registros según el horario de la sede.
- Usar horarios personalizados por empleado cuando existen en la base de datos.
- Mostrar una vista previa con:
  - Nombre
  - Fecha
  - Día
  - Entrada
  - Salida
  - Salida y regreso de almuerzo
  - Horas trabajadas
  - Tardanza
  - Horas extras
  - Permisos asociados
- Filtrar por empleado en la vista previa.
- Descargar reportes Excel:
  - resumen de horas trabajadas
  - horas extras
  - llegadas
  - reporte de almuerzo
- Administrar empleados, sedes, horarios y permisos desde la interfaz.

## Estructura del proyecto

- `app.py` - aplicación principal de Flask y rutas.
- `database.py` - lógica de SQLite para empleados, horarios y permisos.
- `utils/procesamiento.py` - lógica de carga y procesamiento de marcaciones.
- `templates/` - plantillas HTML para la interfaz.
- `static/` - recursos estáticos como imágenes y estilos.
- `uploads/` - archivos cargados temporalmente.
- `config/` - archivos JSON para sedes, empleados y ajustes.
- `requeriments.txt` - dependencias del proyecto.

## Requisitos

- Python 3.10+ (recomendado)
- Flask
- pandas
- openpyxl

## Instalación

1. Crear un entorno virtual (recomendado):

```bash
python -m venv venv
```

2. Activar el entorno virtual:

- Windows PowerShell:

```powershell
./venv/Scripts/Activate.ps1
```

- Windows CMD:

```cmd
venv\Scripts\activate.bat
```

3. Instalar dependencias:

```bash
pip install -r requeriments.txt
```

## Uso

1. Ejecutar la aplicación:

```bash
python app.py
```

2. Abrir el navegador en:

```text
http://127.0.0.1:5000/
```

3. Seleccionar la sede y cargar un archivo CSV o Excel.
4. Revisar la vista previa y descargar los reportes correspondientes.
5. Si es necesario, acceder a la configuración con la ruta `/config/login`.

## Rutas y opciones principales

- `/` - página principal para cargar marcaciones.
- `/vista_previa` - vista previa de los resultados.
- `/tabla_resultados` - tabla con resumen por empleado.
- `/descargar_resumen` - descarga resumen de horas.
- `/descargar_extras` - descarga reporte de horas extras.
- `/descargar_llegadas` - descarga reporte de llegadas.
- `/descargar_almuerzo` - descarga reporte de almuerzos.
- `/empleados` - gestión de empleados.
- `/permisos` - gestión de permisos temporales.
- `/ajustes` - panel de ajustes básicos.
- `/config/login` - acceso a configuración protegida.
- `/config/sedes` - administración de sedes.
- `/config/horarios/<sede>` - edición de horarios por sede.

## Configuración y base de datos

- La aplicación usa SQLite para almacenar empleados, horarios personalizados y permisos.
- La base de datos se inicializa automáticamente al arrancar `app.py`.
- Los horarios de sedes se cargan desde `config/sedes.json` y pueden editarse desde la interfaz.
- El umbral mínimo para horas extras se puede ajustar en `config/settings.json`.

## Notas importantes

- El cálculo de horas extras considera entrada temprana y salida tardía respecto al horario oficial.
- Las horas extras menores al umbral configurado (por defecto 30 minutos) se ignoran.
- Los permisos de tardanza o salida temprana se guardan en la base de datos y se aplican al reporte.
- La aplicación guarda datos procesados en memoria durante la sesión; si reinicias el servidor se pierde la carga actual.

## Recomendaciones

- Usa archivos CSV o Excel que contengan las columnas de marcaciones del huellero.
- Revisa la página de configuración para validar que las sedes y horarios estén bien definidos.
- Si agregas nuevos empleados, confirma que el nombre esté bien escrito para que se mantenga en la lista.

## Contacto

Para ayuda adicional, revisa los archivos `app.py`, `database.py` y `utils/procesamiento.py` para comprender la lógica de procesamiento y los datos esperados.
