#!/usr/bin/env python3
"""Exporta TODO lo generado en la app de Conxemar a una carpeta local. Descarga MANUAL.

Solo LEE de la base 'conxemar' de bmp-iberica: no modifica ni borra nada, y no se programa solo.
Hay que ejecutarlo a mano, con la sesión de gcloud de un Propietario del proyecto:

    gcloud auth login            (si la sesión ha caducado)
    python3 exportar_datos.py                      -> carpeta exportacion_AAAAMMDD_HHMM/
    python3 exportar_datos.py --salida mi_carpeta  -> carpeta con otro nombre

Genera (CSV para Excel en español: separador ';', UTF-8 con BOM):
    leads.csv, notas.csv, expositores_anadidos.csv, visitas_por_usuario.csv, usuarios.csv,
    fotos/ (JPG, incluidas las tarjetas de contacto de los leads) + fotos.csv, datos_completos.json (copia sin fotos) y LEEME_exportacion.txt

IMPORTANTE: la carpeta contiene datos personales de contactos. Guárdala donde corresponda y
NUNCA la subas al repositorio (exportacion_*/ está en .gitignore).
"""
import argparse, base64, csv, datetime, json, os, re, subprocess, sys, unicodedata, urllib.error, urllib.parse, urllib.request

PROYECTO = "bmp-iberica"
BASE = "conxemar"
DOCS = "https://firestore.googleapis.com/v1/projects/%s/databases/%s/documents" % (PROYECTO, BASE)

# Mismas etiquetas que la app
MOM = {"obra": "Obra en curso", "proy": "Proyecto 6 a 12 meses", "info": "Solo información"}
ZONA = {"gal": "Galicia", "esp": "Resto de España", "pt": "Portugal", "ext": "Extranjero"}
OWN = {"garmo": "Garmo", "group": "BMP Group"}
EMP = {"bmp": "BMP Ibérica", "repro": "Grupo Repro", "campisa": "Campisa Ibérica"}
ACC = {"llamada": "Llamada", "email": "Email", "visita": "Visita presencial"}
SEG = {"A": "Competencia", "B": "Prescriptor", "C": "Distribuidor", "D": "Cliente final"}


def token():
    t = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
    if not t:
        sys.exit("No hay sesión de gcloud. Ejecuta primero: gcloud auth login")
    return t


TOK = token()
HDR = {"Authorization": "Bearer " + TOK, "x-goog-user-project": PROYECTO}


def get(url):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        sys.exit("Error %s leyendo %s: %s" % (e.code, url, e.read().decode()[:300]))


def valor(v):
    """Convierte un valor de Firestore (REST) en un valor normal de Python."""
    (tipo, x), = v.items()
    if tipo == "stringValue" or tipo == "timestampValue" or tipo == "referenceValue":
        return x
    if tipo == "integerValue":
        return int(x)
    if tipo == "doubleValue":
        return float(x)
    if tipo == "booleanValue":
        return x
    if tipo == "nullValue":
        return None
    if tipo == "arrayValue":
        return [valor(i) for i in x.get("values", [])]
    if tipo == "mapValue":
        return {k: valor(i) for k, i in x.get("fields", {}).items()}
    return x


def doc(d):
    r = {k: valor(v) for k, v in d.get("fields", {}).items()}
    r["_id"] = d["name"].split("/")[-1]
    return r


def coleccion(ruta):
    """Lee todos los documentos de una colección (paginando)."""
    salida, pagina = [], ""
    while True:
        url = "%s/%s?pageSize=300%s" % (DOCS, ruta, ("&pageToken=" + urllib.parse.quote(pagina)) if pagina else "")
        d = get(url)
        salida += [doc(x) for x in d.get("documents", [])]
        pagina = d.get("nextPageToken", "")
        if not pagina:
            return salida


def slug(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))


def seguro(s, n=60):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", slug(s))[:n] or "sin_nombre"


def fecha(iso):
    return (iso or "")[:16].replace("T", " ")


