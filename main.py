"""
Script Principal para Transcripción, Corrección y Generación de Videos de Sermones

Este script actúa como punto de entrada que coordina todo el proceso de procesamiento
de sermones, desde la transcripción inicial con Whisper hasta la generación de videos
para YouTube y clips cortos para redes sociales.

El flujo completo incluye:
1. Recorte de videos con FFMPEG
2. Transcripción de audio utilizando Whisper API
3. Corrección automática de transcripciones con Claude
4. Extracción de ideas clave estructuradas en tres actos narrativos
5. Generación de imágenes para el sermón completo y las ideas clave
6. Creación de videos con movimiento, audio, subtítulos y logos
7. Organización de todos los archivos en una estructura coherente
"""

import os
import sys
import argparse
from pathlib import Path
import time
import shutil
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sermon_gen.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importamos los módulos específicos del proyecto
from src.transcription.transcriber import SermonTranscriber
from src.correction.transcription_corrector import leer_transcripcion, corregir_con_claude, guardar_transcripcion_corregida, corregir_transcripcion_por_segmentos
from src.correction.transcription_line_corrector import corregir_transcripcion_completa
from src.content_gen.key_ideas_extractor import extraer_y_guardar_ideas_clave
from src.content_gen.editor_ideas_clave import convertir_json_a_txt
from src.image_gen.sermon_video_creator import SermonVideoCreator
from anthropic import Anthropic

# Cargamos las variables de entorno para manejar información sensible de manera segura
load_dotenv()

