"""
Módulo para la extracción de ideas clave de sermones.

Este módulo utiliza la API de Claude para analizar una transcripción
de sermón y extraer las 7 ideas principales para generar contenido
de redes sociales, siguiendo una estructura narrativa de tres actos.
"""

import os
import json
from anthropic import Anthropic

def extraer_ideas_clave(cliente_anthropic, ruta_transcripcion, modelo="claude-3-7-sonnet-20250219"):
    """
    Extrae las ideas clave de una transcripción de sermón siguiendo una estructura narrativa de tres actos.
    
    Args:
        cliente_anthropic: Cliente inicializado de Anthropic
        ruta_transcripcion (str): Ruta al archivo de transcripción corregida
        modelo (str): Modelo de Claude a utilizar
        
    Returns:
        list: Lista de diccionarios con las ideas clave extraídas, siguiendo la estructura de tres actos
    """
    try:
        # Leer la transcripción
        with open(ruta_transcripcion, 'r', encoding='utf-8') as archivo:
            transcripcion = archivo.read()
        
        # Definimos el prompt para Claude
        sistema = """Eres un asistente especializado en análisis de contenido religioso cristiano.
Tu tarea es extraer exactamente 7 frases clave de un sermón siguiendo una estructura narrativa
de tres actos: planteamiento del problema, desafío/propuesta, y resolución/compromiso."""
        
        prompt = f"""
INSTRUCCIONES DETALLADAS:

Analiza la siguiente transcripción de un sermón cristiano y extrae exactamente 7 frases clave, 
organizadas según una estructura narrativa de tres actos:

ACTO 1 - PLANTEAMIENTO DEL PROBLEMA (2 frases):
- Frases que identifican un problema o deficiencia espiritual
- Frases que cuestionan prácticas superficiales de fe
- Ejemplos: "Si Dios es solo una hora de tu fin de semana", "Él no es tu Señor"

ACTO 2 - DESAFÍO Y PROPUESTA (2 frases):
- Frases que proponen un cambio o una nueva perspectiva
- Frases que desafían al oyente a tomar acción
- Ejemplos: "Es priorizar a Dios", "No es un añadido a tu vida ya ocupada"

ACTO 3 - RESOLUCIÓN Y COMPROMISO (3 frases):
- Frases que hablan de resultados y promesas
- Frases que expresan compromiso o intención
- Frases que concluyen con una verdad bíblica
- Ejemplos: "Él es el fundamento sobre el cual construyes toda tu vida", "Y mientras busco primero su reino"

CRITERIOS DE SELECCIÓN:
1. Usa EXACTAMENTE las palabras del predicador, sin parafrasear
2. Selecciona frases que funcionen de forma independiente y tengan impacto
3. Prefiere frases que incluyan referencias bíblicas cuando sea posible
4. Cada frase debe ser breve y clara (1-3 oraciones como máximo)
5. Selecciona frases que mantengan coherencia narrativa entre sí

FORMATO DE RESPUESTA:
Responde ÚNICAMENTE con un array JSON que contenga exactamente 7 objetos, cada uno con:
- "acto": Número del acto (1, 2 o 3)
- "orden": Número de orden dentro del acto (ejemplo: para el acto 1, puede ser 1 o 2)
- "texto": La frase o idea clave (usando las palabras exactas del predicador)
- "referencia_biblica": Referencia bíblica mencionada (si existe) o "No especificada"
- "contexto": Breve descripción (10-15 palabras) sobre el contexto

Las frases deben seguir EXACTAMENTE esta distribución:
- 2 frases para el Acto 1 (Planteamiento)
- 2 frases para el Acto 2 (Desafío)
- 3 frases para el Acto 3 (Resolución)

No incluyas ningún texto adicional, comentario o explicación. Solo el array JSON.

TRANSCRIPCIÓN DEL SERMÓN:
{transcripcion}
"""
        
        # Realizamos la consulta a Claude
        respuesta = cliente_anthropic.messages.create(
            model=modelo,
            max_tokens=2000,
            temperature=0.1,
            system=sistema,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Procesamos la respuesta
        contenido = respuesta.content[0].text
        
        # Intentamos extraer solo el JSON (en caso de que Claude incluya texto adicional)
        try:
            # Buscamos los corchetes de apertura y cierre del JSON
            inicio = contenido.find("[")
            fin = contenido.rfind("]") + 1
            
            if inicio >= 0 and fin > inicio:
                json_str = contenido[inicio:fin]
                ideas = json.loads(json_str)
            else:
                # Si no se encuentran los corchetes, intentamos parsear todo el contenido
                ideas = json.loads(contenido)
        except json.JSONDecodeError:
            print("Error al procesar el JSON devuelto por Claude. Intentando método alternativo...")
            # Método alternativo: eliminar texto no JSON y formatear correctamente
            lineas = contenido.strip().split('\n')
            json_lineas = []
            dentro_json = False
            
            for linea in lineas:
                if linea.strip().startswith("["):
                    dentro_json = True
                
                if dentro_json:
                    json_lineas.append(linea)
                
                if linea.strip().endswith("]"):
                    dentro_json = False
            
            json_str = '\n'.join(json_lineas)
            ideas = json.loads(json_str)
        
        # Verificamos que tenemos exactamente 7 ideas
        if len(ideas) != 7:
            print(f"Advertencia: Se esperaban 7 ideas, pero se obtuvieron {len(ideas)}")
        
        # Verificamos la distribución de actos
        actos_count = {1: 0, 2: 0, 3: 0}
        for idea in ideas:
            acto = idea.get('acto', 0)
            actos_count[acto] = actos_count.get(acto, 0) + 1
        
        if actos_count[1] != 2 or actos_count[2] != 2 or actos_count[3] != 3:
            print(f"Advertencia: Distribución incorrecta de actos. Acto 1: {actos_count[1]}, Acto 2: {actos_count[2]}, Acto 3: {actos_count[3]}")
        
        # Añadimos un campo adicional para la duración aproximada en video
        for i, idea in enumerate(ideas):
            # Asumimos que cada idea duraría aproximadamente entre 5-10 segundos
            idea['duracion_aproximada'] = min(10, max(5, len(idea['texto'].split()) / 3))
            
            # Calculamos una posición aproximada en el sermón
            idea['posicion_relativa'] = (i + 0.5) / len(ideas)
        
        return ideas
        
    except Exception as e:
        print(f"Error al extraer ideas clave: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def guardar_ideas_clave(ideas, ruta_transcripcion):
    """
    Guarda las ideas clave extraídas en un archivo JSON.
    
    Args:
        ideas (list): Lista de ideas clave
        ruta_transcripcion (str): Ruta al archivo de transcripción original
        
    Returns:
        str: Ruta al archivo JSON creado
    """
    try:
        # Generamos el nombre del archivo basado en la transcripción
        nombre_base = os.path.splitext(os.path.basename(ruta_transcripcion))[0]
        directorio = os.path.dirname(ruta_transcripcion)
        ruta_salida = os.path.join(directorio, f"{nombre_base}_ideas_clave.json")
        
        # Guardamos el JSON
        with open(ruta_salida, 'w', encoding='utf-8') as archivo:
            json.dump(ideas, archivo, ensure_ascii=False, indent=2)
        
        print(f"Ideas clave guardadas en: {ruta_salida}")
        return ruta_salida
        
    except Exception as e:
        print(f"Error al guardar ideas clave: {str(e)}")
        return None

def extraer_y_guardar_ideas_clave(cliente_anthropic, ruta_transcripcion, modelo="claude-3-7-sonnet-20250219"):
    """
    Función principal que coordina la extracción y guardado de ideas clave.
    
    Args:
        cliente_anthropic: Cliente inicializado de Anthropic
        ruta_transcripcion (str): Ruta al archivo de transcripción corregida
        modelo (str): Modelo de Claude a utilizar
        
    Returns:
        tuple: (bool, str) - (Éxito, Ruta al archivo JSON con ideas)
    """
    try:
        # Extraer ideas clave
        print(f"Extrayendo ideas clave de: {ruta_transcripcion}")
        ideas = extraer_ideas_clave(cliente_anthropic, ruta_transcripcion, modelo)
        
        if not ideas:
            print("No se pudieron extraer ideas clave.")
            return False, None
        
        # Guardar ideas en JSON
        ruta_json = guardar_ideas_clave(ideas, ruta_transcripcion)
        
        if not ruta_json:
            print("No se pudieron guardar las ideas clave.")
            return False, None
        
        print(f"Se han extraído y guardado {len(ideas)} ideas clave.")
        return True, ruta_json
        
    except Exception as e:
        print(f"Error en el proceso de extracción de ideas clave: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None
