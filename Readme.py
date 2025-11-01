import os


def listar_directorio(ruta_base, archivo_salida="estructura_proyecto.txt"):
    with open(archivo_salida, "w", encoding="utf-8") as f:
        for carpeta_raiz, subcarpetas, archivos in os.walk(ruta_base):
            nivel = carpeta_raiz.replace(ruta_base, "").count(os.sep)
            sangría = "  " * nivel
            f.write(f"{sangría}{os.path.basename(carpeta_raiz)}/\n")
            for archivo in archivos:
                f.write(f"{sangría}  {archivo}\n")


# Ruta base del proyecto (puedes cambiarla)
ruta_del_proyecto = "C:/Users/josem/Documents/Practicas JM"
listar_directorio(ruta_del_proyecto)
