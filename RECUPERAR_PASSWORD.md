# Implementación: recuperación de contraseña

Se agregó al proyecto un flujo de recuperación desde el login. La solicitud devuelve siempre el mismo mensaje, tanto si el correo existe como si no. El backend envía un token aleatorio de un solo uso; en PostgreSQL se almacena solo su hash SHA-256. El enlace vence por defecto en 30 minutos y al cambiar la contraseña se invalidan los tokens pendientes de esa cuenta.

## Archivos modificados o añadidos

- `backend/app/config.py`: ajustes SMTP y vigencia.
- `backend/app/models.py`: tabla de tokens de recuperación.
- `backend/app/schemas.py`: validación de solicitud y contraseña nueva.
- `backend/app/routers/auth.py`: endpoints de solicitud y cambio de contraseña.
- `backend/app/password_reset_mail.py`: envío SMTP.
- `backend/alembic/versions/b7d2c9f41a60_password_reset_tokens.py`: migración de base de datos.
- `backend/.env.example`: plantilla con las variables nuevas.
- `frontend/src/api.js`, `frontend/src/components/Login.jsx` y `Login.css`: interfaz y llamadas al backend.
- `.gitignore`: excluye respaldos `.dump` y `.backup`.

## Aplicar los cambios

1. Reemplaza/actualiza los archivos del proyecto con las versiones de este paquete. Conserva tus archivos locales `backend/.env` y `frontend/.env`; no los sobrescribas con plantillas ni los subas a GitHub.
2. Desde Git Bash, entra al proyecto y revisa que el respaldo local no vaya a GitHub:

```bash
cd /f/Bot_Empleos
git status --short
```

Si `backend/bot_empleos_completo.dump` o cualquier `.dump` aparece en estado de seguimiento, no lo subas. El `.gitignore` actualizado ignora archivos `.dump` nuevos; si ya estaba trackeado, quítalo del índice con `git rm --cached backend/bot_empleos_completo.dump` (no borra el archivo local).

3. Envía los cambios al repositorio:

```bash
git add .
git status --short
git commit -m "Agregar recuperación de contraseña"
git push
```

Antes del commit verifica que `.env`, respaldos y secretos no aparezcan staged.

## Variables para Render

En el servicio del backend, abre **Environment** y añade estas variables con los datos de un proveedor de correo que ofrezca SMTP:

```text
FRONTEND_URL=https://bot-empleo.vercel.app
SMTP_HOST=servidor-smtp-del-proveedor
SMTP_PORT=587
SMTP_USERNAME=usuario-smtp
SMTP_PASSWORD=secreto-smtp
SMTP_FROM_EMAIL=correo-remitente-verificado
SMTP_USE_SSL=false
PASSWORD_RESET_MINUTES=30
```

Los valores `SMTP_HOST`, usuario, contraseña y remitente dependen del proveedor que elijas. Verifica el dominio/remitente con ese proveedor. El código usa STARTTLS para el puerto 587; para conexión SSL implícita usa puerto 465 y `SMTP_USE_SSL=true`. No pongas credenciales SMTP en Vercel, variables `VITE_*`, GitHub ni en el navegador.

`FRONTEND_URL` debe ser el dominio de Vercel solamente, sin ruta y sin barra final. Actualiza `CORS_ORIGINS` solo si cambia el origen web.

## Migrar y desplegar

Haz push a GitHub y espera a que Render y Vercel terminen sus despliegues. Para añadir la tabla a Neon, ejecuta una sola vez la migración desde Render en el directorio raíz configurado (`backend`):

```bash
alembic upgrade head
```

Lo preferible es poner ese comando como **Pre-Deploy Command** para futuras migraciones. También puede ejecutarse en Render Shell, siempre después de que la nueva versión esté desplegada y con `DATABASE_URL` apuntando a Neon.

## Probar

1. Abre el login publicado y pulsa **¿Olvidaste tu contraseña?**.
2. Escribe un correo de cuenta y envía la solicitud. La pantalla debe mostrar el mensaje genérico de confirmación.
3. Abre el correo y el enlace desde el mismo dominio de Vercel. Define una contraseña nueva de al menos 8 caracteres y confírmala.
4. Inicia sesión con la contraseña nueva. El enlace solo funciona una vez y vence según `PASSWORD_RESET_MINUTES`.

Si no llega el correo, revisa que Render tenga todas las variables, que el remitente esté autorizado por el proveedor y los logs del servicio. No compartas contraseñas SMTP, links de restablecimiento, tokens ni cadenas de Neon.
