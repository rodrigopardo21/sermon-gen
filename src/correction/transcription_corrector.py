import os
import argparse
import time
from pathlib import Path
from openai import OpenAI

def configurar_argumentos():
    """Configura los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='Corrige transcripciones usando GPT-4')
    parser.add_argument('--input', type=str, required=True, help='Ruta al archivo de transcripción bruta')
    parser.add_argument('--output', type=str, help='Ruta para guardar la transcripción corregida')
    parser.add_argument('--api_key', type=str, help='Clave API de OpenAI (o usar variable de entorno OPENAI_API_KEY)')
    parser.add_argument('--model', type=str, default="gpt-4-turbo", help='Modelo GPT a utilizar')
    return parser.parse_args()

def leer_transcripcion(ruta_archivo):
    """Lee el contenido del archivo de transcripción."""
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None

def corregir_con_gpt(cliente, transcripcion, modelo):
    """Envía la transcripción a GPT-4 para corrección."""
    prompt = """
    Por favor, corrige la siguiente transcripción de un sermón. 
    Mejora la ortografía, gramática, puntuación y legibilidad general.
    Mantén el contenido y el significado original pero mejora la estructura de las oraciones si es necesario.
    No agregues ni elimines información sustancial.
    
    Transcripción:
    
    """
    
    try:
        respuesta = cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": "Eres un asistente especializado en corregir y mejorar transcripciones de sermones, manteniendo su contenido esencial intacto."},
                {"role": "user", "content": prompt + transcripcion}
            ],
            temperature=0.3
        )
        return respuesta.choices[0].message.content
    except Exception as e:
        print(f"Error al comunicarse con la API de OpenAI: {e}")
        return None

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
    
    # Obtener la clave API de OpenAI
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: Se requiere una clave API de OpenAI. Proporcione --api_key o establezca la variable de entorno OPENAI_API_KEY.")
        return
    
    # Inicializar el cliente de OpenAI
    cliente = OpenAI(api_key=api_key)
    
    # Procesar la transcripción
    print(f"Leyendo transcripción: {args.input}")
    transcripcion = leer_transcripcion(args.input)
    if not transcripcion:
        return
    
    print(f"Enviando a {args.model} para corrección...")
    inicio = time.time()
    transcripcion_corregida = corregir_con_gpt(cliente, transcripcion, args.model)
    fin = time.time()
    
    if not transcripcion_corregida:
        return
    
    print(f"Corrección completada en {fin - inicio:.2f} segundos")
    guardar_transcripcion_corregida(transcripcion_corregida, args.output)
    
    # Mostrar estadísticas
    caracteres_original = len(transcripcion)
    caracteres_corregido = len(transcripcion_corregida)
    print(f"\nEstadísticas:")
    print(f"- Caracteres originales: {caracteres_original}")
    print(f"- Caracteres corregidos: {caracteres_corregido}")
    print(f"- Diferencia: {caracteres_corregido - caracteres_original} caracteres")

if __name__ == "__main__":
    main()
