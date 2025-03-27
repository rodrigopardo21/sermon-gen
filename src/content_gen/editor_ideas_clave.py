"""
Módulo para la edición de ideas clave extraídas.

Este módulo proporciona herramientas para convertir las ideas clave extraídas
a un formato de texto legible y editable, similar a la estructura de un reel.
"""

import os
import json
import argparse

def convertir_json_a_txt(ruta_json, ruta_salida=None):
    """
    Convierte un archivo JSON de ideas clave a un formato de texto editable.
    
    Args:
        ruta_json (str): Ruta al archivo JSON con las ideas clave
        ruta_salida (str, optional): Ruta donde guardar el archivo TXT
        
    Returns:
        str: Ruta al archivo de texto creado
    """
    try:
        # Leer el archivo JSON
        with open(ruta_json, 'r', encoding='utf-8') as archivo:
            ideas = json.load(archivo)
        
        # Si no se especifica ruta de salida, la generamos
        if not ruta_salida:
            base_name = os.path.splitext(os.path.basename(ruta_json))[0]
            directorio = os.path.dirname(ruta_json)
            ruta_salida = os.path.join(directorio, f"{base_name}_editable.txt")
        
        # Crear el contenido del archivo TXT
        contenido = []
        
        # Agregar encabezado explicativo
        contenido.append("# IDEAS CLAVE EXTRAÍDAS DEL SERMÓN - ESTRUCTURA DE TRES ACTOS")
        contenido.append("# =================================")
        contenido.append("# Instrucciones:")
        contenido.append("# 1. Revisa cada idea y edita el texto si lo consideras necesario")
        contenido.append("# 2. Mantén la estructura de 7 frases divididas en 3 actos")
        contenido.append("# 3. Cada bloque debe mantener el formato original")
        contenido.append("# 4. No modifiques las líneas que comienzan con '##'")
        contenido.append("# 5. Guarda el archivo cuando termines")
        contenido.append("# =================================\n")
        
        # Organizar las ideas por acto
        ideas_por_acto = {1: [], 2: [], 3: []}
        for idea in ideas:
            acto = idea.get('acto', 1)  # Default a acto 1 si no está especificado
            ideas_por_acto[acto].append(idea)
        
        # Agregar las ideas por acto
        contenido.append("## ACTO 1: PLANTEAMIENTO DEL PROBLEMA")
        contenido.append("# Frases que identifican un problema o deficiencia espiritual")
        contenido.append("# ---------------------------------")
        for i, idea in enumerate(ideas_por_acto[1], 1):
            contenido.append(f"## IDEA 1.{i}")
            contenido.append(f"TEXTO: {idea['texto']}")
            contenido.append(f"REFERENCIA BÍBLICA: {idea['referencia_biblica']}")
            contenido.append(f"CONTEXTO: {idea['contexto']}")
            contenido.append("")  # Línea en blanco
        
        contenido.append("## ACTO 2: DESAFÍO Y PROPUESTA")
        contenido.append("# Frases que proponen un cambio o una nueva perspectiva")
        contenido.append("# ---------------------------------")
        for i, idea in enumerate(ideas_por_acto[2], 1):
            contenido.append(f"## IDEA 2.{i}")
            contenido.append(f"TEXTO: {idea['texto']}")
            contenido.append(f"REFERENCIA BÍBLICA: {idea['referencia_biblica']}")
            contenido.append(f"CONTEXTO: {idea['contexto']}")
            contenido.append("")  # Línea en blanco
        
        contenido.append("## ACTO 3: RESOLUCIÓN Y COMPROMISO")
        contenido.append("# Frases que hablan de resultados, promesas o compromisos")
        contenido.append("# ---------------------------------")
        for i, idea in enumerate(ideas_por_acto[3], 1):
            contenido.append(f"## IDEA 3.{i}")
            contenido.append(f"TEXTO: {idea['texto']}")
            contenido.append(f"REFERENCIA BÍBLICA: {idea['referencia_biblica']}")
            contenido.append(f"CONTEXTO: {idea['contexto']}")
            contenido.append("")  # Línea en blanco
        
        # Agregar pie explicativo
        contenido.append("# =================================")
        contenido.append("# Para convertir este archivo editado de vuelta a JSON, ejecuta:")
        contenido.append(f"# python src/content_gen/editor_ideas_clave.py txt2json --input {os.path.basename(ruta_salida)}")
        contenido.append("# =================================")
        
        # Guardar el archivo
        with open(ruta_salida, 'w', encoding='utf-8') as archivo:
            archivo.write('\n'.join(contenido))
        
        print(f"Archivo de texto editable guardado en: {ruta_salida}")
        return ruta_salida
        
    except Exception as e:
        print(f"Error al convertir JSON a TXT: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def convertir_txt_a_json(ruta_txt, ruta_salida=None):
    """
    Convierte un archivo de texto editable de ideas clave de vuelta a formato JSON.
    
    Args:
        ruta_txt (str): Ruta al archivo TXT con las ideas clave editadas
        ruta_salida (str, optional): Ruta donde guardar el archivo JSON
        
    Returns:
        str: Ruta al archivo JSON creado
    """
    try:
        # Leer el archivo TXT
        with open(ruta_txt, 'r', encoding='utf-8') as archivo:
            lineas = archivo.readlines()
        
        # Si no se especifica ruta de salida, la generamos
        if not ruta_salida:
            base_name = os.path.splitext(os.path.basename(ruta_txt))[0]
            # Quitamos el sufijo "_editable" si existe
            if base_name.endswith("_editable"):
                base_name = base_name[:-9]
            directorio = os.path.dirname(ruta_txt)
            ruta_salida = os.path.join(directorio, f"{base_name}_editado.json")
        
        # Procesar las líneas para extraer las ideas
        ideas = []
        idea_actual = None
        acto_actual = 1
        
        for linea in lineas:
            linea = linea.strip()
            
            # Ignorar líneas de comentarios y vacías
            if not linea or linea.startswith("#"):
                continue
            
            # Detectar cambio de acto
            if linea.startswith("## ACTO"):
                if "PLANTEAMIENTO" in linea:
                    acto_actual = 1
                elif "DESAFÍO" in linea:
                    acto_actual = 2
                elif "RESOLUCIÓN" in linea:
                    acto_actual = 3
                continue
            
            # Detectar nueva idea
            if linea.startswith("## IDEA"):
                # Si ya teníamos una idea en proceso, la guardamos
                if idea_actual is not None:
                    ideas.append(idea_actual)
                
                # Iniciar nueva idea
                idea_actual = {
                    "acto": acto_actual,
                    "orden": int(linea.split(".")[-1]) if "." in linea else 1,
                    "texto": "",
                    "referencia_biblica": "",
                    "contexto": "",
                    # Estos campos se calculan automáticamente al final
                    "duracion_aproximada": 0,
                    "posicion_relativa": 0
                }
            
            # Detectar campos
            elif linea.startswith("TEXTO: "):
                idea_actual["texto"] = linea[7:]
            elif linea.startswith("REFERENCIA BÍBLICA: "):
                idea_actual["referencia_biblica"] = linea[20:]
            elif linea.startswith("CONTEXTO: "):
                idea_actual["contexto"] = linea[10:]
        
        # No olvidar la última idea
        if idea_actual is not None:
            ideas.append(idea_actual)
        
        # Ordenar las ideas por acto y orden
        ideas.sort(key=lambda x: (x["acto"], x["orden"]))
        
        # Recalcular campos adicionales
        for i, idea in enumerate(ideas):
            # Duración aproximada basada en el número de palabras
            idea["duracion_aproximada"] = min(10, max(5, len(idea["texto"].split()) / 3))
            
            # Posición relativa en el sermón
            idea["posicion_relativa"] = (i + 0.5) / len(ideas)
        
        # Guardar el archivo JSON
        with open(ruta_salida, 'w', encoding='utf-8') as archivo:
            json.dump(ideas, archivo, ensure_ascii=False, indent=2)
        
        print(f"Ideas editadas guardadas en: {ruta_salida}")
        return ruta_salida
        
    except Exception as e:
        print(f"Error al convertir TXT a JSON: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Función principal para uso en línea de comandos."""
    parser = argparse.ArgumentParser(description='Herramienta para la edición de ideas clave extraídas de sermones')
    
    # Subparsers para comandos diferentes
    subparsers = parser.add_subparsers(dest='comando', help='Comando a ejecutar')
    
    # Comando para convertir JSON a TXT
    json_to_txt = subparsers.add_parser('json2txt', help='Convierte un archivo JSON a formato TXT editable')
    json_to_txt.add_argument('--input', type=str, required=True, help='Ruta al archivo JSON')
    json_to_txt.add_argument('--output', type=str, help='Ruta para guardar el archivo TXT (opcional)')
    
    # Comando para convertir TXT a JSON
    txt_to_json = subparsers.add_parser('txt2json', help='Convierte un archivo TXT editado a formato JSON')
    txt_to_json.add_argument('--input', type=str, required=True, help='Ruta al archivo TXT')
    txt_to_json.add_argument('--output', type=str, help='Ruta para guardar el archivo JSON (opcional)')
    
    args = parser.parse_args()
    
    if args.comando == 'json2txt':
        convertir_json_a_txt(args.input, args.output)
    elif args.comando == 'txt2json':
        convertir_txt_a_json(args.input, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
