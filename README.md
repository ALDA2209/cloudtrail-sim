# ☁ CloudTrail Simulator

Simulador interactivo de **AWS CloudTrail**, servicio de la categoría **Controles de Detección** del ecosistema de seguridad de AWS.

Trabajo práctico: *Simulación de Arquitecturas y Servicios de Seguridad Cloud*.

> Esta aplicación **no se conecta a AWS**. Emula el comportamiento, la lógica y el formato de datos de CloudTrail para comprender su funcionamiento a nivel de software.

---

## ¿Qué es AWS CloudTrail?

CloudTrail registra **todas las acciones** que se realizan en una cuenta de AWS: quién hizo qué, cuándo, desde qué IP, en qué servicio y si la acción tuvo éxito o fue denegada. Es la base de la auditoría, la investigación de incidentes y la detección de actividad sospechosa en la nube.

## Correspondencia entre AWS y el simulador

| AWS CloudTrail real | En el simulador |
|---|---|
| Un usuario llama a la API de AWS (crear bucket, eliminar servidor, etc.) | Módulo **Simular acciones** |
| CloudTrail captura el evento | Se guarda en la base de datos con el formato JSON oficial |
| Consola → *Event history* | Módulo **Event history** con filtros |
| Detalle del evento en JSON | Vista de detalle de cada evento |
| Entrega de logs a Amazon S3 | Botón **Exportar JSON** (`{"Records": [...]}`) |
| *Log file integrity validation* (SHA-256) | Módulo **Integridad** con cadena de hashes |

## Funcionalidades

- **Resumen:** totales, eventos por día, resultado de las llamadas, eventos por servicio y acciones sensibles recientes.
- **Simular acciones:** acción manual (usuario, acción, IP, región, éxito/error), generación masiva de eventos aleatorios y escenario de ataque.
- **Event history:** filtros por usuario, evento, servicio, IP, resultado, tipo (lectura/escritura) y fechas; paginación; exportación a JSON.
- **Detalle del evento:** registro completo en formato CloudTrail JSON.
- **Integridad:** verificación de la cadena de hashes SHA-256; simulación de manipulación y borrado de registros para demostrar su detección.

### Servicios y acciones simulados

| Servicio | Acciones |
|---|---|
| Consola | `ConsoleLogin` |
| S3 | `ListBuckets`, `CreateBucket`, `DeleteBucket` |
| EC2 | `DescribeInstances`, `RunInstances`, `TerminateInstances`, `AuthorizeSecurityGroupIngress` |
| IAM | `CreateUser`, `DeleteUser`, `AttachUserPolicy` |
| CloudTrail | `StopLogging` |

## Escenario de ataque: credenciales robadas

Desde la IP extranjera `185.220.101.34`, un atacante usa las credenciales del usuario `dev.backend`:

1. Prueba contraseñas: 5 `ConsoleLogin` fallidos.
2. Entra: `ConsoleLogin` exitoso.
3. Explora: `ListBuckets`.
4. Escala privilegios: `AttachUserPolicy` con `AdministratorAccess`.
5. Crea persistencia: `CreateUser` → `backdoor-user`.
6. Abre acceso remoto: `AuthorizeSecurityGroupIngress` (puerto 22 a `0.0.0.0/0`).
7. Intenta ocultarse: `StopLogging` (apaga CloudTrail).
8. Causa daño: `DeleteBucket` sobre el bucket de backups.

CloudTrail deja el rastro completo, que puede investigarse filtrando por la IP en *Event history*.

## Integridad de los registros

Cada evento guarda un hash SHA-256 de su contenido encadenado con el hash del evento anterior:

```
hash(evento N) = SHA-256( contenido de N + hash(evento N-1) )
```

- Si se **modifica** un evento, su hash deja de coincidir con su contenido.
- Si se **elimina** un evento, el siguiente queda apuntando a un hash inexistente.

## Tecnologías

- Python 3.10 o superior
- Django 5.2
- SQLite
- Bootstrap 5, Bootstrap Icons y Chart.js (por CDN)

## Cómo ejecutarlo

### Opción 1: Windows (automático)

1. Tener **Python** instalado (con la opción *Add Python to PATH*).
2. Descomprimir el proyecto.
3. Doble clic en **`iniciar.bat`**.

El script crea el entorno virtual, instala las dependencias, crea la base de datos, carga datos de demostración y abre el navegador en `http://127.0.0.1:8000`.

### Opción 2: Manual (Windows, Linux o Mac)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux / Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```

Abrir `http://127.0.0.1:8000`.

Para volver a cargar los datos de demostración en cualquier momento: `python manage.py cargar_demo` o el botón **Reiniciar datos de demostración** en el Resumen.

## Estructura del proyecto

```
cloudtrail-sim/
├── config/                  # Configuración de Django
├── trail/                   # Aplicación del simulador
│   ├── models.py            # Modelo Evento (formato CloudTrail + hashes)
│   ├── simulador.py         # Catálogo de acciones AWS y generador de eventos
│   ├── views.py             # Resumen, simulación, historial, exportación e integridad
│   ├── urls.py
│   ├── management/commands/cargar_demo.py
│   └── templates/trail/     # Plantillas HTML
├── iniciar.bat              # Arranque automático en Windows
├── requirements.txt
└── manage.py
```

## Autor

Aldahir Pablo Silva Villar
