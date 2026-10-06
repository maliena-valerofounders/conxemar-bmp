#!/usr/bin/env python3
"""Valida y publica firestore.rules SOLO en la base 'conxemar' de bmp-iberica.

Se hace por API y no desde la consola de Firebase porque ahí el selector de base de datos
arranca en '(default)': pegar las reglas en la base equivocada es fácil y no avisa.

Uso:  gcloud auth login   (una vez)   y después   python3 publicar_reglas.py
"""
import json, subprocess, urllib.request, urllib.error, sys

PROYECTO = "bmp-iberica"
BASE = "conxemar"

tok = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
if not tok:
    sys.exit("No hay sesión de gcloud. Ejecuta: gcloud auth login")
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json", "x-goog-user-project": PROYECTO}

def llamar(metodo, url, cuerpo):
    req = urllib.request.Request(url, method=metodo, headers=H, data=json.dumps(cuerpo).encode())
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        sys.exit("Error %s: %s" % (e.code, e.read().decode()[:600]))

reglas = open("firestore.rules", encoding="utf-8").read()
fuente = {"source": {"files": [{"name": "firestore.rules", "content": reglas}]}}
base = "https://firebaserules.googleapis.com/v1/projects/" + PROYECTO

problemas = llamar("POST", base + ":test", fuente).get("issues")
if problemas:
    sys.exit("Las reglas tienen errores, no se publica nada: " + json.dumps(problemas))
conjunto = llamar("POST", base + "/rulesets", fuente)["name"]
# Para bases con nombre el release es cloud.firestore/<base> (SIN el segmento "database/": la API lo acepta pero Firestore lo ignora).
nombre = "projects/%s/releases/cloud.firestore/%s" % (PROYECTO, BASE)
try:
    llamar("PATCH", "https://firebaserules.googleapis.com/v1/" + nombre, {"release": {"name": nombre, "rulesetName": conjunto}})
except SystemExit:
    llamar("POST", base + "/releases", {"name": nombre, "rulesetName": conjunto})
print("Publicadas en la base '%s' de %s: %s" % (BASE, PROYECTO, conjunto))