def procesar_sermon(args):
    """
    Función principal que coordina todo el proceso de transcripción, 
    corrección, extracción de ideas clave y generación de videos.

    Args:
        args: Argumentos de línea de comandos con configuraciones del proceso
    """
    # 1. Configurar directorios de trabajo
    logger.info("Iniciando procesamiento de sermón")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, 'input_videos')
    output_dir = os.path.join(base_dir, 'output_transcriptions')
    corrected_dir = os.path.join(output_dir, 'corrected')

    # Crear directorios si no existen
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(corrected_dir, exist_ok=True)

    # 2. Inicializar clientes de API
    logger.info("Inicializando clientes de API")
    api_key_claude = os.getenv('ANTHROPIC_API_KEY')
    if not api_key_claude:
        logger.error("No se encontró la clave de API de Anthropic. Configure ANTHROPIC_API_KEY en el archivo .env")
        return False

    cliente_anthropic = Anthropic(api_key=api_key_claude)

    # Inicializar transcriptor (para Whisper API)
    whisper_api_key = os.getenv('OPENAI_API_KEY')
    if not whisper_api_key:
        logger.warning("No se encontró la clave de API de OpenAI para Whisper. Se omitirá la transcripción.")
    
    transcriber = None
    if whisper_api_key:
        transcriber = SermonTranscriber(
            input_dir=input_dir,
            output_dir=output_dir,
            api_key=whisper_api_key
        )

    # 3. Determinar método de corrección a utilizar
    metodo_correccion = args.correccion if args.correccion else "linea_por_linea"
    logger.info(f"Método de corrección seleccionado: {metodo_correccion}")

    # 4. Obtener lista de videos a procesar
    if args.video:
        # Si se especificó un video, usar solo ese
        videos = [args.video]
        if not os.path.exists(os.path.join(input_dir, args.video)):
            logger.error(f"El video especificado no existe: {args.video}")
            return False
    else:
        # Si no, procesar todos los videos en el directorio de entrada
        videos = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.MP4'))]
    
    if not videos:
        logger.error(f"No se encontraron archivos de video en {input_dir}")
        logger.info("Por favor, coloque sus videos en la carpeta 'input_videos'")
        return False

    # 5. Procesar cada video
    for video_filename in videos:
        logger.info(f"\nProcesando video: {video_filename}")
        video_name_base = Path(video_filename).stem
        
        try:
            # 5.1 Fase de transcripción (si se activa)
            transcription_path = None
            transcript_json = None
            
            if args.transcribe and transcriber:
                logger.info("Iniciando transcripción con Whisper API")
                transcription_file = transcriber.process_video(video_filename)
                
                # Extraer las rutas de los archivos generados
                if isinstance(transcription_file, dict):
                    logger.debug(f"Resultado de transcripción: {transcription_file.keys()}")
                    transcript_txt = os.path.join(output_dir, f"{video_name_base}_transcript.txt")
                    transcript_json = os.path.join(output_dir, f"{video_name_base}_transcription.json")
                    
                    if os.path.exists(transcript_txt):
                        transcription_path = transcript_txt
                        logger.info(f"Transcripción generada: {transcription_path}")
                    else:
                        transcription_path = transcript_txt  # Usar esta ruta aunque no exista
                else:
                    transcription_path = transcription_file
            else:
                # Si no se activa la transcripción, buscar archivos existentes
                transcript_txt = os.path.join(output_dir, f"{video_name_base}_transcript.txt")
                transcript_json = os.path.join(output_dir, f"{video_name_base}_transcription.json")
                
                if os.path.exists(transcript_txt):
                    transcription_path = transcript_txt
                    logger.info(f"Usando transcripción existente: {transcription_path}")
                else:
                    logger.error(f"No se encontró archivo de transcripción para {video_filename}")
                    continue
            
            # 5.2 Fase de corrección (si se activa)
            corrected_file = None
            
            if args.corregir and transcription_path and os.path.exists(transcription_path):
                logger.info("Iniciando corrección de transcripción con Claude")
                
                # Crear ruta para archivo corregido según el método
                if metodo_correccion == "segmentos":
                    corrected_file = os.path.join(corrected_dir, f"{video_name_base}_corregido_segmentos.txt")
                    logger.info("Usando método de corrección por segmentos")
                    
                    # Definir tamaño de segmento para la corrección
                    tamano_segmento = 1500
                    
                    exito, caracteres_original, caracteres_corregido = corregir_transcripcion_por_segmentos(
                        cliente_anthropic, 
                        transcription_path, 
                        corrected_file, 
                        "claude-3-7-sonnet-20250219", 
                        tamano_segmento=tamano_segmento
                    )
                else:  # "linea_por_linea"
                    corrected_file = os.path.join(corrected_dir, f"{video_name_base}_corregido_lineas.txt")
                    logger.info("Usando método de corrección línea por línea")
                    
                    # Usar método de corrección línea por línea
                    exito, texto_corregido = corregir_transcripcion_completa(
                        cliente_anthropic,
                        transcription_path,
                        # Usar JSON si existe
                        transcript_json if transcript_json and os.path.exists(transcript_json) else None,
                        corrected_file,
                        "claude-3-7-sonnet-20250219"
                    )
                    
                    # Calcular estadísticas
                    if exito:
                        texto_original = leer_transcripcion(transcription_path)
                        caracteres_original = len(texto_original) if texto_original else 0
                        caracteres_corregido = len(texto_corregido) if texto_corregido else 0
                
                if exito and corrected_file:
                    logger.info(f"Transcripción corregida guardada en: {corrected_file}")
                    logger.info(f"Estadísticas de corrección:")
                    logger.info(f"- Caracteres originales: {caracteres_original}")
                    logger.info(f"- Caracteres corregidos: {caracteres_corregido}")
                    logger.info(f"- Diferencia: {caracteres_corregido - caracteres_original} caracteres")
                    if caracteres_original > 0:
                        logger.info(f"- % cambio: {((caracteres_corregido - caracteres_original) / caracteres_original) * 100:.2f}%")
                else:
                    logger.error("Error durante la corrección. Continuando con el archivo original.")
                    corrected_file = transcription_path
            else:
                # Si no se activa la corrección o no hay transcripción, buscar archivos existentes
                corrected_file_base = os.path.join(corrected_dir, f"{video_name_base}_corregido_lineas.txt")
                if os.path.exists(corrected_file_base):
                    corrected_file = corrected_file_base
                    logger.info(f"Usando archivo corregido existente: {corrected_file}")
                else:
                    corrected_file = transcription_path  # Usar transcripción sin corregir
                    logger.warning("No se encontró archivo corregido. Usando transcripción sin corregir.")
            
            # 5.3 Fase de extracción de ideas clave (si se activa)
            ideas_path = None
            
            if args.ideas and corrected_file and os.path.exists(corrected_file):
                logger.info("Extrayendo ideas clave con Claude")
                exito_ideas, ruta_ideas = extraer_y_guardar_ideas_clave(
                    cliente_anthropic,
                    corrected_file,
                    "claude-3-7-sonnet-20250219"
                )
                
                if exito_ideas:
                    ideas_path = ruta_ideas
                    logger.info(f"Ideas clave guardadas en: {ideas_path}")
                    
                    # Convertir a formato TXT para edición
                    ruta_txt = convertir_json_a_txt(ruta_ideas)
                    if ruta_txt:
                        logger.info(f"Versión editable de ideas clave: {ruta_txt}")
                else:
                    logger.error("Error extrayendo ideas clave")
            else:
                # Buscar archivo de ideas existente
                ideas_file = os.path.join(corrected_dir, f"{video_name_base}_corregido_lineas_ideas_clave.json")
                if os.path.exists(ideas_file):
                    ideas_path = ideas_file
                    logger.info(f"Usando archivo de ideas existente: {ideas_path}")
            
            # 5.4 Fase de generación de videos (si se activa)
            if args.videos:
                if not corrected_file or not os.path.exists(corrected_file):
                    logger.error("No se puede generar video sin una transcripción válida")
                    continue
                
                logger.info("Iniciando generación de videos")
                
                # Inicializar creador de videos
                # Buscar logos en la ubicación predeterminada
                logos_paths = []
                assets_dir = os.path.join(base_dir, "assets")
                logos_dir = os.path.join(assets_dir, "logos")
                
                # Crear directorio de assets si no existe
                if not os.path.exists(assets_dir):
                    os.makedirs(assets_dir, exist_ok=True)
                    logger.info(f"Creado directorio de assets: {assets_dir}")
                
                # Crear directorio de logos si no existe
                if not os.path.exists(logos_dir):
                    os.makedirs(logos_dir, exist_ok=True)
                    logger.info(f"Creado directorio de logos: {logos_dir}")
                    logger.info(f"Coloque sus logos en: {logos_dir}")
                else:
                    # Buscar logos existentes
                    for logo_file in os.listdir(logos_dir):
                        if logo_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                            logos_paths.append(os.path.join(logos_dir, logo_file))
                    
                    if logos_paths:
                        logger.info(f"Se encontraron {len(logos_paths)} logos en {logos_dir}")
                    else:
                        logger.warning(f"No se encontraron logos en {logos_dir}")
                
                # Crear el generador de videos
                try:
                    video_creator = SermonVideoCreator(
                        project_dir=base_dir,
                        sermon_name=video_name_base,
                        logos_paths=logos_paths,
                        use_cache=not args.no_cache
                    )
                    
                    # Procesar el sermón
                    sermon_video, idea_videos = video_creator.process_sermon(num_images=args.num_imagenes)
                    
                    if sermon_video:
                        logger.info(f"Video completo del sermón generado: {sermon_video}")
                    
                    if idea_videos:
                        logger.info(f"Videos de ideas clave generados:")
                        for video in idea_videos:
                            logger.info(f"- {video}")
                    
                except Exception as e:
                    logger.error(f"Error durante generación de videos: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # 5.5 Fase de preparación para redes sociales (si se activa)
            if args.social and transcriber and transcription_path and os.path.exists(transcription_path):
                try:
                    logger.info("Preparando contenido para redes sociales")
                    social_content = transcriber.prepare_social_media_content(transcription_path)
                    
                    # Resumen de contenido generado
                    logger.info("Contenido para redes sociales:")
                    logger.info(f"- Segmentos para YouTube: {len(social_content['youtube'])}")
                    logger.info(f"- Clips para Reels: {len(social_content['reels'])}")
                    logger.info(f"- Clips para TikTok: {len(social_content['tiktok'])}")
                except Exception as e:
                    logger.error(f"Error generando contenido para redes sociales: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error procesando {video_filename}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("\n¡Proceso completado!")
    return True

def main():
    """Punto de entrada principal del programa."""
    # Crear el parser de argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Sistema de procesamiento de sermones')
    
    # Argumentos generales
    parser.add_argument('--video', type=str, help='Nombre del archivo de video a procesar (si se omite, se procesan todos)')
    
    # Activar/desactivar etapas
    parser.add_argument('--transcribe', action='store_true', help='Activar transcripción con Whisper')
    parser.add_argument('--corregir', action='store_true', help='Activar corrección con Claude')
    parser.add_argument('--ideas', action='store_true', help='Activar extracción de ideas clave')
    parser.add_argument('--videos', action='store_true', help='Activar generación de videos')
    parser.add_argument('--social', action='store_true', help='Activar preparación para redes sociales')
    parser.add_argument('--all', action='store_true', help='Activar todas las etapas')
    
    # Opciones específicas
    parser.add_argument('--correccion', choices=['segmentos', 'linea_por_linea'], 
                        help='Método de corrección a utilizar (default: linea_por_linea)')
    parser.add_argument('--num-imagenes', type=int, default=10, 
                        help='Número de imágenes para el video completo (default: 10)')
    parser.add_argument('--no-cache', action='store_true', 
                        help='Desactivar caché de imágenes (genera nuevas imágenes siempre)')
    
    args = parser.parse_args()
    
    # Si se selecciona --all, activar todas las etapas
    if args.all:
        args.transcribe = True
        args.corregir = True
        args.ideas = True
        args.videos = True
        args.social = True
    
    # Si no se selecciona ninguna etapa, mostrar ayuda
    if not any([args.transcribe, args.corregir, args.ideas, args.videos, args.social]):
        parser.print_help()
        print("\nDebe seleccionar al menos una etapa del proceso o usar --all")
        return
    
    # Procesar los sermones
    try:
        procesar_sermon(args)
    except Exception as e:
        logger.error(f"Error en la ejecución del programa: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
