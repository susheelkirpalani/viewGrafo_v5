# server.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime
import json
import networkx as nx
from pyvis.network import Network
import os
import shutil

app = FastAPI()

# --- RUTAS Y DIRECTORIOS ---
BASE = Path(".").resolve()
ARCHIVO_ARBOL = BASE / "arbol_decisiones.json"
TEMPLATES_DIR = BASE / "templates"
STATIC_DIR = BASE / "static"
EXPORTS_DIR = BASE / "exports"

# Aseguramos directorios necesarios (templates y static pueden existir por separado)
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
# exports se crea solo cuando se exporta, pero podemos asegurarlo si se desea:
# EXPORTS_DIR.mkdir(exist_ok=True)

# Estado en memoria (sesión simplificada)
user_path = []  # lista de ids que representan la ruta desde la raíz hasta el nodo actual

# -------------------------
# Utilidades de archivo
# -------------------------
def cargar_arbol():
    if ARCHIVO_ARBOL.exists():
        try:
            return json.loads(ARCHIVO_ARBOL.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def guardar_arbol(data):
    with open(ARCHIVO_ARBOL, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def borrar_arbol():
    if ARCHIVO_ARBOL.exists():
        try:
            ARCHIVO_ARBOL.unlink()
        except Exception:
            pass

# -------------------------
# Utilidades de árbol
# -------------------------
def crear_raiz(texto):
    """Crea la raíz con id P1."""
    raiz = {"id": "P1", "texto": texto, "opciones": []}
    guardar_arbol(raiz)
    return raiz

def buscar_nodo_por_path(arbol, path):
    """Sigue la ruta de IDs y devuelve el nodo objetivo (o la raíz si path vacío)."""
    nodo = arbol
    # Si arbol está vacío o no tiene 'id', devolvemos None
    if not nodo or "id" not in nodo:
        return None
    if not path:
        return nodo
    # Recorremos los ids en path para ubicar el nodo destino
    current = nodo
    for pid in path:
        found = next((o for o in current.get("opciones", []) if o.get("id") == pid), None)
        if not found:
            return current
        current = found
    return current

def generar_id_hijo(parent_id, parent_node):
    """
    Genera un id jerárquico tipo:
    P1 -> P1.1, P1.2...
    """
    hijos = parent_node.get("opciones", [])
    next_index = len(hijos) + 1
    return f"{parent_id}.{next_index}"

def obtener_profundidad(id_str):
    """Calcula profundidad a partir de id (P1 -> 1, P1.1 -> 2, etc.)."""
    return id_str.count('.') + 1

def obtener_rama(arbol, path):
    """
    Devuelve:
    - ramaPrincipal: R1, R2, R3 según primera selección desde la raíz
    - nodoActual: P1, P1.1, P1.2, etc.
    """
    if not path:
        return {"ramaPrincipal": None, "nodoActual": "P1"}  # raíz

    nodo_actual_id = path[-1]
    primera_id = path[0]
    # Si primera_id tiene un punto (por ejemplo P1.2), usamos esa segunda parte como índice de rama
    if '.' in primera_id:
        parts = primera_id.split('.')
        rama_principal = f"R{parts[1]}"
    else:
        rama_principal = "R1"

    return {"ramaPrincipal": rama_principal, "nodoActual": nodo_actual_id}

# -------------------------
# Endpoints y lógica
# -------------------------

# Servir archivos estáticos (css/js)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    idx = BASE / "index.html"
    if idx.exists():
        return HTMLResponse(idx.read_text(encoding="utf-8"))
    return HTMLResponse("<h3>Index no encontrado. Coloca index.html en la raíz del proyecto.</h3>")

@app.get("/iniciar")
def iniciar():
    """Reinicia la sesión del usuario (no borra el archivo del árbol)."""
    global user_path
    user_path = []
    return JSONResponse({"ok": True})

@app.get("/obtener_pregunta_actual")
def obtener_pregunta_actual():
    arbol = cargar_arbol()
    if not arbol:
        return JSONResponse({"existe": False})

    nodo = buscar_nodo_por_path(arbol, user_path)
    if nodo is None:
        return JSONResponse({"existe": False})

    opciones = [
        {
            "id": o["id"],
            "texto": o.get("texto", ""),
            "es_final": o.get("es_final", False),
            "tiene_respuesta": "respuesta" in o
        }
        for o in nodo.get("opciones", [])
    ]
    current_id = nodo.get("id", "P1")
    profundidad = obtener_profundidad(current_id)
    rama_data = obtener_rama(arbol, user_path)

    # progress simple
    MAX_DEPTH = 6
    progress_percent = int(min(100, (profundidad / MAX_DEPTH) * 100))

    # path labels
    path_labels = []
    node_cursor = arbol
    path_labels.append(node_cursor.get("texto", node_cursor.get("id")))
    for pid in user_path:
        found = next((o for o in node_cursor.get("opciones", []) if o.get("id") == pid), None)
        if not found:
            break
        node_cursor = found
        path_labels.append(node_cursor.get("texto", node_cursor.get("id")))

    data = {
        "existe": True,
        "id": nodo.get("id"),
        "texto": nodo.get("texto"),
        "opciones": opciones,
        "tienePadre": len(user_path) > 0,
        "profundidad": profundidad,
        "rama": rama_data["ramaPrincipal"],
        "nodoActual": rama_data["nodoActual"],
        "progressPercent": progress_percent,
        "pathLabels": path_labels
    }
    return JSONResponse(data)

@app.post("/nueva_pregunta")
async def nueva_pregunta(request: Request):
    """
    Soporta:
    - Crear raíz: { "texto": "..." }
    - Agregar subpreguntas: { "subpreguntas": ["a","b"], "ultimas": [false,true] } (ultimas es opcional, lista paralela booleana)
    - Avanzar a subpregunta seleccionada: { "id": "P1.1", "avanzar": true }
    - Guardar respuesta final para opción marcada como es_final: { "id": "P1.2", "respuesta": "..." , "finalizar": true }
    """
    body = await request.json()
    arbol = cargar_arbol()

    # Crear raíz si no existe
    if not arbol:
        texto = body.get("texto")
        if not texto:
            return JSONResponse({"error": "Texto de raíz ausente"}, status_code=400)
        raiz = crear_raiz(texto)
        return JSONResponse({"ok": True, "raiz": raiz})

    # Avanzar a subpregunta seleccionada (navegación)
    if body.get("avanzar"):
        seleccion_id = body.get("id")
        if not seleccion_id:
            return JSONResponse({"error": "Falta id"}, status_code=400)
        nodo_actual = buscar_nodo_por_path(arbol, user_path)
        if nodo_actual is None:
            return JSONResponse({"error": "Nodo actual no encontrado"}, status_code=400)
        if not any(o.get("id") == seleccion_id for o in nodo_actual.get("opciones", [])):
            return JSONResponse({"error": "Id no encontrada entre opciones del nodo actual"}, status_code=400)
        user_path.append(seleccion_id)
        # guardamos (aunque la estructura no cambió), para mantener consistencia
        guardar_arbol(arbol)
        return JSONResponse({"ok": True})

    # Guardar respuesta final para una opción marcada como es_final
    if body.get("finalizar"):
        target_id = body.get("id")
        respuesta = body.get("respuesta", "").strip()
        if not target_id:
            return JSONResponse({"error": "Falta id"}, status_code=400)
        if respuesta == "":
            return JSONResponse({"error": "Respuesta vacía"}, status_code=400)
        # buscar la opción por id en todo el árbol (recorrido DFS)
        encontrado = False

        def buscar_y_guardar(nodo):
            nonlocal encontrado
            if not nodo:
                return False
            for op in nodo.get("opciones", []):
                if op.get("id") == target_id:
                    op["respuesta"] = respuesta
                    op["finalizado"] = True
                    encontrado = True
                    return True
                if buscar_y_guardar(op):
                    return True
            return False

        buscar_y_guardar(arbol)
        if not encontrado:
            return JSONResponse({"error": "Id no encontrada en el árbol"}, status_code=400)
        guardar_arbol(arbol)
        return JSONResponse({"ok": True, "finalizado": True})

    # Agregar subpreguntas (con posibilidad de marcar cada una como última)
    subpregs = body.get("subpreguntas")
    ultimas = body.get("ultimas", [])  # lista booleana paralela
    if subpregs:
        nodo = buscar_nodo_por_path(arbol, user_path)
        if nodo is None:
            return JSONResponse({"error": "Nodo actual no encontrado"}, status_code=400)
        if "opciones" not in nodo:
            nodo["opciones"] = []
        for idx, texto in enumerate(subpregs):
            if not texto or not texto.strip():
                continue
            new_id = generar_id_hijo(nodo["id"], nodo)
            es_final = False
            try:
                es_final = bool(ultimas[idx])
            except Exception:
                es_final = False
            nodo["opciones"].append({"id": new_id, "texto": texto.strip(), "opciones": [], "es_final": es_final})
        guardar_arbol(arbol)
        return JSONResponse({"ok": True})

    return JSONResponse({"ok": False, "msg": "No action performed"})

@app.get("/retroceder")
def retroceder():
    if user_path:
        user_path.pop()
    return JSONResponse({"ok": True})

@app.post("/toggle_es_final")
async def toggle_es_final(request: Request):
    """
    Marca/desmarca una opción como es_final
    body: { "id": "P1.2", "es_final": true }
    """
    body = await request.json()
    target_id = body.get("id")
    if not target_id:
        return JSONResponse({"error": "Falta id"}, status_code=400)
    arbol = cargar_arbol()
    changed = False

    def buscar_y_toggle(nodo):
        nonlocal changed
        if not nodo:
            return False
        for op in nodo.get("opciones", []):
            if op.get("id") == target_id:
                op["es_final"] = bool(body.get("es_final", True))
                guardar_arbol(arbol)
                changed = True
                return True
            if buscar_y_toggle(op):
                return True
        return False

    buscar_y_toggle(arbol)
    if not changed:
        return JSONResponse({"error": "Id no encontrada"}, status_code=400)
    return JSONResponse({"ok": True})

@app.get("/ver_grafo", response_class=HTMLResponse)
def ver_grafo():
    """
    Genera una vista HTML del grafo usando pyvis y devuelve la página.
    """
    arbol = cargar_arbol()
    if not arbol:
        return HTMLResponse("<h3>❌ No existe el árbol. Crea primero la pregunta raíz.</h3>")

    # Construir grafo con networkx
    G = nx.DiGraph()

    def recorrer(nodo, padre=None):
        # label corto (texto) y nodos únicos por id
        G.add_node(nodo["id"], label=nodo.get("texto", nodo.get("id")))
        if padre:
            G.add_edge(padre, nodo["id"])
        for hijo in nodo.get("opciones", []):
            recorrer(hijo, nodo["id"])

    recorrer(arbol)

    net = Network(height="600px", width="100%", directed=True)
    net.from_nx(G)
    net.show_buttons(filter_=["physics"])

    salida = TEMPLATES_DIR / "grafo_dinamico.html"
    net.save_graph(str(salida))
    html = salida.read_text(encoding="utf-8")

    # Insertamos (si se desea) un botón 'Borrar todo' visible dentro del HTML generado
    # Pero como acordamos, el botón de borrar estará fuera del iframe en UI principal.
    return HTMLResponse(html)

# -------------------------
# Nuevos endpoints: export y reset
# -------------------------

@app.get("/export_json")
def export_json():
    """
    Exporta el arbol_decisiones.json a /exports/export_YYYY-MM-DD_HH-MM-SS.json
    y devuelve el archivo como descarga (FileResponse).
    """
    if not ARCHIVO_ARBOL.exists():
        return JSONResponse({"error": "No existe arbol_decisiones.json para exportar"}, status_code=404)

    # crear carpeta exports si no existe
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # generar nombre con timestamp
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    export_name = f"export_{stamp}.json"
    export_path = EXPORTS_DIR / export_name

    # copiar el archivo
    try:
        shutil.copy(str(ARCHIVO_ARBOL), str(export_path))
    except Exception as e:
        return JSONResponse({"error": f"No se pudo crear archivo export: {str(e)}"}, status_code=500)

    # devolver como descarga
    return FileResponse(path=str(export_path), filename=export_name, media_type="application/json")

@app.post("/reset")
def reset():
    """
    Resetea el proyecto: borra arbol_decisiones.json y limpia la ruta de usuario.
    NO toca /exports (histórico).
    """
    global user_path
    user_path = []
    borrar_arbol()
    return JSONResponse({"ok": True})

# -------------------------
# Run guard (opcional) - si ejecutas con 'python server.py' directamente
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
