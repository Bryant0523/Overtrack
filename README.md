# Overtrack

Overtrack es una aplicación web en Flask que procesa registros de marcaciones de un huellero para generar reportes de asistencia, tardanzas y horas extras.

## Funcionalidad principal

- Cargar archivos CSV o Excel con datos de marcaciones.
- Seleccionar la sede de trabajo (Medellín, Barranquilla o Cartagena).
- Procesar registros de entrada/salida por empleado y fecha.
- Mostrar una vista previa con:
  - Nombre
  - Fecha
  - Día
  - Entrada
  - Salida
  - Horas trabajadas
  - Tardanza
  - Horas extras
- Filtrar por empleado.
- Exportar reportes en Excel:
  - Horas extras
  - Llegadas

## Estructura del proyecto

- `app.py` - aplicación principal de Flask.
- `utils/procesamiento.py` - lógica para procesar los registros de marcaciones.
- `templates/` - plantillas HTML de la interfaz.
- `static/` - recursos estáticos como CSS.
- `uploads/` - carpeta donde se guardan los archivos cargados.

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
pip install flask pandas openpyxl
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
4. Revisar la vista previa y descargar los reportes.

## Sedes y horarios predefinidos

- `medellin`
  - Lunes a sábado: 08:00 - 17:00
- `barranquilla`
  - Lunes a viernes: 08:00 - 17:00
  - Sábado: 09:00 - 14:00
- `cartagena`
  - Lunes a viernes: 09:00 - 17:30
  - Sábado: 09:00 - 15:00

## Notas importantes

- El cálculo de horas extras considera entrada antes del horario oficial y salida después del horario oficial.
- Si el empleado no marca entrada o salida, se muestra un mensaje específico.
- La aplicación guarda temporalmente los datos procesados en memoria durante la sesión.
- La exportación crea archivos Excel con formato y totales.

## Mejoras futuras

- Agregar un archivo `requirements.txt` para instalar dependencias automáticamente.
- Soporte completo para versiones de domingos y días no laborales.
- Validación más robusta del formato de los archivos de entrada.
- Guardado persistente de datos si se desea conservar los registros.
