"""
Script Principal para Transcripción y Corrección de Sermones
Este script demuestra el uso de nuestro sistema de transcripción, corrección automática
y generación de contenido para redes sociales. Actúa como un punto de entrada que coordina
todo el proceso de manera organizada y segura.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from src.transcription.transcriber import SermonTranscriber
from src.correction.transcription_corrector import leer_transcripcion, corregir_con_claude, guardar_transcripcion_corregida, corregir_transcripcion_por_segmentos
# Importamos el nuevo módulo de corrección línea por línea
from src.correction.transcription_line_corrector import corregir_transcripcion_completa
# Importamos el nuevo módulo de extracción de ideas clave
from src.content_gen.key_ideas_extractor import extraer_y_guardar_ideas_clave
# Importamos el editor de ideas clave
from src.content_gen.editor_ideas_clave import convertir_json_a_txt, convertir_txt_a_json
# Importamos el generador de videos con stock
from src.content_gen.stock_video_generator import StockVideoGenerator
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
    
    # Inicializamos el generador de videos
    video_generator = StockVideoGenerator(base_dir=base_dir)
    
    # Creamos los directorios si no existen
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'sermones'), exist_ok=True)

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
            output_dir=os.path.join(base_dir, 'output_transcriptions'),  # Temporal, luego moveremos los archivos
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
            
            # Solicitar información del sermón
            titulo_sermon = input("Por favor, ingresa el título del sermón: ")
            fecha_str = input("Ingresa la fecha del sermón (YYYY-MM-DD) o deja en blanco para usar la fecha actual: ")
            
            # Usar fecha actual si no se proporciona
            if not fecha_str:
                fecha_sermon = datetime.now().strftime("%Y-%m-%d")
            else:
                fecha_sermon = fecha_str
            
            # Crear estructura de directorios para este sermón
            sermon_dir = video_generator.crear_directorio_sermon(titulo_sermon, fecha_sermon)
            
            # Definir rutas para este sermón
            transcripcion_dir = os.path.join(sermon_dir, "transcripcion")
            ideas_clave_dir = os.path.join(sermon_dir, "ideas_clave")
            videos_cortos_dir = os.path.join(sermon_dir, "videos_cortos")
            video_largo_dir = os.path.join(sermon_dir, "video_largo")
            
            try:
                # Realizamos la transcripción
                print("\nRealizando transcripción con Whisper...")
                transcription_file = transcriber.process_video(video_filename)
                
                # Verificamos que la transcripción se ha generado correctamente
                if transcription_file:
                    if isinstance(transcription_file, dict):
                        # Intentamos extraer la ruta del diccionario
                        print("transcription_file es un diccionario con claves:", transcription_file.keys())
                        
                        # Verificamos si ya tenemos un archivo de transcripción en texto plano
                        video_name = transcription_file.get("video_filename", video_filename)
                        video_name_base = Path(video_name).stem
                        transcript_txt = os.path.join(transcriber.output_dir, f"{video_name_base}_transcript.txt")
                        
                        # Guardamos también la ruta al archivo JSON para el nuevo método
                        transcript_json = os.path.join(transcriber.output_dir, f"{video_name_base}_transcription.json")
                        
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
                    
                    # Copiar los archivos de transcripción a la carpeta del sermón
                    if os.path.exists(transcription_path):
                        # Copiar el archivo de transcripción
                        sermon_transcript_txt = os.path.join(transcripcion_dir, f"{video_name_base}_transcript.txt")
                        shutil.copy2(transcription_path, sermon_transcript_txt)
                        
                        # Copiar el archivo de audio
                        audio_path = os.path.join(transcriber.output_dir, f"{video_name_base}_audio.wav")
                        if os.path.exists(audio_path):
                            sermon_audio_path = os.path.join(transcripcion_dir, f"{video_name_base}_audio.wav")
                            shutil.copy2(audio_path, sermon_audio_path)
                        
                        # Actualizar la ruta a la transcripción
                        transcription_path = sermon_transcript_txt
                        
                        # Definimos la ruta para la transcripción corregida
                        base_name = os.path.basename(transcription_path)
                        
                        # Creamos rutas de salida diferentes según el método
                        if metodo_correccion == "segmentos":
                            corrected_file = os.path.join(transcripcion_dir, f"{Path(base_name).stem}_corregido_segmentos.txt")
                            print(f"\nEnviando a Claude para corrección automática por segmentos...")
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
                            corrected_file = os.path.join(transcripcion_dir, f"{Path(base_name).stem}_corregido_lineas.txt")
                            print(f"\nEnviando a Claude para corrección línea por línea...")
                            modelo_claude = "claude-3-7-sonnet-20250219"
                            
                            # Usamos el nuevo método de corrección
                            exito, texto_corregido = corregir_transcripcion_completa(
                                cliente_anthropic,
                                transcription_path,
                                transcript_json if transcript_json and os.path.exists(transcript_json) else None,
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
                            ideas_path = os.path.join(ideas_clave_dir, f"{Path(base_name).stem}_ideas_clave.json")
                            exito_ideas, ruta_ideas = extraer_y_guardar_ideas_clave(
                                cliente_anthropic,
                                corrected_file,
                                modelo_claude
                            )
                            
                            # Copiar el archivo de ideas clave a la carpeta del sermón
                            if exito_ideas and os.path.exists(ruta_ideas):
                                shutil.copy2(ruta_ideas, ideas_path)
                                
                                # Actualizar la ruta a las ideas clave
                                ruta_ideas = ideas_path
                                
                                print(f"Ideas clave extraídas y guardadas en: {ruta_ideas}")
                                
                                # Convertir a formato TXT para edición
                                ruta_txt = convertir_json_a_txt(ruta_ideas)
                                if ruta_txt:
                                    print(f"Se ha creado un archivo de texto editable en: {ruta_txt}")
                                    print("Puedes abrir este archivo, editar las ideas y luego convertirlo de vuelta a JSON.")
                                    
                                    # Preguntar si el usuario quiere editar las ideas clave
                                    editar_ideas = input("\n¿Quieres editar las ideas clave ahora? (s/n): ")
                                    
                                    if editar_ideas.lower() == 's':
                                        print(f"Por favor, edita el archivo: {ruta_txt}")
                                        print("Presiona Enter cuando hayas terminado...")
                                        input()
                                        
                                        # Convertir de vuelta a JSON
                                        ruta_ideas_editado = os.path.join(ideas_clave_dir, f"{Path(base_name).stem}_ideas_clave_editado.json")
                                        convertir_txt_a_json(ruta_txt, ruta_ideas_editado)
                                        ruta_ideas = ruta_ideas_editado
                                    
                                    # Preguntar si el usuario quiere generar videos ahora o esperar edición
                                    generar_videos_ahora = input("\n¿Quieres generar videos ahora con las ideas extraídas? (s/n): ")
                                    
                                    if generar_videos_ahora.lower() == 's':
                                        # Obtener la ruta del audio
                                        sermon_audio_path = os.path.join(transcripcion_dir, f"{video_name_base}_audio.wav")
                                        
                                        if os.path.exists(sermon_audio_path):
                                            print("\nGenerando videos a partir de las ideas clave...")
                                            
                                            # Generar videos cortos para redes sociales
                                            print("Generando videos cortos para redes sociales...")
                                            videos_generados = video_generator.generar_videos_ideas(
                                                ruta_ideas, 
                                                sermon_audio_path, 
                                                videos_cortos_dir
                                            )
                                            
                                            if videos_generados:
                                                print(f"\nSe han generado {len(videos_generados)} videos cortos:")
                                                for video in videos_generados:
                                                    print(f"- {video}")
                                            else:
                                                print("No se pudieron generar los videos cortos.")
                                                
                                            # Preguntar si el usuario quiere generar el video completo
                                            generar_completo = input("\n¿Quieres generar el video completo del sermón con subtítulos? (s/n): ")
                                            
                                            if generar_completo.lower() == 's':
                                                # Verificar que existe el video original
                                                video_path = os.path.join(input_dir, video_filename)
                                                if os.path.exists(video_path):
                                                    output_video = os.path.join(video_largo_dir, f"{video_name_base}_completo.mp4")
                                                    
                                                    print("\nGenerando video completo con subtítulos...")
                                                    video_generator.generar_video_sermon_completo(
                                                        video_path,
                                                        corrected_file,
                                                        output_video
                                                    )
                                                else:
                                                    print(f"No se encontró el video original: {video_path}")
                                        else:
                                            print(f"No se encontró el archivo de audio: {sermon_audio_path}")
                                            print("Asegúrate de que el archivo de audio existe antes de generar videos.")
                                    else:
                                        print("\nPuedes generar videos más tarde utilizando el generador de videos.")
                            else:
                                print("No se pudieron extraer las ideas clave. Continuando con el resto del proceso.")
                        else:
                            print("Error durante la corrección con Claude.")
                    else:
                        print(f"No se pudo encontrar el archivo de transcripción: {transcription_path}")
                else:
                    print("No se pudo generar la transcripción.")
                    continue
                
            except Exception as e:
                print(f"Error procesando {video_filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print("\n¡Proceso completado!")
        print("Todos los archivos han sido organizados en carpetas por sermón en el directorio 'sermones/'")
        print("La estructura de cada sermón incluye:")
        print("- transcripcion/: Archivos de transcripción original y corregida")
        print("- ideas_clave/: Ideas clave extraídas en formato JSON y editable")
        print("- videos_cortos/: Videos generados para redes sociales")
        print("- video_largo/: Video completo del sermón con subtítulos")

    except Exception as e:
        print(f"Error en la ejecución del programa: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
