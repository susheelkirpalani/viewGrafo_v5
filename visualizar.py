import json
from pathlib import Path
import html

# Archivos
ARBOL_FILE = Path("arbol_decisiones.json")
HTML_FILE = Path("grafo_decisiones.html")

# Colores
COLOR_NODO = "#60a5fa"
COLOR_SELECCIONADO = "#10b981"
COLOR_TEXTO = "#ffffff"
COLOR_BORDE = "#2563eb"


def recorrer_arbol(nodo, nodos, edges, parent_id=None, ruta_ids=None):
    """Recorre el árbol y genera nodos y aristas."""
    if not nodo:
        return
    nid = nodo.get("id", "")
    texto = nodo.get("texto", "(sin texto)")
    color = COLOR_NODO
    if ruta_ids and nid in ruta_ids:
        color = COLOR_SELECCIONADO

    nodos.append({
        "id": nid,
        "label": texto,
        "color": {"background": color, "border": COLOR_BORDE},
        "font": {"color": COLOR_TEXTO}
    })

    if parent_id:
        edges.append({
            "from": parent_id,
            "to": nid,
            "label": "→",
            "arrows": "to"
        })

    for op in nodo.get("opciones", []):
        op_id = op.get("id")
        op_texto = op.get("texto", "")
        siguiente = op.get("siguiente")
        nodos.append({
            "id": op_id,
            "label": op_texto,
            "color": {"background": "#fbbf24", "border": "#b45309"},
            "font": {"color": "#111"}
        })
        edges.append({
            "from": nid,
            "to": op_id,
            "label": "elige",
            "arrows": "to"
        })
        if isinstance(siguiente, dict):
            recorrer_arbol(siguiente, nodos, edges, op_id, ruta_ids)


def generar_grafo():
    if not ARBOL_FILE.exists():
        print("⚠️ No existe arbol_decisiones.json. Nada que visualizar.")
        return

    data = json.loads(ARBOL_FILE.read_text(encoding="utf-8"))
    nodos, edges = [], []

    # Intentar leer ruta guardada (si existe)
    ruta_file = Path("estado_ruta.json")
    ruta_ids = []
    if ruta_file.exists():
        try:
            ruta_ids = json.loads(ruta_file.read_text(encoding="utf-8"))
        except Exception:
            ruta_ids = []

    recorrer_arbol(data, nodos, edges, None, ruta_ids)

    # --- HTML de salida ---
    html_code = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Visualización del Árbol de Decisiones</title>
<link rel="stylesheet" href="lib/vis-9.1.2/vis-network.css" />
<script src="lib/vis-9.1.2/vis-network.min.js"></script>
<style>
body {{ background:#f9fafb; font-family:Arial, sans-serif; text-align:center; }}
#network {{ width: 95%; height: 90vh; margin: 20px auto; border:1px solid #ddd; border-radius:10px; }}
h2 {{ color:#2563eb; }}
</style>
</head>
<body>
<h2>🌳 Visualización del Árbol de Decisiones</h2>
<div id="network"></div>

<script>
  const nodes = new vis.DataSet({json.dumps(nodos, ensure_ascii=False)});
  const edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
  const container = document.getElementById('network');
  const data = {{ nodes, edges }};
  const options = {{
    layout: {{ hierarchical: {{ direction: 'UD', sortMethod: 'directed' }} }},
    nodes: {{ shape: 'box', margin:10, widthConstraint: {{ maximum:250 }} }},
    edges: {{ smooth: true }},
    physics: false,
    interaction: {{ hover: true }}
  }};
  const network = new vis.Network(container, data, options);
</script>
</body>
</html>
"""
    HTML_FILE.write_text(html_code, encoding="utf-8")
    print(f"✅ Grafo generado correctamente en: {HTML_FILE}")


if __name__ == "__main__":
    generar_grafo()
