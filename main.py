"""
Script Principal para Transcripción y Corrección de Sermones
Este script demuestra el uso de nuestro sistema de transcripción, corrección automática
y generación de contenido para redes sociales. Actúa como un punto de entrada que coordina
todo el proceso de manera organizada y segura.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from src.transcription.transcriber import SermonTranscriber
from src.correction.transcription_corrector import leer_transcripcion, corregir_con_claude, guardar_transcripcion_corregida, corregir_transcripcion_por_segmentos
# Importamos el nuevo módulo de corrección línea por línea
from src.correction.transcription_line_corrector import corregir_transcripcion_completa
# Importamos el nuevo módulo de extracción de ideas clave
from src.content_gen.key_ideas_extractor import extraer_y_guardar_ideas_clave
# Importamos el editor de ideas clave
from src.content_gen.editor_ideas_clave import convertir_json_a_txt
from anthropic import Anthropic

# Cargamos las variables de entorno para manejar información sensible de manera segura
load_dotenv()

def main():
    """
    Función principal que coordina el proceso de transcripción, corrección y generación de contenido.
    Esta función demuestra el flujo completo del proceso, desde la configuración
    inicial hasta la generación de contenido para redes sociales.
    """
    # Configuramos las rutas de los directorios de trabajo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, 'input_videos')
    output_dir = os.path.join(base_dir, 'output_transcriptions')
    corrected_dir = os.path.join(output_dir, 'corrected')

    # Creamos los directorios si no existen
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(corrected_dir, exist_ok=True)

    # Determinar qué método de corrección usar (por segmentos o línea por línea)
    metodo_correccion = "linea_por_linea"  # Opciones: "segmentos" o "linea_por_linea"

    try:
        # Obtenemos la clave de API de las variables de entorno
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("No se encontró la clave de API de Anthropic. Por favor, configura ANTHROPIC_API_KEY en el archivo .env")

        # Inicializamos el cliente de Anthropic para la corrección
        cliente_anthropic = Anthropic(api_key=api_key)

        # Inicializamos nuestro transcriptor (mantenemos OpenAI para Whisper)
        whisper_api_key = os.getenv('OPENAI_API_KEY')
        if not whisper_api_key:
            print("ADVERTENCIA: No se encontró la clave de API de OpenAI para Whisper. Algunas funciones podrían no estar disponibles.")
        
        transcriber = SermonTranscriber(
            input_dir=input_dir,
            output_dir=output_dir,
            api_key=whisper_api_key
        )

        # Lista de videos a procesar
        videos = [f for f in os.listdir(input_dir) if f.endswith('.mp4')]
        
        if not videos:
            print(f"No se encontraron archivos MP4 en {input_dir}")
            print("Por favor, coloca tus videos en la carpeta 'input_videos'")
            return

        # Procesamos cada video encontrado
        for video_filename in videos:
            print(f"\nProcesando video: {video_filename}")
            try:
                # Realizamos la transcripción
                transcription_file = transcriber.process_video(video_filename)
                
                # Verificamos que la transcripción se ha generado correctamente
                if transcription_file:
                    if isinstance(transcription_file, dict):
                        # Intentamos extraer la ruta del diccionario
                        print("transcription_file es un diccionario con claves:", transcription_file.keys())
                        
                        # Verificamos si ya tenemos un archivo de transcripción en texto plano
                        video_name = transcription_file.get("video_filename", video_filename)
                        video_name_base = Path(video_name).stem
                        transcript_txt = os.path.join(output_dir, f"{video_name_base}_transcript.txt")
                        
                        # Guardamos también la ruta al archivo JSON para el nuevo método
                        transcript_json = os.path.join(output_dir, f"{video_name_base}_transcription.json")
                        
                        if os.path.exists(transcript_txt):
                            transcription_path = transcript_txt
                            print(f"Usando archivo de transcripción existente: {transcription_path}")
                        else:
                            # Intentamos crear la ruta a partir de la información disponible
                            transcription_path = transcript_txt
                            print(f"Intentando usar ruta generada: {transcription_path}")
                    else:
                        transcription_path = transcription_file
                        # No tenemos JSON en este caso
                        transcript_json = None
                    
                    if os.path.exists(transcription_path):
                        # Definimos la ruta para la transcripción corregida
                        base_name = os.path.basename(transcription_path)
                        
                        # Creamos rutas de salida diferentes según el método
                        if metodo_correccion == "segmentos":
                            corrected_file = os.path.join(corrected_dir, f"{Path(base_name).stem}_corregido_segmentos.txt")
                            print(f"Enviando a Claude para corrección automática por segmentos...")
                            modelo_claude = "claude-3-7-sonnet-20250219"
                            
                            # Definimos un tamaño de segmento
                            tamano_segmento = 1500
                            
                            exito, caracteres_original, caracteres_corregido = corregir_transcripcion_por_segmentos(
                                cliente_anthropic, 
                                transcription_path, 
                                corrected_file, 
                                modelo_claude, 
                                tamano_segmento=tamano_segmento
                            )
                        else:  # "linea_por_linea"
                            corrected_file = os.path.join(corrected_dir, f"{Path(base_name).stem}_corregido_lineas.txt")
                            print(f"Enviando a Claude para corrección línea por línea...")
                            modelo_claude = "claude-3-7-sonnet-20250219"
                            
                            # Usamos el nuevo método de corrección
                            exito, texto_corregido = corregir_transcripcion_completa(
                                cliente_anthropic,
                                transcription_path,
                                transcript_json if os.path.exists(transcript_json or "") else None,
                                corrected_file,
                                modelo_claude
                            )
                            
                            # Calculamos estadísticas para mantener consistencia
                            if exito:
                                texto_original = leer_transcripcion(transcription_path)
                                caracteres_original = len(texto_original)
                                caracteres_corregido = len(texto_corregido)

                        if exito:
                            print(f"\nEstadísticas de corrección:")
                            print(f"- Caracteres originales: {caracteres_original}")
                            print(f"- Caracteres corregidos: {caracteres_corregido}")
                            print(f"- Diferencia: {caracteres_corregido - caracteres_original} caracteres")
                            print(f"- Porcentaje de cambio: {((caracteres_corregido - caracteres_original) / caracteres_original) * 100:.2f}%")
                            
                            # Después de la corrección, extraemos las ideas clave
                            print("\nExtrayendo ideas clave para generación de videos...")
                            exito_ideas, ruta_ideas = extraer_y_guardar_ideas_clave(
                                cliente_anthropic,
                                corrected_file,
                                modelo_claude
                            )
                            
                            if exito_ideas:
                                print(f"Ideas clave extraídas y guardadas en: {ruta_ideas}")
                                
                                # Convertir a formato TXT para edición
                                ruta_txt = convertir_json_a_txt(ruta_ideas)
                                if ruta_txt:
                                    print(f"Se ha creado un archivo de texto editable en: {ruta_txt}")
                                    print("Puedes abrir este archivo, editar las ideas y luego convertirlo de vuelta a JSON.")
                            else:
                                print("No se pudieron extraer las ideas clave. Continuando con el resto del proceso.")
                        else:
                            print("Error durante la corrección con Claude.")
                    else:
                        print(f"No se pudo encontrar el archivo de transcripción: {transcription_path}")
                else:
                    print("No se pudo generar la transcripción.")
                    continue
                
                try:
                    # Preparamos contenido para redes sociales solo si existe el archivo de transcripción
                    if os.path.exists(transcription_path):
                        social_content = transcriber.prepare_social_media_content(transcription_path)
                        
                        # Mostramos un resumen de los resultados
                        print("\nResumen de contenido generado:")
                        print(f"- Segmentos para YouTube: {len(social_content['youtube'])}")
                        print(f"- Clips para Reels: {len(social_content['reels'])}")
                        print(f"- Clips para TikTok: {len(social_content['tiktok'])}")
                    else:
                        print("No se puede generar contenido para redes sociales sin un archivo de transcripción válido.")
                except Exception as e:
                    print(f"Error generando contenido para redes sociales: {str(e)}")
                
            except Exception as e:
                print(f"Error procesando {video_filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print("\nAhora puedes revisar las transcripciones corregidas en la carpeta output_transcriptions/corrected.")
        print(f"Las transcripciones corregidas tienen '_corregido_{metodo_correccion}' en el nombre del archivo.")
        print("Las ideas clave extraídas se guardan como '_ideas_clave.json' en la misma carpeta.")
        print("Para cada archivo JSON de ideas clave, se genera un archivo TXT editable.")
        print("Una vez revisadas, puedes continuar con la generación de contenido multimedia.")

        print("\n¡Proceso completado!")
        print(f"Las transcripciones originales se han guardado en: {output_dir}")
        print(f"Las transcripciones corregidas se han guardado en: {corrected_dir}")

    except Exception as e:
        print(f"Error en la ejecución del programa: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
