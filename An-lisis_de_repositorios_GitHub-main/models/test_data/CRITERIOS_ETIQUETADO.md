# Criterios de etiquetado del conjunto de prueba

Definidos **antes** de revisar los hallazgos. El etiquetado se hace a ciegas: sin ver la
predicción del modelo.

## Pregunta que responde cada etiqueta

> Si este repositorio estuviera en producción y alguien copiara este valor,
> ¿obtendría acceso a algo o descubriría un secreto?

## 1 = Credencial real

- Valor literal asignado a un campo de credencial (contraseña, token, clave, secreto) en
  código, configuración, scripts o dotfiles, **aunque sea débil** (`hunter22`, `admin123`).
- Contraseñas por defecto de una aplicación o plantilla que se usarían tal cual al
  desplegarla (p. ej. `MYSQL_ROOT_PASSWORD=db-57xsl` en un `docker-compose.yml`).
- Tokens o claves con formato de proveedor y valor no reconocible como ejemplo.
- Claves privadas (encabezado `-----BEGIN ... PRIVATE KEY-----`) en un archivo de claves.
- Hashes de contraseñas (htpasswd, shadow, volcados SQL).

## 0 = Falso positivo

- **Placeholders**: `changeme`, `your_password`, `<token>`, `${VAR}`, `{{ var }}`, `xxxx`, `****`,
  `REPLACE_ME`, valores vacíos o descriptivos (`password`, `secret`, `example`).
- **Valores de ejemplo conocidos**: `AKIAIOSFODNN7EXAMPLE`, `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`,
  token de jwt.io, valores secuenciales (`1234567890abcdef`, `abcdefgh...`).
- **Datos de prueba**: valores en archivos de pruebas, `testdata/`, `fixtures/` o `__mocks__/`
  creados para probar un detector o una función (aunque parezcan aleatorios).
- **Documentación**: valores en `.md`, `.adoc`, `.rst` o comentarios que explican cómo configurar
  algo, y prosa que contiene la palabra "password" o "token".
- **Código sin secreto**: referencias a otra variable, lecturas de entorno, llamadas a funciones,
  nombres de campo de formularios o traducciones (`password=Contraseña`).

## Casos dudosos

Se anotan en la columna `note` con el motivo. Se aplica la regla general: si el valor
funcionaría tal cual en un despliegue real, es 1; si es evidente que alguien debe reemplazarlo
o que solo existe para pruebas o documentación, es 0.
