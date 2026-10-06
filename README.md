# Conxemar BMP Group: app del equipo

Misma arquitectura que el CRM, todo dentro del proyecto de Google Cloud **`bmp-iberica`**:

| Parte | Dónde |
|---|---|
| Web | Cloud Run, servicio `conxemar-app`, `europe-west1` (nginx con `index.html`) |
| Datos | Firestore, base **`conxemar`** (`europe-southwest1`), con protección contra borrado |
| Inicio de sesión | Firebase Authentication con Google, en el mismo proyecto |
| Código | GitHub, repositorio `conxemar-bmp` |

Dirección: https://conxemar-app-643465692981.europe-west1.run.app

A diferencia del CRM, aquí el navegador habla directamente con Firestore y la seguridad la ponen las **reglas** (`firestore.rules`), no un servidor.

## Quién entra
- **Con Google:** cualquier cuenta con correo **@bmpiberica.com** o **@comercialgarmo.com** (correo verificado).
- **Con enlace por correo** (para quien no tenga cuenta de Google): solo **@comercialgarmo.com**. La persona escribe su correo, recibe un enlace de un solo uso y, al abrirlo, la app le pide su nombre y apellido, que saldrá en sus leads y notas. Si abre el enlace en otro dispositivo, la app le vuelve a pedir el correo.
- Misma cuenta en varios dispositivos: ve todo lo suyo. No se sincronizan los borradores sin guardar ni las casillas de la pestaña Stand.
- La colección `allowed` solo sirve para excepciones de otros dominios (documento con el correo en minúsculas) y para marcar administradores (`admin: true`).
- Limitación: el nombre lo escribe cada persona, así que no es a prueba de suplantación entre compañeros.

## Qué garantizan las reglas (probadas con 25 casos en el simulador de Firebase)
- "Creado por" (`by`) siempre es quien escribe y no se puede cambiar.
- Solo el autor, o un administrador, borra lo suyo. Las notas solo las edita su autor.
- "Visitado" de cada persona es privado (`users/{uid}/private/visits`).
- Solo los administradores cambian el catálogo y la lista de accesos.
- Todo lo que no está listado, cerrado.

## Desplegar la web
```bash
gcloud run deploy conxemar-app --source . --project bmp-iberica --region europe-west1 \
  --max-instances 3 --min-instances 0 --memory 256Mi --cpu 1 --no-invoker-iam-check --quiet
```
`--no-invoker-iam-check` es lo mismo que usa `crm-leads` para ser público. La política de la organización no permite dar `allUsers` como invocador. La app se protege con su propio inicio de sesión.

Si la dirección cambia, hay que autorizarla en Firebase: Authentication > Configuración > Dominios autorizados.

## Publicar las reglas
```bash
python3 publicar_reglas.py
```
Valida y publica **solo en la base `conxemar`**. No uses el editor de la consola de Firebase: su selector arranca en `(default)`.

## Descarga de los datos (manual, después de la feria)
Todo lo generado en la app vive en la base `conxemar`. El botón "Exportar" de Leads solo saca los leads (CSV). Para llevarse **todo**, un Propietario del proyecto ejecuta a mano:
```bash
gcloud auth login            # solo si la sesión ha caducado
python3 exportar_datos.py    # crea la carpeta exportacion_AAAAMMDD_HHMM/
```
No se programa ni se lanza solo, y **solo lee**: no modifica ni borra nada. Genera, en CSV para Excel en español (`;`, UTF-8 con BOM): `leads.csv`, `notas.csv`, `expositores_anadidos.csv`, `visitas_por_usuario.csv`, `usuarios.csv`, `fotos.csv`, la carpeta `fotos/` con los JPG, `datos_completos.json` (copia completa sin las imágenes) y `LEEME_exportacion.txt` con los totales.
La carpeta contiene datos personales de contactos: guárdala donde corresponda y no la subas al repositorio (`exportacion_*/` está en `.gitignore`).

## Catálogo (privado)
Los expositores, los productos y los textos del stand NO están en el repositorio ni en la web: viven en Firestore (`config/catalog`) y solo los ven las personas autorizadas. El archivo `catalogo.json` está en `.gitignore`. Un administrador lo carga desde la app (pestaña Stand > Equipo y catálogo).

Firestore no admite arrays dentro de arrays: la lista de expositores se guarda como texto (`Tjson`).

## Pendiente
- Despliegue automático desde GitHub (como `desplegar.yml` del CRM). La federación de identidad del CRM solo acepta repositorios de `ivanhuertasg`: hay que mover este repositorio a su cuenta o ampliar la condición.
- El proyecto `bmp-conxemar-2026` (Firebase) quedó sin uso tras pasar todo a `bmp-iberica`. Decidir si se borra.
- Copia de seguridad programada de la base `conxemar` (las del CRM la tienen diaria).
