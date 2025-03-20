import os
import argparse
import time
import re
from pathlib import Path
from anthropic import Anthropic

def configurar_argumentos():
    """Configura los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='Corrige transcripciones usando Claude')
    parser.add_argument('--input', type=str, required=True, help='Ruta al archivo de transcripción bruta')
    parser.add_argument('--output', type=str, help='Ruta para guardar la transcripción corregida')
    parser.add_argument('--api_key', type=str, help='Clave API de Anthropic (o usar variable de entorno ANTHROPIC_API_KEY)')
    parser.add_argument('--model', type=str, default="claude-3-7-sonnet-20250219", help='Modelo Claude a utilizar')
    return parser.parse_args()

def leer_transcripcion(ruta_archivo):
    """Lee el contenido del archivo de transcripción."""
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None

def corregir_con_claude(cliente, transcripcion, modelo, id_segmento=None, total_segmentos=None):
    """Envía la transcripción a Claude para corrección."""
    # Información de segmento para incluir en el prompt
    info_segmento = ""
    if id_segmento is not None and total_segmentos is not None:
        info_segmento = f"\nEste es el segmento {id_segmento} de {total_segmentos} de la transcripción completa."
    
    sistema = """Eres un corrector de transcripciones EXTREMADAMENTE CONSERVADOR. Tu ÚNICO trabajo es corregir errores ortográficos, gramaticales y de puntuación OBVIOS. NUNCA, bajo ninguna circunstancia, debes modificar el contenido, longitud, estructura o estilo del texto original. Debes devolver un texto casi idéntico al original, con la misma cantidad aproximada de caracteres."""
    
    prompt = f"""
    INSTRUCCIONES CRÍTICAS PARA LA CORRECCIÓN DE TRANSCRIPCIÓN
    
    Tu tarea es ÚNICAMENTE corregir errores OBVIOS de ortografía, gramática y puntuación en el segmento de transcripción proporcionado.{info_segmento}
    
    REGLAS ESTRICTAS QUE DEBES SEGUIR AL PIE DE LA LETRA:
    1. NO añadas NINGÚN contenido nuevo, ni siquiera un párrafo introductorio.
    2. NO resumas, condensas o parafrasees el texto bajo NINGUNA circunstancia.
    3. NO elimines NINGUNA parte del texto original.
    4. CONSERVA exactamente cada palabra, frase, oración y párrafo del original.
    5. MANTÉN todas las repeticiones, muletillas y características del habla oral.
    6. CORRIGE ÚNICAMENTE: ortografía, puntuación, gramática y errores tipográficos evidentes.
    7. CONSERVA el estilo de habla del predicador sin modificarlo.
    8. MANTÉN la misma longitud (número de caracteres) del texto original.
    
    EJEMPLOS DE LO QUE SÍ DEBES CORREGIR:
    - "Habían personas" → "Había personas" (concordancia gramatical)
    - "Iba en contra" → "Iba en contra" (sin cambios si está gramaticalmente correcto)
    - Añadir puntos y comas donde falten pero sin cambiar el sentido o ritmo
    - Corregir palabras mal escritas como "tectual" → "textual"
    
    EJEMPLOS DE LO QUE NO DEBES MODIFICAR:
    - Repeticiones intencionales como "cierto, cierto"
    - Expresiones coloquiales como "monedita de oro"
    - El estilo informal y característico de un sermón hablado
    - Digresiones o cambios abruptos de tema (comunes en el habla natural)
    
    IMPORTANTE: Tu respuesta debe mantener la estructura, el contenido y la intención exactos del original. Tu misión es SOLO corregir errores obvios, no mejorar el texto ni hacerlo más coherente o fluido.
    
    Segmento de transcripción a corregir (delimita con <INICIO_SEGMENTO> y <FIN_SEGMENTO>):
    
    <INICIO_SEGMENTO>
    {transcripcion}
    <FIN_SEGMENTO>
    
    EXTREMADAMENTE IMPORTANTE: Tu respuesta debe tener EXACTAMENTE la misma extensión que el texto original o muy similar, conservando todo el contenido. NO agregues ninguna introducción o conclusión. MANTÉN TODO EL CONTENIDO ORIGINAL.
    """
    
    try:
        respuesta = cliente.messages.create(
            model=modelo,
            max_tokens=4000,
            temperature=0.05,  # Temperatura más baja para respuestas más conservadoras
            system=sistema,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extraer solo el texto corregido, sin comentarios adicionales que Claude pudiera añadir
        texto_corregido = respuesta.content[0].text
        
        # Intentamos eliminar texto adicional que Claude podría añadir antes o después del segmento
        if "<INICIO_SEGMENTO>" in texto_corregido and "<FIN_SEGMENTO>" in texto_corregido:
            texto_corregido = re.search(r'<INICIO_SEGMENTO>(.*?)<FIN_SEGMENTO>', texto_corregido, re.DOTALL)
            if texto_corregido:
                texto_corregido = texto_corregido.group(1).strip()
        
        # Si no encontramos los delimitadores, tomamos todo el contenido
        return texto_corregido
    except Exception as e:
        print(f"Error al comunicarse con la API de Anthropic: {e}")
        return None

def verificar_integridad(texto_original, texto_corregido, tolerancia=0.20):
    """
    Verifica que el texto corregido mantenga la integridad del original.
    
    Args:
        texto_original: El texto original
        texto_corregido: El texto corregido
        tolerancia: La diferencia máxima permitida en longitud (por defecto 20%)
        
    Returns:
        bool: True si el texto corregido mantiene la integridad, False en caso contrario
    """
    # Verificar longitud similar
    len_original = len(texto_original)
    len_corregido = len(texto_corregido)
    
    # Calculamos la diferencia porcentual
    if len_original == 0:
        return False
    
    diferencia = abs(len_original - len_corregido) / len_original
    
    # Si la diferencia es mayor que la tolerancia, el texto no mantiene integridad
    if diferencia > tolerancia:
        print(f"Advertencia: La longitud del texto corregido difiere significativamente del original.")
        print(f"Original: {len_original} caracteres, Corregido: {len_corregido} caracteres")
        print(f"Diferencia: {diferencia*100:.1f}% (tolerancia: {tolerancia*100:.1f}%)")
        return False
    
    # Verificar que las palabras clave estén presentes
    # Extraemos algunas palabras significativas del original
    palabras_significativas = set()
    
    # Extraemos frases de 3 palabras del texto original 
    palabras_original = texto_original.split()
    if len(palabras_original) >= 3:
        for i in range(len(palabras_original) - 2):
            frase = " ".join(palabras_original[i:i+3]).lower()
            # Solo consideramos frases con palabras significativas (evitamos frases comunes)
            if len(frase) > 15:  # Frases relativamente largas
                palabras_significativas.add(frase)
    
    # Verificamos que algunas de estas frases estén en el texto corregido
    palabras_presentes = 0
    muestra_palabras = list(palabras_significativas)[:10]  # Tomamos hasta 10 frases
    
    for frase in muestra_palabras:
        if frase.lower() in texto_corregido.lower():
            palabras_presentes += 1
    
    # Si tenemos palabras significativas y menos del 70% están presentes, fallamos
    if len(muestra_palabras) > 0 and palabras_presentes / len(muestra_palabras) < 0.7:
        print(f"Advertencia: Contenido significativo puede haberse perdido en la corrección.")
        print(f"Solo {palabras_presentes} de {len(muestra_palabras)} frases clave encontradas.")
        return False
    
    return True

def dividir_texto(texto, tamano_segmento=1000):
    """Divide el texto en segmentos más pequeños respetando párrafos.
    
    Nota: Reducimos el tamaño de segmento para procesar mejor el texto.
    """
    # Diagnóstico
    print(f"Texto original: {len(texto)} caracteres")
    print(f"Tamaño de segmento solicitado: {tamano_segmento} caracteres")
    
    # Identificar el encabezado
    encabezado = ""
    lineas = texto.split('\n')
    
    # Identificamos el encabezado (primeras líneas hasta la separación)
    i = 0
    encabezado_encontrado = False
    for i, linea in enumerate(lineas):
        encabezado += linea + "\n"
        if "================" in linea:
            i += 1  # Incluimos la línea de separación
            encabezado_encontrado = True
            break
    
    # Si no encontramos la línea de separación o el encabezado es muy pequeño,
    # establecemos un límite mínimo para el encabezado
    if not encabezado_encontrado or len(encabezado) < 300:
        # Tomamos al menos 10 líneas como encabezado o hasta 300 caracteres
        nuevo_i = 0
        nuevo_encabezado = ""
        for j, linea in enumerate(lineas):
            nuevo_encabezado += linea + "\n"
            nuevo_i = j + 1
            if len(nuevo_encabezado) >= 300 or j >= 10:
                break
        
        # Solo usamos el nuevo encabezado si es más grande que el anterior
        if len(nuevo_encabezado) > len(encabezado):
            encabezado = nuevo_encabezado
            i = nuevo_i
    
    # Diagnóstico del encabezado
    print(f"Encabezado identificado: {len(encabezado)} caracteres")
    
    # El resto del texto lo dividimos en segmentos más pequeños
    resto_texto = "\n".join(lineas[i:])
    
    # Dividimos en segmentos más pequeños para mejor procesamiento
    chunks = []
    texto_actual = ""
    current_size = 0
    
    for parrafo in resto_texto.split('\n'):
        if current_size + len(parrafo) + 1 > tamano_segmento and current_size > 0:
            chunks.append(texto_actual)
            texto_actual = parrafo
            current_size = len(parrafo)
        else:
            if texto_actual:
                texto_actual += "\n" + parrafo
            else:
                texto_actual = parrafo
            current_size += len(parrafo) + 1  # +1 por el salto de línea
    
    if texto_actual:
        chunks.append(texto_actual)
    
    # Diagnóstico de segmentos antes de añadir encabezado
    print(f"Segmentos creados (sin encabezado): {len(chunks)}")
    
    # Si no se crearon suficientes segmentos, forzar división por caracteres
    if len(chunks) < 3 and len(resto_texto) > tamano_segmento * 2:
        print("Aplicando división forzada por caracteres...")
        chunks = []
        inicio = 0
        while inicio < len(resto_texto):
            fin = min(inicio + tamano_segmento, len(resto_texto))
            # Ajustar para no cortar en medio de una palabra
            if fin < len(resto_texto):
                # Retroceder hasta encontrar un espacio o salto de línea
                while fin > inicio and resto_texto[fin] not in [' ', '\n']:
                    fin -= 1
                if fin == inicio:  # Si no se encontró un buen punto de corte
                    fin = min(inicio + tamano_segmento, len(resto_texto))
            
            chunks.append(resto_texto[inicio:fin])
            inicio = fin
        
        print(f"Segmentos forzados creados: {len(chunks)}")
    
    # Ahora añadimos el encabezado a cada segmento
    segmentos_con_encabezado = []
    for segmento in chunks:
        segmentos_con_encabezado.append(encabezado + segmento)
    
    # Diagnóstico final
    print(f"Segmentos con encabezado: {len(segmentos_con_encabezado)}")
    for i, seg in enumerate(segmentos_con_encabezado):
        print(f"  Segmento {i+1}: {len(seg)} caracteres")
    
    return segmentos_con_encabezado

def corregir_segmentos(cliente, segmentos, modelo):
    """Corrige múltiples segmentos de transcripción y los combina."""
    segmentos_corregidos = []
    segmentos_fallidos = []
    
    # Primera pasada: corregir cada segmento individual
    for i, segmento in enumerate(segmentos):
        print(f"Corrigiendo segmento {i+1}/{len(segmentos)}...")
        intentos = 0
        max_intentos = 3
        segmento_corregido = None
        
        while intentos < max_intentos and segmento_corregido is None:
            # Corregimos el segmento
            segmento_corregido = corregir_con_claude(cliente, segmento, modelo, i+1, len(segmentos))
            
            # Verificamos integridad si obtuvimos respuesta
            if segmento_corregido:
                if not verificar_integridad(segmento, segmento_corregido, tolerancia=0.20):
                    print(f"Fallo de integridad en el segmento {i+1}. Reintentando...")
                    segmento_corregido = None  # Reintentar
            
            intentos += 1
        
        if segmento_corregido:
            segmentos_corregidos.append(segmento_corregido)
        else:
            print(f"Error al corregir el segmento {i+1} después de {max_intentos} intentos. Se usará el texto original.")
            segmentos_corregidos.append(segmento)
            segmentos_fallidos.append(i+1)
    
    # Informamos sobre los segmentos fallidos
    if segmentos_fallidos:
        print(f"Los siguientes segmentos no pudieron ser corregidos y se mantuvieron originales: {segmentos_fallidos}")
    
    # Segunda pasada: extraer el encabezado del primer segmento
    encabezado = ""
    primer_segmento = segmentos_corregidos[0]
    lineas_primer_segmento = primer_segmento.split('\n')
    
    # Identificamos el encabezado (hasta la línea con "====")
    indice_fin_encabezado = 0
    for i, linea in enumerate(lineas_primer_segmento):
        encabezado += linea + "\n"
        if "================" in linea:
            indice_fin_encabezado = i + 1
            break
    
    # Si no encontramos la línea de separación, tomamos las primeras 5 líneas como encabezado
    if not encabezado or "================" not in encabezado:
        indice_fin_encabezado = min(5, len(lineas_primer_segmento))
        encabezado = "\n".join(lineas_primer_segmento[:indice_fin_encabezado]) + "\n"
    
    # Identificar un patrón común en todos los segmentos (como "El Señor nos ayude")
    patron_comun = ""
    if len(segmentos_corregidos) > 1:
        # Tomamos las primeras 100 caracteres de cada segmento después del encabezado
        muestras = []
        for seg in segmentos_corregidos:
            lineas_seg = seg.split('\n')
            if len(lineas_seg) > indice_fin_encabezado:
                contenido = ' '.join(lineas_seg[indice_fin_encabezado:])[:100]
                muestras.append(contenido)
        
        # Buscamos un patrón común al inicio (primeros 50 caracteres)
        if muestras:
            patron_min_length = 20  # Al menos 20 caracteres para considerar un patrón
            patron_length = 0
            for i in range(min(50, min(len(m) for m in muestras))):
                if all(m[i] == muestras[0][i] for m in muestras):
                    patron_length = i + 1
                else:
                    break
            
            if patron_length >= patron_min_length:
                patron_comun = muestras[0][:patron_length]
                print(f"Patrón común identificado: '{patron_comun[:30]}...'")
    
    # Tercera pasada: combinar segmentos eliminando duplicados
    texto_combinado = ""
    
    # Agregamos el encabezado solo una vez
    texto_combinado += encabezado
    
    # Agregamos el contenido del primer segmento (sin encabezado)
    contenido_primer_segmento = '\n'.join(lineas_primer_segmento[indice_fin_encabezado:])
    texto_combinado += contenido_primer_segmento
    
    # Agregamos los demás segmentos, eliminando encabezados y patrones comunes
    for i in range(1, len(segmentos_corregidos)):
        seg = segmentos_corregidos[i]
        
        # Dividimos el segmento en líneas
        lineas_seg = seg.split('\n')
        
        # Saltamos las líneas del encabezado
        indice_inicio = 0
        for j, linea in enumerate(lineas_seg):
            if "================" in linea:
                indice_inicio = j + 1
                break
        
        # Si no encontramos la línea de separación, saltamos las primeras líneas (mismo número que en el encabezado)
        if indice_inicio == 0:
            indice_inicio = indice_fin_encabezado
        
        # Extraemos el contenido después del encabezado
        contenido = '\n'.join(lineas_seg[indice_inicio:])
        
        # Eliminamos el patrón común si existe
        if patron_comun and contenido.startswith(patron_comun):
            contenido = contenido[len(patron_comun):].lstrip()
        
        # Añadimos el contenido sin duplicaciones
        if contenido:
            texto_combinado += "\n" + contenido
    
    return texto_combinado

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

def corregir_transcripcion_por_segmentos(cliente_anthropic, ruta_archivo, ruta_salida, modelo="claude-3-7-sonnet-20250219", tamano_segmento=1000):
    """Corrige una transcripción dividiéndola en segmentos."""
    # Leer la transcripción completa
    transcripcion_completa = leer_transcripcion(ruta_archivo)
    if not transcripcion_completa:
        return False, 0, 0
    
    # Dividir en segmentos (con tamaño ajustado)
    print(f"Dividiendo transcripción en segmentos de aproximadamente {tamano_segmento} caracteres...")
    segmentos = dividir_texto(transcripcion_completa, tamano_segmento)
    print(f"Transcripción dividida en {len(segmentos)} segmentos.")
    
    # Verificar que se hayan creado suficientes segmentos
    if len(segmentos) <= 1 and len(transcripcion_completa) > tamano_segmento * 2:
        print("ADVERTENCIA: La transcripción no se dividió correctamente. Forzando división.")
        # Dividir el texto en fragmentos de tamaño fijo ignorando párrafos
        texto_chars = list(transcripcion_completa)
        encabezado = transcripcion_completa[:min(500, len(transcripcion_completa))]  # Tomar los primeros 500 caracteres como encabezado
        chunks = [texto_chars[i:i+tamano_segmento] for i in range(0, len(texto_chars), tamano_segmento)]
        segmentos = [encabezado + ''.join(chunk) for chunk in chunks]
        print(f"Segmentos forzados creados: {len(segmentos)}")
    
    # Corregir segmentos
    print(f"Enviando segmentos a {modelo} para corrección...")
    inicio = time.time()
    transcripcion_corregida = corregir_segmentos(cliente_anthropic, segmentos, modelo)
    fin = time.time()
    
    if not transcripcion_corregida:
        return False, 0, 0
    
    print(f"Corrección completada en {fin - inicio:.2f} segundos")
    
    # Verificar integridad final
    if not verificar_integridad(transcripcion_completa, transcripcion_corregida, tolerancia=0.20):
        print("ADVERTENCIA: La transcripción corregida final presenta diferencias significativas con el original.")
        print("Se recomienda revisar manualmente el resultado.")
    
    # Guardar resultado
    exito = guardar_transcripcion_corregida(transcripcion_corregida, ruta_salida)
    
    if exito:
        # Estadísticas
        caracteres_original = len(transcripcion_completa)
        caracteres_corregido = len(transcripcion_corregida)
        return True, caracteres_original, caracteres_corregido
    
    return False, 0, 0

def main():
    """Función principal del programa."""
    args = configurar_argumentos()
    
    # Verificar si existe el archivo de entrada
    if not os.path.exists(args.input):
        print(f"El archivo de entrada no existe: {args.input}")
        return
    
    # Configurar la ruta de salida si no se especificó
    if not args.output:
        ruta_entrada = Path(args.input)
        args.output = str(ruta_entrada.parent / f"{ruta_entrada.stem}_corregido{ruta_entrada.suffix}")
    
    # Obtener la clave API de Anthropic
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Se requiere una clave API de Anthropic. Proporcione --api_key o establezca la variable de entorno ANTHROPIC_API_KEY.")
        return
    
    # Inicializar el cliente de Anthropic
    cliente = Anthropic(api_key=api_key)
    
    # Procesar la transcripción por segmentos
    print(f"Leyendo transcripción: {args.input}")
    exito, caracteres_original, caracteres_corregido = corregir_transcripcion_por_segmentos(
        cliente, args.input, args.output, args.model, tamano_segmento=tamano_segmento
    )
    
    if exito:
        # Mostrar estadísticas
        print(f"\nEstadísticas:")
        print(f"- Caracteres originales: {caracteres_original}")
        print(f"- Caracteres corregidos: {caracteres_corregido}")
        print(f"- Diferencia: {caracteres_corregido - caracteres_original} caracteres")
        print(f"- Porcentaje de cambio: {((caracteres_corregido - caracteres_original) / caracteres_original) * 100:.2f}%")

if __name__ == "__main__":
    main()
