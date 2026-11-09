# Fuentes de empleo: LinkedIn, Jooble y Magneto

## LinkedIn no se conecta por scraping

LinkedIn indica que no permite crawlers, bots u otro software de terceros para raspar o copiar sus servicios. Su acuerdo también prohíbe copiar información obtenida de sus servicios directamente o a través de terceros sin consentimiento. Que una página sea visible sin iniciar sesión no constituye por sí solo autorización para automatizar su extracción. Esta aplicación no consulta el muro, no usa cookies y no automatiza sesiones. [1] [2]

La Job Posting API oficial de LinkedIn está destinada a partners autorizados para publicar vacantes en LinkedIn; no es una API abierta para buscar ofertas. [3]

## Alertas de empleo de LinkedIn por Gmail

Nexo Laboral ofrece una fuente separada para alertas que llegan por correo. Usa OAuth 2.0 y la Gmail API, no automatiza LinkedIn. Cada usuario conecta una cuenta, crea un filtro/etiqueta en Gmail y selecciona esa etiqueta en la interfaz. El servidor cifra el refresh token con `ENCRYPTION_KEY`; el estado OAuth se consume una sola vez y vence en 10 minutos.

En una búsqueda, Gmail API recibe la etiqueta elegida junto con `from:linkedin.com` y `newer_than:7d`; se limita el lote a 50 mensajes. El parser vuelve a validar el dominio del remitente y acepta solo enlaces canónicos a ofertas de empleo de LinkedIn. La etiqueta limita lo que consulta el programa, pero **no limita el permiso OAuth**: `gmail.readonly` permite técnicamente leer todo el buzón y Google lo clasifica como scope restringido. Conecta una cuenta Gmail dedicada exclusivamente a alertas de LinkedIn. Para aplicaciones externas en modo de prueba, los refresh tokens pueden expirar a los 7 días; revisa los requisitos de verificación y evaluación antes de publicar el servicio. [12] [13]

## Jooble Colombia

La aplicación integra Jooble en **Buscar** mediante una clave guardada en `backend/.env`. Agrupa los cargos del perfil en una solicitud, normaliza la respuesta y usa el flujo existente de deduplicación, puntuación y guardado. No requiere migración de base de datos.

Jooble documenta una clave distinta por país, un plan gratuito de 500 solicitudes totales de por vida por clave y HTTP 403 cuando la clave está ausente o es inválida. El portal colombiano describe la API para buscar vacantes y publicar las respuestas en un sitio propio. Si se recibe 403, comprobar que la clave se haya emitido en el portal colombiano, reiniciar el backend y pedir a Jooble que confirme el estado de la clave y el endpoint regional. [4] [5] [6]

## Magneto Empleo: beta personal

La aplicación navega a rutas públicas de búsqueda con formato `/co/trabajos/buscar/loc-{ciudad}-co/{cargo}`. Usa Playwright/Chromium headless en un contexto temporal sin inicio de sesión ni perfil persistente; no visita páginas de detalle ni navega a páginas de resultados con `?`. Un único navegador consulta los cargos secuencialmente, con dos segundos entre rutas. Ante HTTP 403, 429 o 500 detiene la fuente sin reintentos y conserva las ofertas obtenidas antes del error. El `robots.txt` general desautoriza rutas con parámetros y bloquea al user-agent `Scrapy`; la ruta de búsqueda validada no tiene `?`. [7] [8]

El parser toma campos breves de las tarjetas públicas —título, empresa, ubicación y datos de resumen— y guarda el enlace del anuncio original. No descarga descripciones completas ni abre páginas individuales. En una inspección técnica de la búsqueda de Bogotá/Analista (2026-10-23), el estado embebido público del listado contenía un campo `publishDate` ISO ligado al ID de cada oferta; no aparece como texto dentro de las tarjetas. La integración asocia ese ID con el final de la URL y conserva solo publicaciones de hasta 120 horas. Si no puede asociar una fecha válida, excluye la oferta; si el listado deja de exponer fechas, la fuente falla con un aviso en lugar de incorporar ofertas sin verificar. Esta es una observación de implementación sobre la página indicada, no una garantía de una API estable. [9] [11]

El puntaje de coincidencia sigue usando principalmente título y ubicación; las habilidades detalladas pueden no quedar reflejadas. El usuario debe verificar requisitos y postularse en Magneto.

Esta fuente se implementa como beta de bajo volumen para el uso personal/familiar indicado por el usuario. Eso no es una autorización de Magneto ni una conclusión jurídica. El reglamento publicado prohíbe reproducir, copiar o distribuir contenido y limita que terceros se beneficien de la plataforma sin autorización expresa. El uso no comercial o para pocas personas no elimina automáticamente esas condiciones. Para uso sostenido, pedir permiso escrito o acceso a la API empresarial de Magneto. Si Magneto bloquea la fuente o pide detenerla, deshabilitarla. [8] [10]

## Referencias

[1]: https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions?lang=en "LinkedIn Prohibited Software and Extensions"
[2]: https://www.linkedin.com/legal/user-agreement "LinkedIn User Agreement"
[3]: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview?view=li-lts-2026-04 "LinkedIn Job Posting API overview"
[4]: https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation "Jooble REST API Documentation"
[5]: https://help.jooble.org/en/support/solutions/articles/60000922689-how-to-connect-to-the-jooble-rest-api "How to connect to the Jooble REST API"
[6]: https://co.jooble.org/api/about "Jooble REST API Colombia"
[7]: https://www.magneto365.com/robots.txt "Magneto robots.txt"
[8]: https://static.magneto365.com/wordpress/2026/10/docs/reglamento-prestacion-de-servicio-3068.pdf "Reglamento de prestación de servicios de Magneto"
[9]: https://www.magneto365.com/co/trabajos/ofertas-empleo-de-director-servicios-salud "Página pública de resultados Magneto"
[10]: https://empresas.magneto365.com/es-co/soluciones/integraciones-ats-tecnologia "Integraciones empresariales de Magneto"
[11]: https://www.magneto365.com/co/trabajos/buscar/loc-bogota-d.c.-co/analista "Búsqueda pública de Analista en Bogotá"
[12]: https://developers.google.com/workspace/gmail/api/auth/scopes "Gmail API OAuth scopes"
[13]: https://developers.google.com/identity/protocols/oauth2#expiration "Google OAuth refresh token expiration"
