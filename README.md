# Link de Pago

Sistema de generación de links de pago con integración Webpay para pagos en Chile.

## Descripción

Link de Pago permite a usuarios autenticados crear enlaces de pago compartibles. Los pagadores pueden completar transacciones a través de Webpay (Transbank) sin necesidad de registro. El sistema notifica automáticamente por email cuando se completa un pago.

## Características

- **Autenticación con Google OAuth** - Login seguro sin contraseñas
- **Generación de links únicos** - URLs cortas y fáciles de compartir
- **Integración Webpay Plus** - Pagos con tarjetas de crédito y débito
- **Links de uso único o múltiple** - Configurable según necesidad
- **Expiración configurable** - Links con fecha límite opcional
- **Notificaciones por email** - Alertas automáticas al recibir pagos
- **Dashboard de gestión** - Visualiza y administra tus links de pago
- **Métricas básicas** - Conteo de vistas y pagos por link

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy
- **Base de datos**: PostgreSQL
- **Autenticación**: Google OAuth (Authlib)
- **Pagos**: Transbank SDK v5 (Webpay Plus)
- **Templates**: Jinja2
- **Email**: aiosmtplib

## Instalación

### Requisitos previos

- Python 3.11+
- PostgreSQL
- Credenciales de Google OAuth
- (Producción) Credenciales de Webpay

### Setup

```bash
# Clonar repositorio
git clone <repository-url>
cd link-pago

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor de desarrollo
uvicorn app.main:app --reload
```

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
# Requerido
SECRET_KEY=tu-clave-secreta-muy-segura

# Base de datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/linkpago

# Google OAuth
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret

# Webpay (opcional en desarrollo - usa credenciales de prueba)
WEBPAY_ENVIRONMENT=integration
# Para producción:
# WEBPAY_ENVIRONMENT=production
# WEBPAY_COMMERCE_CODE=tu-codigo-comercio
# WEBPAY_API_KEY=tu-api-key

# Email (para notificaciones)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
EMAIL_FROM=noreply@tudominio.com

# App
APP_URL=http://localhost:8000
```

## Uso

### Flujo de pago

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Usuario   │────▶│ Crear Link   │────▶│  Compartir  │
│ autenticado │     │  de Pago     │     │    URL      │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌──────────────┐            │
                    │  Notifica    │◀───────────┤
                    │  por Email   │            │
                    └──────────────┘            ▼
                           ▲            ┌──────────────┐
                           │            │   Pagador    │
                    ┌──────┴──────┐     │ abre link    │
                    │   Webpay    │◀────┴──────────────┘
                    │  confirma   │
                    └─────────────┘
```

### API Endpoints

#### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/auth/google/login` | Iniciar login con Google |
| GET | `/auth/google/callback` | Callback de OAuth |
| POST | `/auth/logout` | Cerrar sesión |
| GET | `/auth/me` | Obtener usuario actual |

#### Links de Pago (requiere autenticación)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/links/` | Crear nuevo link |
| GET | `/api/v1/links/` | Listar mis links |
| GET | `/api/v1/links/{id}` | Obtener link por ID |
| PATCH | `/api/v1/links/{id}` | Actualizar link |
| DELETE | `/api/v1/links/{id}` | Cancelar link |

#### Pagos (público)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/pay/{slug}` | Página de pago |
| POST | `/pay/{slug}/init` | Iniciar transacción |
| GET | `/pay/return` | Callback de Webpay |

### Ejemplo: Crear un link de pago

```bash
curl -X POST "http://localhost:8000/api/v1/links/" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{
    "amount": 15000,
    "description": "Servicio de consultoría",
    "single_use": true,
    "expires_at": "2024-12-31T23:59:59Z"
  }'
```

Respuesta:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "abc123xyz",
  "amount": 15000,
  "description": "Servicio de consultoría",
  "currency": "CLP",
  "status": "active",
  "single_use": true,
  "times_paid": 0,
  "views_count": 0,
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

El link de pago será: `http://localhost:8000/pay/abc123xyz`

## Desarrollo

```bash
# Activar entorno virtual
source venv/bin/activate

# Servidor con recarga automática
uvicorn app.main:app --reload

# Crear migración
alembic revision --autogenerate -m "descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1
```

### Webpay en desarrollo

En modo `integration`, el sistema usa automáticamente las credenciales de prueba de Transbank. Para probar pagos:

- **Tarjeta de crédito**: 4051 8856 0044 6623
- **CVV**: 123
- **Fecha expiración**: cualquier fecha futura
- **RUT**: 11.111.111-1
- **Clave**: 123

## Estados de un Link

| Estado | Descripción |
|--------|-------------|
| `active` | Disponible para recibir pagos |
| `paid` | Pagado (solo para links de uso único) |
| `expired` | Fecha de expiración alcanzada |
| `cancelled` | Cancelado por el usuario |

## Licencia

MIT
