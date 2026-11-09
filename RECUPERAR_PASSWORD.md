# Recuperación de contraseña: configuración y despliegue

El proyecto incluye recuperación desde el login. El flujo usa un token aleatorio de un solo uso; en PostgreSQL guarda únicamente el hash, y el enlace vence por defecto en 30 minutos. La respuesta de solicitud es genérica para no revelar si un correo está registrado.

## Importante para Render Free

Render Free bloquea conexiones salientes por SMTP en los puertos 25, 465 y 587. Por eso la implementación actual prioriza la **API HTTPS de Resend** por el puerto 443. Si existe `RESEND_API_KEY`, no intenta SMTP. SMTP se conserva como alternativa para servicios de hosting que sí permitan esos puertos.

## Variables de Render para Resend

En Render, abre el servicio del backend y entra a **Environment**. Añade o corrige:

```text
RESEND_API_KEY=tu_api_key_de_resend
RESEND_FROM_EMAIL=Nexo Laboral <no-reply@haducon.shop>
FRONTEND_URL=https://bot-empleo.vercel.app
PASSWORD_RESET_MINUTES=30
```

`RESEND_API_KEY` es una clave API de Resend. No la pongas en Vercel, GitHub, el código o el chat. `RESEND_FROM_EMAIL` debe usar un dominio que Resend muestre como **Verified**. Si configuraste un remitente `@gmail.com`, Resend lo rechazará. Puedes dejar las variables `SMTP_*` antiguas; la API HTTPS de Resend se usa cuando hay `RESEND_API_KEY`.

La función requiere un dominio verificado para mandar a usuarios. El dominio de prueba `resend.dev` solo sirve para enviar a la dirección asociada a la cuenta Resend. La verificación se hace en Resend → **Domains**, añadiendo en el DNS del dominio los registros indicados por Resend.

## Publicar los cambios

1. Copia los archivos actualizados sobre el proyecto local, conservando `backend/.env`, `frontend/.env` y `.git`. No sustituyas tus archivos de secretos por plantillas.
2. Desde Git Bash:

```bash
cd /f/Bot_Empleos
git status --short
```

Confirma que no aparezcan `.env` ni `backend/bot_empleos_completo.dump`. Luego:

```bash
git add .
git status --short
git commit -m "Enviar recuperación mediante Resend HTTPS"
git push
```

3. Espera el despliegue de Render. En **Logs**, confirma que la aplicación inicia correctamente.
4. La migración `b7d2c9f41a60` crea `password_reset_tokens`; si ya la aplicaste a Neon y `alembic current` mostró esa revisión, no hace falta repetirla. Si no, ejecuta desde el backend local con `DATABASE_URL` apuntando a Neon:

```bash
python -m alembic upgrade head
```

## Probar

Desde el login, pulsa **¿Olvidaste tu contraseña?** y solicita un enlace para una cuenta registrada. Revisa **Resend → Emails** y el spam. Si hay un error, revisa los logs de Render; la API no muestra detalles al visitante para no exponer la cuenta.

Un nuevo enlace invalida los anteriores para esa cuenta. La aplicación aplica además un intervalo mínimo de 60 segundos entre envíos al mismo usuario.
