import os

def listar_estructura(ruta_base=".", nivel=0, max_nivel=3):
    """
    Lista la estructura de carpetas y archivos de un proyecto.
    - ruta_base: carpeta raíz desde donde listar.
    - nivel: profundidad actual (no modificar).
    - max_nivel: máximo nivel de carpetas a mostrar.
    """
    if nivel == 0:
        print(f"Estructura de proyecto en: {os.path.abspath(ruta_base)}\n")

    if nivel > max_nivel:
        return

    try:
        elementos = sorted(os.listdir(ruta_base))
    except PermissionError:
        return

    for elemento in elementos:
        ruta_completa = os.path.join(ruta_base, elemento)
        prefijo = "│   " * nivel + "├── " if nivel > 0 else ""
        if os.path.isdir(ruta_completa):
            print(f"{prefijo}{elemento}/")
            listar_estructura(ruta_completa, nivel + 1, max_nivel)
        else:
            print(f"{prefijo}{elemento}")

if __name__ == "__main__":
    listar_estructura(".", max_nivel=3)
