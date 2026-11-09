# Nexo Laboral

Aplicación web para buscar ofertas, compararlas con tu perfil y analizarlas con IA. El proyecto contiene un backend FastAPI y una interfaz React/Vite.

## Requisitos

- Python 3.11 o posterior.
- Node.js compatible con Vite 8 (Node 20.19+ o 22.12+).
- PostgreSQL.

## Inicio rápido

1. Crea una base PostgreSQL vacía y configura `backend/.env` copiando `backend/.env.example`. Genera valores nuevos para las claves:

   ```bash
   cd backend
   cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"  # SECRET_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
   ```

   Actualiza `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY` y `CORS_ORIGINS`. Nunca uses claves publicadas o compartidas.

2. Instala y arranca el backend:

   ```bash
   cd backend
   python -m venv .venv
   # Linux/macOS: source .venv/bin/activate
   # Windows PowerShell: .venv\\Scripts\\Activate.ps1
   pip install -r requirements.txt
   # Necesario solo si vas a usar Magneto:
   python -m playwright install chromium
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

3. En otra terminal, configura la URL de API y arranca el frontend:

   ```bash
   cd frontend
   cp .env.example .env
   npm ci
   npm run dev
   ```

   Abre la dirección local que muestra Vite.

## Filtro por día en que se encontró

En **Ofertas**, el filtro muestra las vacantes encontradas el lunes, martes, etc. de la semana actual. La fecha visible como **Encontrada el** es el día en que la oferta entró a tu bandeja, no necesariamente su fecha original de publicación. Esta fecha siempre está disponible; cuando una fuente también proporciona la fecha de publicación, se muestra en una etiqueta aparte.

Cada día se ordena por mayor porcentaje de coincidencia con el perfil y, en caso de empate, por la incorporación más reciente. Las ofertas se guardan una sola vez por usuario: si el mismo enlace o una vacante con la misma huella normalizada (título, empresa y ubicación) vuelve a aparecer en una búsqueda posterior de la semana, conserva el primer día y no se repite en otro. Al comenzar una nueva semana, una oferta que vuelva a encontrarse puede entrar en la bandeja de esa semana.

El campo opcional `jobs.published_at` se conserva para las fuentes que entregan esa información, pero el filtro diario no depende de él. Si aún no aplicaste la actualización anterior, ejecuta `alembic upgrade head`; esta migración agrega el campo sin eliminar ofertas.

## Fuente opcional: Jooble Colombia

Jooble ya está integrado en **Buscar**. Para habilitarlo, solicita una clave desde el portal oficial de [Jooble Colombia](https://co.jooble.org/api/about) y agrega `JOOBLE_API_KEY=tu_clave` a `backend/.env`; no la pongas en el frontend ni en el repositorio. Reinicia el backend. Sin la clave, la opción aparece deshabilitada con instrucciones. Cada ejecución agrupa los cargos del perfil en una sola solicitud a la API.

La documentación de Jooble consultada indica claves por país y una cuota gratuita total de 500 solicitudes por clave. Confirma el plan y los términos vigentes antes de abrir el servicio a varios usuarios. Esta fuente es una alternativa de ofertas; **no extrae LinkedIn**.

## Alertas de LinkedIn por Gmail

La fuente **LinkedIn (alertas de Gmail)** usa OAuth 2.0 y Gmail API; no visita ni automatiza el muro de LinkedIn. Para habilitarla:

1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/), activa Gmail API y crea un cliente OAuth de tipo **Aplicación web**. Registra como URI de redirección autorizada la dirección exacta configurada en `GOOGLE_OAUTH_REDIRECT_URI` (en local: `http://localhost:8000/gmail/oauth/callback`). Configura la pantalla de consentimiento y agrega como usuarios de prueba a las cuentas que usarán el proyecto.
2. Usa un buzón Gmail dedicado solo a alertas de LinkedIn. Si LinkedIn envía las alertas a otro buzón, reenvíalas al dedicado. En Gmail, crea un filtro desde un correo real de alerta y asígnale una etiqueta. No es necesario que la etiqueta tenga un nombre específico.
3. Copia las variables `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` y `GOOGLE_OAUTH_REDIRECT_URI` desde `backend/.env.example` a `backend/.env`; no compartas ni publiques el secreto. Reinicia el backend, inicia sesión en Nexo Laboral, conecta Gmail y selecciona la etiqueta creada.

La aplicación solicita `gmail.readonly` (además de `openid` y `email` para identificar la cuenta), cifra el refresh token con `ENCRYPTION_KEY` y guarda una conexión por usuario. Las llamadas de lectura usan la etiqueta seleccionada y el filtro `from:linkedin.com`; antes de importar, la app también valida el remitente, el asunto y que el enlace apunte a una vacante de LinkedIn. Solo consulta mensajes de los últimos 7 días (máximo 50 por búsqueda). Al desconectar, intenta revocar el token de Google y elimina la credencial local.

