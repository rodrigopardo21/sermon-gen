"""
Script Principal para Transcripción y Generación de Contenido de Sermones
Este script coordina el proceso completo de transcripción, corrección,
extracción de ideas clave y generación de videos, organizando todo en
una estructura de carpetas para cada sermón.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from src.transcription.transcriber import SermonTranscriber
from src.correction.transcription_corrector import leer_transcripcion, corregir_con_claude, guardar_transcripcion_corregida, corregir_transcripcion_por_segmentos
from src.correction.transcription_line_corrector import corregir_transcripcion_completa
from src.content_gen.key_ideas_extractor import extraer_y_guardar_ideas_clave
from src.content_gen.editor_ideas_clave import convertir_json_a_txt, convertir_txt_a_json
# Importamos el nuevo gestor de proyectos
from src.management.project_manager import SermonProjectManager
from src.content_gen.prompt_generator import PromptGenerator
from src.audio.audio_processor import AudioProcessor
from anthropic import Anthropic
# Cargamos las variables de entorno para manejar información sensible de manera segura
load_dotenv()

def main():
    """
    Función principal que coordina el proceso completo de transcripción,
    corrección, extracción de ideas clave y generación de videos.
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

    # Inicializamos el gestor de proyectos
    project_manager = SermonProjectManager(base_dir)

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
            
            # Creamos un nuevo proyecto para este video
            sermón_titulo = os.path.splitext(video_filename)[0]
            project_metadata = project_manager.create_project_structure(video_filename, sermón_titulo)
            
            # Copiamos el archivo de entrada al directorio del proyecto
            input_path = os.path.join(input_dir, video_filename)
            project_manager.copy_input_file(input_path, project_metadata)
            
            # Actualizamos el estado del proyecto
            project_manager.update_project_status(project_metadata["project_id"], "transcription_started")
            
            try:
                # Realizamos la transcripción
                print(f"Iniciando transcripción de {video_filename}...")
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
                    
                    # Organizamos los archivos de transcripción en el proyecto
                    transcription_files = {
                        "txt": transcription_path,
                        "json": transcript_json if os.path.exists(transcript_json or "") else None
                    }
                    project_manager.organize_transcription_files(project_metadata, transcription_files)
                    
                    # Comprobamos si hay segmentos de audio y los organizamos
                    audio_segments = []
                    audio_base_name = f"{video_name_base}_audio"
                    for i in range(1, 10):  # Asumimos un máximo de 10 segmentos
                        segment_path = os.path.join(output_dir, f"{audio_base_name}_segment_{i}.mp3")
                        if os.path.exists(segment_path):
                            audio_segments.append(segment_path)
                    
                    # También incluimos el archivo de audio WAV principal
                    wav_path = os.path.join(output_dir, f"{audio_base_name}.wav")
                    if os.path.exists(wav_path):
                        audio_segments.append(wav_path)
                    
                    if audio_segments:
                        project_manager.organize_audio_files(project_metadata, audio_segments)
                    
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
                            # Actualizamos el estado del proyecto
                            project_manager.update_project_status(
                                project_metadata["project_id"], 
                                "correction_completed",
                                {"corrected_file": corrected_file}
                            )
                            
                            # Organizamos el archivo corregido en el proyecto
                            corrected_files = {"corrected": corrected_file}
                            project_manager.organize_transcription_files(project_metadata, corrected_files)
                            
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
                                # Actualizamos el estado del proyecto
                                project_manager.update_project_status(
                                    project_metadata["project_id"], 
                                    "key_ideas_extracted",
                                    {"ideas_file": ruta_ideas}
                                )
                                
                                print(f"Ideas clave extraídas y guardadas en: {ruta_ideas}")
                                
                                # Convertir a formato TXT para edición
                                ruta_txt = convertir_json_a_txt(ruta_ideas)
                                if ruta_txt:
                                    print(f"Se ha creado un archivo de texto editable en: {ruta_txt}")
                                    print("Puedes abrir este archivo, editar las ideas y luego convertirlo de vuelta a JSON.")
                                    
                                    # Organizamos los archivos de ideas clave en el proyecto
                                    ideas_files = {
                                        "ideas_json": ruta_ideas,
                                        "ideas_txt": ruta_txt
                                    }
                                    project_manager.organize_transcription_files(project_metadata, ideas_files)
                                    
                                    # Añadir marcas de tiempo a las ideas clave y crear audio para video corto
                                    print("\nPreparando audio para video corto...")
                                    audio_processor = AudioProcessor()
                                    
                                    # Añadir marcas de tiempo a las ideas clave
                                    enriched_json = audio_processor.add_timestamps_to_ideas(
                                        ruta_ideas,
                                        transcript_json,
                                        os.path.join(project_metadata["directories"]["transcription"], f"{Path(base_name).stem}_ideas_clave_with_timestamps.json")
                                    )
                                    
                                    if enriched_json:
                                        # Crear audio para el video corto
                                        audio_for_short = audio_processor.extract_audio_for_key_ideas(
                                            enriched_json,
                                            os.path.join(project_metadata["directories"]["audio"], f"{video_name_base}_audio.wav"),
                                            os.path.join(project_metadata["directories"]["audio"], f"{video_name_base}_ideas_clave.wav")
                                        )
                                        
                                        # Generar archivo de subtítulos SRT para el video corto
                                        subtitles_path = audio_processor.generate_subtitle_file(
                                            enriched_json,
                                            os.path.join(project_metadata["directories"]["transcription"], f"{Path(base_name).stem}_ideas_clave_subtitles.srt"),
                                            "srt"
                                        )
                                        
                                        # Generar prompts para nim.video
                                        print("\nGenerando prompts para nim.video...")
                                        prompt_generator = PromptGenerator()
                                        
                                        # Obtener duraciones de audio
                                        audio_completo_path = os.path.join(project_metadata["directories"]["audio"], f"{video_name_base}_audio.wav")
                                        duracion_audio_completo = "00:30:00"  # Valor predeterminado
                                        
                                        # Intentar obtener la duración real del audio completo
                                        duracion_segundos = audio_processor.get_audio_duration(audio_completo_path)
                                        if duracion_segundos:
                                            duracion_audio_completo = audio_processor.format_duration(duracion_segundos)
                                        
                                        # Duración del audio de ideas clave
                                        duracion_audio_ideas = "00:01:10"  # Valor predeterminado
                                        
                                        # Si existe el archivo de audio para ideas clave, obtener su duración
                                        if audio_for_short and os.path.exists(audio_for_short):
                                            duracion_segundos = audio_processor.get_audio_duration(audio_for_short)
                                            if duracion_segundos:
                                                duracion_audio_ideas = audio_processor.format_duration(duracion_segundos)
                                        
                                        print(f"Duración del audio completo: {duracion_audio_completo}")
                                        print(f"Duración del audio de ideas clave: {duracion_audio_ideas}")
                                        
                                        prompt_corto, prompt_largo, temas = prompt_generator.generar_prompts_para_sermon(
                                            ruta_ideas,
                                            sermón_titulo,
                                            duracion_audio_completo,
                                            duracion_audio_ideas
                                        )
                                        
                                        # Guardar los prompts en el directorio del proyecto
                                        proyecto_dir = project_metadata["directories"]["project"]
                                        ruta_prompt_corto, ruta_prompt_largo = prompt_generator.guardar_prompts(
                                            proyecto_dir, prompt_corto, prompt_largo
                                        )
                                        
                                        if ruta_prompt_corto and ruta_prompt_largo:
                                            print(f"Prompts para nim.video guardados en el directorio del proyecto:")
                                            print(f"- Video corto (reel/short): {os.path.basename(ruta_prompt_corto)}")
                                            print(f"- Video largo (sermón completo): {os.path.basename(ruta_prompt_largo)}")
                                            print("Puedes copiar y pegar estos prompts en nim.video para generar tus videos.")
                                            
                                            # Actualizar el estado del proyecto
                                            project_manager.update_project_status(
                                                project_metadata["project_id"],
                                                "prompts_generated",
                                                {
                                                    "prompts": {
                                                        "video_corto": ruta_prompt_corto,
                                                        "video_largo": ruta_prompt_largo,
                                                        "temas_detectados": temas
                                                    },
                                                    "audio_ideas_clave": audio_for_short,
                                                    "subtitulos_ideas_clave": subtitles_path
                                                }
                                            )
                                        else:
                                            print("No se pudieron generar los prompts para nim.video.")
                                    else:
                                        print("No se pudieron añadir marcas de tiempo a las ideas clave.")
                            else:
                                print("No se pudieron extraer las ideas clave. Continuando con el resto del proceso.")
                        else:
                            print("Error durante la corrección con Claude.")
                    else:
                        print(f"No se pudo encontrar el archivo de transcripción: {transcription_path}")
                else:
                    print("No se pudo generar la transcripción.")
                    continue
                
                # Actualizamos el estado final del proyecto
                project_manager.update_project_status(
                    project_metadata["project_id"], 
                    "processing_completed",
                    {"status_message": "Transcripción, corrección e ideas clave completadas"}
                )
                
            except Exception as e:
                print(f"Error procesando {video_filename}: {str(e)}")
                # Registramos el error en el proyecto
                project_manager.update_project_status(
                    project_metadata["project_id"], 
                    "error",
                    {"error_message": str(e)}
                )
                import traceback
                traceback.print_exc()
                continue

        print("\nAhora puedes revisar las transcripciones corregidas en la carpeta output_transcriptions/corrected.")
        print(f"Las transcripciones corregidas tienen '_corregido_{metodo_correccion}' en el nombre del archivo.")
        print("Las ideas clave extraídas se guardan como '_ideas_clave.json' en la misma carpeta.")
        print("Para cada archivo JSON de ideas clave, se genera un archivo TXT editable.")
        print("Una vez revisadas, puedes continuar con la generación de contenido multimedia.")

        print("\n¡Proceso completado!")
        print("Cada sermón procesado ha sido organizado en su propia carpeta dentro de sermon_projects/")
        print("Proyectos procesados:")
        for project in project_manager.list_projects():
            status_icon = "✅" if project["status"] == "processing_completed" else "❌"
            print(f"{status_icon} {project['sermon_title']} (ID: {project['project_id']})")

    except Exception as e:
        print(f"Error en la ejecución del programa: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