def csv_out(ruta, cabecera, filas):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(cabecera)
        w.writerows(filas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", help="carpeta de destino (por defecto exportacion_AAAAMMDD_HHMM)")
    a = ap.parse_args()
    salida = a.salida or "exportacion_" + datetime.datetime.now().strftime("%Y%m%d_%H%M")
    if os.path.exists(salida):
        sys.exit("La carpeta '%s' ya existe. No sobrescribo nada: elige otra con --salida." % salida)
    os.makedirs(os.path.join(salida, "fotos"))

    print("Leyendo la base '%s' de %s (solo lectura)..." % (BASE, PROYECTO))
    catalogo = get(DOCS + "/config/catalog")
    cat = doc(catalogo) if catalogo else {}
    prods = {p["k"]: p["n"] for p in cat.get("prods", [])}
    T = json.loads(cat["Tjson"]) if cat.get("Tjson") else []
    # clave de expositor del catálogo -> (nombre, stand), igual que la calcula la app
    exp = {slug(r[1]) + "_" + slug(r[2]): (r[1], r[2]) for r in T}

    leads = coleccion("leads")
    notas = coleccion("notes")
    anad = coleccion("expositores")
    for c in anad:
        exp["c_" + c["_id"]] = (c.get("name", ""), c.get("stand", ""))
    for l in leads:
        exp["l_" + l["_id"]] = ("Tarjeta de contacto: " + (l.get("empresa") or "lead"), "")
    fidx = coleccion("photoidx")
    usuarios = coleccion("users")
    allowed = coleccion("allowed")
    visitas = {}
    for u in usuarios:
        v = get("%s/users/%s/private/visits" % (DOCS, urllib.parse.quote(u["_id"], safe="")))
        visitas[u["_id"]] = doc(v).get("keys", {}) if v else {}

    nombre = {u["_id"]: u.get("name", "") for u in usuarios}
    correo = {u["_id"]: u.get("email", "") for u in usuarios}
    quien = lambda uid: nombre.get(uid) or uid or ""

    # Último acceso y proveedor (Firebase Authentication)
    acceso = {}
    try:
        req = urllib.request.Request(
            "https://identitytoolkit.googleapis.com/v1/projects/%s/accounts:query" % PROYECTO,
            method="POST", data=json.dumps({"returnUserInfo": True, "limit": "500"}).encode(),
            headers=dict(HDR, **{"Content-Type": "application/json"}))
        for u in json.loads(urllib.request.urlopen(req).read()).get("userInfo", []):
            ms = int(u.get("lastLoginAt", "0") or 0) / 1000
            acceso[u["localId"]] = (datetime.datetime.fromtimestamp(ms).strftime("%Y-%m-%d %H:%M") if ms else "",
                                    ",".join(p["providerId"] for p in u.get("providerUserInfo", [])))
    except Exception:
        pass

    # --- leads.csv
    filas = []
    for l in sorted(leads, key=lambda x: x.get("ts", "")):
        filas.append([fecha(l.get("ts")), quien(l.get("by")), correo.get(l.get("by"), ""), l.get("empresa", ""),
                      l.get("nombre", ""), l.get("cargo", ""), l.get("tel", ""), l.get("mail", ""),
                      " + ".join(prods.get(k, k) for k in l.get("int", [])),
                      " + ".join(EMP.get(k, k) for k in l.get("emp", [])),
                      MOM.get(l.get("mom"), ""), ZONA.get(l.get("zona"), ""), SEG.get(l.get("seg"), ""),
                      OWN.get(l.get("own"), ""), ACC.get(l.get("accion"), ""), l.get("fecha", ""), l.get("nota", ""),
                      quien(l.get("updBy")) if l.get("updBy") and l.get("updBy") != l.get("by") else "",
                      fecha(l.get("upd")), l["_id"]])
    csv_out(os.path.join(salida, "leads.csv"),
            ["Fecha captura", "Lead creado por", "Email del creador", "Empresa", "Contacto", "Cargo", "Teléfono",
             "Email", "Productos", "Interés en (empresa)", "Momento", "Zona", "Segmento", "Gestiona",
             "Acción programada", "Fecha de la acción", "Nota", "Editado por", "Última edición", "Id"], filas)

    # --- notas.csv
    filas = []
    for n in sorted(notas, key=lambda x: (exp.get(x.get("key"), ("", ""))[0], x.get("ts", ""))):
        e = exp.get(n.get("key"), (n.get("key", ""), ""))
        filas.append([e[0], e[1], n.get("text", ""), quien(n.get("by")), correo.get(n.get("by"), ""),
                      fecha(n.get("ts")), "sí" if n.get("updBy") and n.get("upd") != n.get("ts") else "", n["_id"]])
    csv_out(os.path.join(salida, "notas.csv"),
            ["Expositor", "Stand", "Nota", "Nota creada por", "Email del autor", "Fecha", "Editada", "Id"], filas)

    # --- expositores_anadidos.csv
    filas = [[c.get("name", ""), SEG.get(c.get("seg"), ""), c.get("stand", ""), c.get("town", ""),
              {True: "Galicia", False: "Fuera de Galicia"}.get(c.get("gal"), "No sé"), c.get("desc", ""),
              c.get("acc", ""), quien(c.get("by")), fecha(c.get("ts")), c["_id"]] for c in anad]
    csv_out(os.path.join(salida, "expositores_anadidos.csv"),
            ["Empresa", "Segmento", "Stand", "Localidad", "Zona", "Qué hace", "Qué hacer con ellos", "Añadido por", "Fecha", "Id"], filas)

    # --- visitas_por_usuario.csv
    filas = []
    for uid, ks in visitas.items():
        for k, si in sorted(ks.items()):
            if si:
                e = exp.get(k, (k, ""))
                filas.append([quien(uid), correo.get(uid, ""), e[0], e[1]])
    csv_out(os.path.join(salida, "visitas_por_usuario.csv"), ["Usuario", "Email", "Expositor visitado", "Stand"], filas)

    # --- usuarios.csv
    admins = {a["_id"] for a in allowed if a.get("admin")}
    filas = [[u.get("name", ""), u.get("email", ""), u["_id"], "sí" if (u.get("email", "").lower() in admins) else "",
              acceso.get(u["_id"], ("", ""))[0], acceso.get(u["_id"], ("", ""))[1]] for u in usuarios]
    csv_out(os.path.join(salida, "usuarios.csv"),
            ["Nombre", "Email", "Id de usuario", "Administrador", "Último acceso", "Método de acceso"], filas)

    # --- fotos
    filas, hechas = [], 0
    for p in sorted(fidx, key=lambda x: x.get("ts", "")):
        d = get(DOCS + "/photodata/" + urllib.parse.quote(p["_id"], safe=""))
        data = doc(d).get("data", "") if d else ""
        if not data:
            continue
        e = exp.get(p.get("key"), (p.get("key", ""), ""))
        archivo = "%s_%s_%s.jpg" % (seguro(e[0]), (p.get("ts") or "")[:10], p["_id"][-4:])
        with open(os.path.join(salida, "fotos", archivo), "wb") as f:
            f.write(base64.b64decode(data.split(",", 1)[-1]))
        filas.append([archivo, e[0], e[1], quien(p.get("by")), fecha(p.get("ts"))])
        hechas += 1
    csv_out(os.path.join(salida, "fotos.csv"), ["Archivo", "Asociada a", "Stand", "Foto creada por", "Fecha"], filas)

    # --- copia completa (sin las imágenes, que van en fotos/)
    with open(os.path.join(salida, "datos_completos.json"), "w", encoding="utf-8") as f:
        json.dump({"exportado": datetime.datetime.now().isoformat(timespec="seconds"), "proyecto": PROYECTO, "base": BASE,
                   "leads": leads, "notas": notas, "expositores_anadidos": anad, "fotos_indice": fidx, "usuarios": usuarios,
                   "accesos_manuales": allowed, "visitas": visitas}, f, ensure_ascii=False, indent=1)

    resumen = ("Exportación de la app de Conxemar 2026\nFecha: %s\nProyecto: %s | Base: %s\n\n"
               "Leads: %d\nNotas: %d\nExpositores añadidos a mano: %d\nFotos: %d\nUsuarios: %d\nMarcas de visitado: %d\n\n"
               "Contiene datos personales de contactos. Guárdala donde corresponda y no la subas al repositorio.\n") % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), PROYECTO, BASE, len(leads), len(notas), len(anad), hechas,
        len(usuarios), sum(1 for ks in visitas.values() for s in ks.values() if s))
    open(os.path.join(salida, "LEEME_exportacion.txt"), "w", encoding="utf-8").write(resumen)
    print("\n" + resumen + "Carpeta: " + os.path.abspath(salida))


if __name__ == "__main__":
    main()
