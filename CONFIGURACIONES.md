# Sistema de Configuraciones - Documentación

## ✅ Características Implementadas

### 1. **Autenticación de Configuraciones** 
- Contraseña: `admin123`
- Ruta: `/config/login` (acceder via botón "⚙️ Configuraciones" en navbar)
- Sesión protegida con decorador `@require_config_auth`
- Logout disponible en `/config/logout`

### 2. **CRUD de Sedes**
- **Crear sedes:** Formulario para agregar nuevas sedes al sistema
- **Editar horarios:** Configurar entrada/salida por día para cada sede
- **Eliminar sedes:** Remover sedes (min. 1 sede requerida)
- Cambios se guardan en `config/sedes.json` automáticamente
- Ruta principal: `/config/sedes`

### 3. **Gestión de Horarios por Sede**
- Editor interactivo para cada día de la semana
- Validación automática de duración de jornada
- Soporte para 6 días: Lunes a Sábado
- Ruta: `/config/horarios/<sede>`
- Cambios se aplican inmediatamente en próximos cálculos

### 4. **Persistencia de Empleados**
- Se guardan automáticamente al procesar archivos CSV/Excel
- Ubicación: `config/empleados.json`
- Visualización en panel de configuraciones
- Funciones en `utils/procesamiento.py`:
  - `cargar_empleados()` - Carga lista desde JSON
  - `guardar_empleados()` - Guarda lista a JSON
  - `agregar_empleado()` - Agrega si no existe

### 5. **Panel Principal de Configuraciones**
- Estadísticas: Sedes, Empleados, Estado del Sistema
- Acceso rápido a: Gestión de sedes, Horarios, Lista de empleados
- Tabla resumen con botones "Ajustar horarios"
- Ruta: `/configuraciones` (requiere autenticación)

---

## 📁 Archivos Creados/Modificados

### Nuevos archivos:
```
config/empleados.json                    # Lista de empleados (JSON)
templates/config_login.html              # Formulario de autenticación
templates/configuraciones.html           # Panel principal
templates/config_sedes.html              # CRUD de sedes
templates/config_horarios.html           # Editor de horarios
```

### Modificados:
```
app.py                                   # +200 líneas: nuevas rutas, autenticación
utils/procesamiento.py                   # +50 líneas: gestión de empleados
templates/base.html                      # Agregado botón "⚙️ Configuraciones"
```

---

## 🔐 Flujo de Autenticación

```
Usuario clica "⚙️ Configuraciones" 
    ↓
Redirige a /config/login
    ↓
Ingresa password: admin123
    ↓
session['config_auth'] = True
    ↓
Acceso a /configuraciones y sub-rutas
```

---

## 🛠️ Nuevas Rutas API

| Ruta | Método | Autenticación | Función |
|------|--------|---------------|---------|
| `/config/login` | GET/POST | No | Formulario login |
| `/config/logout` | GET | No | Cierra sesión |
| `/configuraciones` | GET | ✅ Sí | Panel principal |
| `/config/sedes` | GET/POST | ✅ Sí | CRUD sedes |
| `/config/horarios/<sede>` | GET/POST | ✅ Sí | Editor horarios |

---

## 📊 Estructura de Datos

### empleados.json
```json
["Juan Pérez", "María García", "Carlos López"]
```

### sedes.json (config)
```json
{
  "medellin": {
    "Lunes": {"entrada": "08:00", "salida": "17:00"},
    "Martes": {"entrada": "08:00", "salida": "17:00"},
    ...
  },
  "barranquilla": {...},
  "cartagena": {...}
}
```

---

## 🎯 Casos de Uso

### Caso 1: Procesar archivo CSV
1. Usuario sube CSV en "Inicio"
2. Al procesar, empleados se guardan automáticamente en `empleados.json`
3. Aparecen en lista de empleados del panel de configuraciones

### Caso 2: Agregar nueva sede
1. Acceder a "⚙️ Configuraciones" (password: admin123)
2. Click en "Gestión de sedes"
3. Ingresa nombre (ej: "monterrey")
4. Click "+ Crear sede"
5. Nueva sede se carga con horarios por defecto (8:00-17:00)

### Caso 3: Ajustar horarios
1. Panel de configuraciones → buscar sede
2. Click "Ajustar horarios →"
3. Modificar entrada/salida por día
4. Click "💾 Guardar cambios"
5. Se recalculan tardanzas/extras para próximos archivos

---

## 🔧 Configuración de Contraseña

Para cambiar la contraseña, editar en `app.py`:
```python
CONFIG_PASSWORD = "admin123"  # Cambiar aquí
```

---

## ✨ Características Destacadas

- ✅ Persistencia automática de empleados
- ✅ CRUD funcional para sedes y horarios
- ✅ Interfaz protegida por contraseña
- ✅ Sesiones Flask (seguridad)
- ✅ Diseño Tailwind CSS coherente
- ✅ Validaciones en formularios
- ✅ Historial de cambios en JSON
- ✅ Decoradores Python para autenticación

---

## 📋 Validaciones Implementadas

1. **Sedes:** No permite eliminar la única sede
2. **Horarios:** Calcula automáticamente duración de jornada
3. **Empleados:** No duplica empleados en la lista
4. **Autenticación:** Redirige a login si no autenticado
5. **Formularios:** Requiere campos obligatorios

---

## 🚀 Próximas Mejoras (Opcional)

- [ ] Backup automático de configuraciones
- [ ] Historial de cambios en horarios
- [ ] Exportar reporte de empleados
- [ ] Cambio dinámico de contraseña
- [ ] Roles de usuario (admin/operador)
- [ ] Auditoría de cambios
- [ ] API REST para integraciones
