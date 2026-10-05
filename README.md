# Conxemar BMP Group: puesta en marcha (GitHub Pages + Firebase)

La app es una web estática (GitHub Pages) que guarda los datos en Firestore (Google Cloud) y deja entrar solo a las personas autorizadas, con su cuenta de Google. Sirve igual para el equipo de BMP Group y para el de Garmo.

## Qué hay en esta carpeta

| Archivo | Para qué | ¿Se sube a GitHub? |
|---|---|---|
| `index.html` | La app | Sí |
| `manifest.webmanifest`, `sw.js` | Instalar en pantalla de inicio y abrir sin conexión | Sí |
| `firestore.rules` | Reglas de seguridad de la base de datos | Sí (o solo se pegan en Firebase) |
| `catalogo.json` | Expositores, productos y textos del stand (estrategia comercial) | **No.** Está en `.gitignore`. Se carga desde la app |

La web de GitHub Pages es pública. Por eso `index.html` no lleva ningún dato comercial: todo se descarga de la base de datos después de iniciar sesión.

## Pasos (unos 30 minutos)

### 1. Crear el proyecto de Firebase
1. Entra en https://console.firebase.google.com con la cuenta de BMP.
2. **Añadir proyecto** y ponle nombre, por ejemplo `bmp-conxemar-2026`. Desactiva Google Analytics.
3. Recomendado: proyecto **nuevo**, no el `bmp-iberica` del CRM. Las reglas de Firestore se aplican a toda la base y no hay que arriesgarse a tocar el CRM.

### 2. Activar el inicio de sesión con Google
1. **Build > Authentication > Comenzar > Google > Activar**. Elige el correo de soporte y guarda.
2. **Authentication > Settings > Authorized domains > Add domain**: añade `TU-USUARIO.github.io` (el dominio donde publicarás).

### 3. Crear la base de datos
1. **Build > Firestore Database > Crear base de datos**.
2. Región **europe-west** (UE, por los datos personales de los contactos). No se puede cambiar después.
3. Modo **producción**.

### 4. Publicar las reglas de seguridad
1. En Firestore, pestaña **Reglas**: pega el contenido de `firestore.rules` y pulsa **Publicar**.
2. Si usas la CLI (`npm i -g firebase-tools`, `firebase login`, `firebase deploy --only firestore:rules`), también vale.

### 5. Crear el primer administrador
Sin esto nadie puede entrar. En Firestore, pestaña **Datos**:
1. **Iniciar colección** con ID `allowed`.
2. ID del documento: **tu correo de Google, entero en minúsculas** (por ejemplo `m.aliena@bmpiberica.com`).
3. Campo `admin`, tipo booleano, valor `true`.

### 6. Copiar la configuración web
1. **Configuración del proyecto > Tus apps > Web (`</>`)**, registra una app y copia el bloque `firebaseConfig`.
2. En `index.html`, sustituye los `PEGAR_AQUI` de `FIREBASE_CONFIG` por `apiKey`, `authDomain`, `projectId` y `appId`.
3. Esas claves son públicas por diseño. La seguridad la dan las reglas del paso 4.

### 7. Publicar en GitHub Pages
1. Crea un repositorio (por ejemplo `conxemar-bmp`) y sube `index.html`, `manifest.webmanifest`, `sw.js`, `firestore.rules` y `.gitignore`. **No subas `catalogo.json`.**
2. **Settings > Pages > Deploy from a branch > main / (root)**.
3. La dirección será `https://TU-USUARIO.github.io/conxemar-bmp/`. Debe coincidir con el dominio autorizado en el paso 2.

### 8. Primer arranque
1. Abre la dirección, pulsa **Entrar con Google** con tu cuenta.
2. Ve a **Stand > Equipo y catálogo**. Elige `catalogo.json` para cargar los 67 expositores y los textos.
3. En la misma sección, **añade los correos del equipo de BMP y de Garmo** (cuentas de Google, en minúsculas). Marca "Administrador" solo para quien deba gestionar accesos o borrar lo de otros.
4. Cada persona abre la dirección, entra con Google y, en el móvil, **Añadir a pantalla de inicio**.

## Qué garantizan las reglas (en el servidor)
- Solo entran correos que estén en `allowed`.
- "Creado por" siempre es quien escribe y no se puede cambiar.
- Solo el autor (o un administrador) borra sus leads, notas, fotos y expositores. Las notas solo las edita su autor.
- "Visitado" de cada persona es privado: nadie más lo puede leer.
- Solo los administradores cambian el catálogo y la lista de accesos.

## Comprobación antes de la feria
1. Con tu cuenta: crea un lead y una nota. Deben aparecer con tu nombre.
2. Con una cuenta de prueba **no** añadida a `allowed`: debe salir "Todavía no tienes acceso".
3. Añade esa cuenta como miembro: debe ver el lead, no poder borrarlo, y su "visitado" no debe afectarte.
4. Pon el móvil en modo avión, crea un lead, vuelve a conectar: debe sincronizarse.

## Lo que hay que saber
- **Sin conexión:** la app y los datos se guardan en el móvil. Los cambios se envían solos al volver la red. La primera vez hay que abrirla con conexión.
- **Coste:** el plan gratuito de Firebase (Spark) cubre de sobra un equipo pequeño durante una feria. Revisa las cuotas si se suben muchas fotos.
- **Fotos:** se guardan reducidas (unos 60 a 100 KB cada una) dentro de la base de datos, visibles para todo el equipo.
- **Cuentas:** todo el mundo necesita una cuenta de Google (Gmail o de empresa).
- **Protección de datos:** hay datos personales de contactos. La base está en la UE y el acceso está limitado a las personas autorizadas. Conviene dejar constancia de quién tiene acceso y borrar los datos cuando deje de hacer falta.
- **Actualizar la app:** edita `index.html` y súbelo. El service worker toma la versión nueva en la siguiente apertura con conexión.
- **Marcha atrás:** en Firebase, quitar el correo de `allowed` corta el acceso de esa persona al instante.
