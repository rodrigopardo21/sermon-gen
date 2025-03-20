"""
Módulo para la corrección de transcripciones línea por línea.

Este módulo proporciona funcionalidades para corregir transcripciones manteniendo
su estructura original y utilizando Claude para realizar correcciones específicas
sin alterar el formato general.
"""

import os
import json
import time
from anthropic import Anthropic

def leer_transcripcion(ruta_archivo):
    """Lee el contenido del archivo de transcripción."""
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None

def leer_json_transcripcion(ruta_json):
    """Lee el archivo JSON de transcripción que contiene segmentos con marcas de tiempo."""
    try:
        with open(ruta_json, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except Exception as e:
        print(f"Error al leer el archivo JSON: {e}")
        return None

def extraer_limites_segmentos(datos_json):
    """
    Extrae los límites entre segmentos de audio desde los datos JSON.
    
    Args:
        datos_json: Datos de transcripción en formato JSON que contiene información de segmentos
        
    Returns:
        list: Lista de límites de segmentos (en caracteres) en el texto completo
    """
    if not datos_json or 'segments' not in datos_json:
        print("No se encontró información de segmentos en el JSON")
        return []
    
    # Extraer los segmentos
    segmentos = datos_json.get('segments', [])
    
    # Calcular los límites en caracteres (aproximado)
    limites = []
    texto_acumulado = ""
    
    for i, segmento in enumerate(segmentos):
        # Omitimos el último segmento ya que no hay límite después de él
        if i < len(segmentos) - 1:
            texto_acumulado += segmento.get('text', '') + " "
            limites.append(len(texto_acumulado))
    
    print(f"Identificados {len(limites)} límites de segmentos")
    return limites

def dividir_en_unidades_pequenas(texto):
    """
    Divide el texto en unidades más pequeñas para una corrección más efectiva.
    
    Args:
        texto (str): Texto completo a dividir
        
    Returns:
        list: Lista de unidades de texto pequeñas
    """
    # 1. Primero, separamos el encabezado
    lineas = texto.split('\n')
    encabezado = []
    contenido = []
    
    # Identificar el encabezado (asumimos que está antes de la línea con ======)
    en_encabezado = True
    for linea in lineas:
        if "=====" in linea:
            encabezado.append(linea)
            en_encabezado = False
            continue
        
        if en_encabezado:
            encabezado.append(linea)
        else:
            contenido.append(linea)
    
    # 2. Dividimos el contenido en pequeñas unidades, aproximadamente por frases
    # (Consideramos frases como unidades terminadas en ".", "?", o "!")
    texto_contenido = '\n'.join(contenido)
    
    # Reemplazamos los finales de frase seguidos de salto de línea para preservarlos
    texto_contenido = texto_contenido.replace('.\n', '.||SALTO||')
    texto_contenido = texto_contenido.replace('?\n', '?||SALTO||')
    texto_contenido = texto_contenido.replace('!\n', '!||SALTO||')
    
    # Dividimos por finales de frase
    fragmentos_raw = []
    for fragmento in texto_contenido.replace('. ', '.|SPLIT|').replace('? ', '?|SPLIT|').replace('! ', '!|SPLIT|').split('|SPLIT|'):
        # Restauramos los saltos de línea
        fragmento = fragmento.replace('||SALTO||', '\n')
        if fragmento.strip():
            fragmentos_raw.append(fragmento.strip())
    
    # 3. Agrupamos frases en unidades de tamaño razonable (300-400 caracteres máximo)
    unidades = []
    unidad_actual = ""
    max_tamano = 400  # Máximo número de caracteres por unidad
    
    for fragmento in fragmentos_raw:
        if len(unidad_actual) + len(fragmento) <= max_tamano:
            if unidad_actual:
                unidad_actual += " " + fragmento
            else:
                unidad_actual = fragmento
        else:
            if unidad_actual:  # Guardamos la unidad actual antes de empezar una nueva
                unidades.append(unidad_actual)
            unidad_actual = fragmento
    
    # No olvidamos la última unidad
    if unidad_actual:
        unidades.append(unidad_actual)
    
    # 4. El encabezado lo dejamos como una unidad separada
    encabezado_texto = '\n'.join(encabezado)
    if encabezado_texto.strip():
        unidades.insert(0, encabezado_texto)
    
    print(f"Texto dividido en {len(unidades)} unidades pequeñas")
    return unidades

def corregir_unidad(cliente, unidad, modelo="claude-3-7-sonnet-20250219"):
    """
    Corrige una unidad individual de texto usando Claude, manteniendo su estructura.
    
    Args:
        cliente: Cliente de Anthropic
        unidad (str): Unidad de texto a corregir
        modelo (str): Modelo Claude a utilizar
        
    Returns:
        str: Unidad corregida
    """
    # Si la unidad está vacía o es muy corta, la devolvemos sin cambios
    if not unidad or len(unidad) < 10:
        return unidad
    
    sistema = """Eres un corrector EXTREMADAMENTE CONSERVADOR de transcripciones de sermones religiosos. 
Tu ÚNICA tarea es corregir errores ortográficos, gramaticales, y términos religiosos mal transcritos, 
MANTENIENDO EXACTAMENTE la misma estructura, formato y contenido."""
    
    prompt = f"""
INSTRUCCIONES DE CORRECCIÓN ESTRICTAS:

Corrige ÚNICAMENTE los siguientes tipos de errores en este fragmento de un sermón:
1. Errores ortográficos básicos (palabras mal escritas)
2. Errores gramaticales evidentes
3. Términos bíblicos o teológicos incorrectos, incluyendo:
   - Nombres de libros bíblicos mal escritos o confundidos
   - Referencias incorrectas como "avenida del Señor" que debería ser "venida del Señor"
   - Palabras teológicas incorrectas o mal transcritas
4. Nombres propios de personas bíblicas o religiosas conocidas

REGLAS QUE DEBES SEGUIR ABSOLUTAMENTE:
1. NO CAMBIÉS la estructura o formato del texto
2. NO AGREGUES ni ELIMINES contenido
3. NO ALTERES los saltos de línea
4. NO REESCRIBAS ni PARAFRASEES el texto
5. MANTÉN los términos y expresiones propias del predicador aunque parezcan coloquiales
6. PRESERVA las repeticiones intencionales (como palabras repetidas)
7. NO INTENTES mejorar la claridad o fluidez del texto

TEXTO A CORREGIR:
{unidad}

RESPONDE ÚNICAMENTE CON EL TEXTO CORREGIDO, SIN COMENTARIOS ADICIONALES.
"""
    
    try:
        respuesta = cliente.messages.create(
            model=modelo,
            max_tokens=1000,
            temperature=0.1,  # Temperatura muy baja para ser conservador
            system=sistema,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extraer solo el texto corregido
        texto_corregido = respuesta.content[0].text
        
        # Si la corrección cambia significativamente la longitud, usamos el original
        if abs(len(texto_corregido) - len(unidad)) > len(unidad) * 0.2:
            print(f"Advertencia: La corrección cambió significativamente la longitud del texto. Usando original.")
            return unidad
        
        return texto_corregido
    
    except Exception as e:
        print(f"Error al comunicarse con la API de Anthropic: {e}")
        return unidad

def corregir_transcripcion_por_unidades(cliente, texto_completo, limites_segmentos=None, modelo="claude-3-7-sonnet-20250219"):
    """
    Corrige una transcripción completa por unidades pequeñas, preservando los límites de segmentos.
    
    Args:
        cliente: Cliente de Anthropic
        texto_completo (str): Texto completo de la transcripción
        limites_segmentos (list): Lista de posiciones (en caracteres) donde hay límites de segmentos
        modelo (str): Modelo Claude a utilizar
        
    Returns:
        str: Transcripción corregida completa
    """
    # Dividir en unidades pequeñas
    unidades = dividir_en_unidades_pequenas(texto_completo)
    
    # Corregir cada unidad
    unidades_corregidas = []
    for i, unidad in enumerate(unidades):
        print(f"Corrigiendo unidad {i+1}/{len(unidades)}...")
        
        # Hacemos tres intentos máximo por unidad
        intentos = 0
        unidad_corregida = None
        
        while intentos < 3 and unidad_corregida is None:
            try:
                unidad_corregida = corregir_unidad(cliente, unidad, modelo)
            except Exception as e:
                print(f"Error en intento {intentos+1}: {e}")
                time.sleep(2)  # Pequeña pausa antes de reintentar
                intentos += 1
        
        # Si todos los intentos fallaron, usamos la unidad original
        if unidad_corregida is None:
            unidad_corregida = unidad
            print(f"No se pudo corregir la unidad {i+1}. Usando original.")
        
        # Verificamos si se hicieron cambios
        if unidad_corregida != unidad:
            print(f"  Se realizaron correcciones en la unidad {i+1}")
        
        unidades_corregidas.append(unidad_corregida)
    
    # Combinamos todas las unidades preservando el formato original
    texto_corregido = ""
    es_primera_unidad = True
    
    for unidad in unidades_corregidas:
        # Para el encabezado (primera unidad) no añadimos espacio
        if es_primera_unidad:
            texto_corregido += unidad
            es_primera_unidad = False
        else:
            # Para las demás unidades, verificamos si debemos añadir espacio o no
            if texto_corregido.endswith("\n") or unidad.startswith("\n"):
                texto_corregido += unidad
            else:
                texto_corregido += " " + unidad
    
    return texto_corregido

def guardar_transcripcion_corregida(transcripcion_corregida, ruta_salida):
    """Guarda la transcripción corregida en un archivo."""
    try:
        # Crear directorio si no existe
        directorio = os.path.dirname(ruta_salida)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
            
        with open(ruta_salida, 'w', encoding='utf-8') as archivo:
            archivo.write(transcripcion_corregida)
        print(f"Transcripción corregida guardada en: {ruta_salida}")
        return True
    except Exception as e:
        print(f"Error al guardar la transcripción corregida: {e}")
        return False

def corregir_transcripcion_completa(cliente_anthropic, ruta_texto, ruta_json=None, ruta_salida=None, modelo="claude-3-7-sonnet-20250219"):
    """
    Función principal que coordina el proceso completo de corrección.
    
    Args:
        cliente_anthropic: Cliente de Anthropic inicializado
        ruta_texto (str): Ruta al archivo de texto de la transcripción
        ruta_json (str): Ruta al archivo JSON con metadatos (opcional)
        ruta_salida (str): Ruta donde guardar el resultado (opcional)
        modelo (str): Modelo Claude a utilizar
        
    Returns:
        tuple: (bool, str) - (Éxito, Texto corregido)
    """
    # Leer la transcripción
    texto_original = leer_transcripcion(ruta_texto)
    if not texto_original:
        return False, None
    
    # Si no se especifica ruta de salida, la generamos
    if not ruta_salida:
        base_name = os.path.basename(ruta_texto)
        directorio = os.path.dirname(ruta_texto)
        nombre_base = os.path.splitext(base_name)[0]
        ruta_salida = os.path.join(directorio, f"{nombre_base}_linea_por_linea.txt")
    
    # Leer información de segmentos si se proporciona un archivo JSON
    limites_segmentos = None
    if ruta_json:
        datos_json = leer_json_transcripcion(ruta_json)
        if datos_json:
            limites_segmentos = extraer_limites_segmentos(datos_json)
    
    # Corregir la transcripción por unidades pequeñas
    print(f"Iniciando corrección de la transcripción...")
    texto_corregido = corregir_transcripcion_por_unidades(
        cliente_anthropic, texto_original, limites_segmentos, modelo
    )
    
    # Guardar resultado
    exito = guardar_transcripcion_corregida(texto_corregido, ruta_salida)
    
    # Estadísticas
    if exito:
        print(f"\nEstadísticas:")
        print(f"- Caracteres originales: {len(texto_original)}")
        print(f"- Caracteres corregidos: {len(texto_corregido)}")
        print(f"- Diferencia: {len(texto_corregido) - len(texto_original)} caracteres")
    
    return exito, texto_corregido

def main():
    """Función principal para uso en línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Corrección de transcripciones línea por línea con Claude')
    parser.add_argument('--input', type=str, required=True, help='Ruta al archivo de transcripción')
    parser.add_argument('--json', type=str, help='Ruta al archivo JSON de metadatos (opcional)')
    parser.add_argument('--output', type=str, help='Ruta para guardar la transcripción corregida')
    parser.add_argument('--api_key', type=str, help='Clave API de Anthropic (o usar variable ANTHROPIC_API_KEY)')
    parser.add_argument('--model', type=str, default="claude-3-7-sonnet-20250219", help='Modelo Claude a utilizar')
    
    args = parser.parse_args()
    
    # Obtener API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Se requiere una clave API de Anthropic. Proporcione --api_key o establezca la variable de entorno ANTHROPIC_API_KEY.")
        return
    
    # Inicializar cliente
    cliente = Anthropic(api_key=api_key)
    
    # Procesar la transcripción
    exito, _ = corregir_transcripcion_completa(
        cliente, args.input, args.json, args.output, args.model
    )
    
    if exito:
        print("Corrección completada con éxito.")
    else:
        print("Error durante el proceso de corrección.")

if __name__ == "__main__":
    main()