**Límite de permiso:** aunque el código consulta únicamente una etiqueta, `gmail.readonly` autoriza técnicamente a la aplicación a leer todo el buzón. La etiqueta no reduce el alcance OAuth. Por eso se recomienda un Gmail dedicado y no conectar un correo personal. Google clasifica este scope como restringido; almacenar o transmitir datos de Gmail en un servidor puede requerir una evaluación de seguridad. Además, en una aplicación externa en modo de prueba, Google puede hacer caducar los refresh tokens después de 7 días. Consulta la [clasificación de scopes de Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes) y la [documentación de expiración de refresh tokens](https://developers.google.com/identity/protocols/oauth2#expiration).

## Magneto Empleo: beta personal

Magneto se consulta mediante rutas públicas con formato `/co/trabajos/buscar/loc-{ciudad}-co/{cargo}`. Playwright abre Chromium headless en un contexto temporal sin inicio de sesión ni perfil persistente; usa un solo navegador por lote y consulta los cargos secuencialmente con dos segundos entre ellos. El scraper lee el `publishDate` asociado al ID de cada oferta en los datos embebidos del listado y solo conserva publicaciones de hasta cinco días (120 horas). Ofertas sin fecha asociable o con más antigüedad se excluyen; no se visitan páginas de detalle ni se requiere migración de base de datos. El filtro aplica a búsquedas nuevas: las ofertas Magneto que ya estaban guardadas no se borran automáticamente. Instala el navegador ejecutando `python -m playwright install chromium` después de `pip install -r requirements.txt`. Si Chromium no está instalado o Magneto responde HTTP 403, 429 o 500, la fuente se detiene sin reintentos y conserva los resultados previos del lote. Se guardan campos breves de las tarjetas y el enlace original. La puntuación no incluye el texto completo de requisitos, así que hay que revisar la vacante en Magneto antes de postularse.

Esta integración es una prueba personal de bajo volumen, no una declaración de que Magneto la autorice. Su reglamento publicado restringe copiar o distribuir contenidos; el uso familiar o no comercial no elimina por sí solo esas condiciones. Si Magneto solicita detener la extracción, hay que deshabilitar la fuente. Para uso sostenido, solicita permiso por escrito o acceso a su API empresarial.

## Seguridad antes de publicar

- Los archivos `.env` originales fueron retirados intencionalmente; el ZIP solo trae plantillas. Las credenciales incluidas en el archivo original deben considerarse expuestas: rota la contraseña de base de datos, `SECRET_KEY`, `ENCRYPTION_KEY` y cualquier clave externa que hubiera sido real. Al cambiar `ENCRYPTION_KEY`, las claves de IA y los refresh tokens Gmail cifrados con la clave antigua no se podrán descifrar; vuelve a guardar las claves y reconecta Gmail.
- No subas `.env`, bases de datos ni credenciales al control de versiones. El `.gitignore` ya los excluye.
- Cambia `CORS_ORIGINS` a los dominios HTTPS exactos de producción. No uses comodines con credenciales.
- Sirve la aplicación detrás de HTTPS, usa secretos gestionados por el entorno de despliegue y configura copias de seguridad protegidas.
- El token de acceso ahora se conserva en `sessionStorage` y desaparece al cerrar la pestaña/sesión. La app debe desplegarse en un origen confiable; protege siempre frente a XSS y no insertes contenido remoto como HTML.
- La API incluye cabeceras de seguridad, validación de secretos, límites en listas y campos de perfil y una duración de token configurable (5–1440 minutos).

## Comprobaciones

Desde `backend`: `python -m unittest discover -s tests -v`. Desde `frontend`: `npm run build` y `npm run lint`. El linter puede mostrar advertencias existentes de hooks React en `AIKeys.jsx` y `Jobs.jsx`; no son errores de compilación.


## Nombre y foto en el menú lateral

El nombre mostrado en el menú se toma de **Mi perfil → Nombre completo**; el correo queda como dato secundario. Puedes subir, reemplazar o quitar una foto desde la parte superior de **Mi perfil**. Se aceptan JPG, PNG y WebP de hasta 2 MB; el backend valida el contenido real, limita las dimensiones y convierte la imagen a WebP de hasta 512 × 512 antes de guardarla.

La foto se almacena como `BYTEA` en la fila del perfil de PostgreSQL, no en una carpeta del servidor ni en un servicio externo. Así queda incluida en las copias de seguridad de la base de datos. Esta actualización agrega la columna nullable `profiles.avatar_data`; después de copiar los archivos, actualiza la dependencia con `pip install -r requirements.txt`, ejecuta `alembic upgrade head` desde `backend` y reinicia la API. La migración no modifica los perfiles existentes ni requiere cambios en `.env`.

## Recuperación de contraseña

El login incluye recuperación por correo con enlace de un solo uso y vencimiento. Para configurar SMTP, aplicar la migración de tokens y desplegar los cambios, sigue [RECUPERAR_PASSWORD.md](RECUPERAR_PASSWORD.md).
