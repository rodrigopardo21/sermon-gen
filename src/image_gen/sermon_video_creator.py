"""
Módulo principal para la creación de videos de sermones y clips para redes sociales.

Este módulo coordina el proceso completo de generación de videos de sermones y clips cortos,
incluyendo la sincronización de audio, la adición de subtítulos, y la generación de
movimiento en las imágenes para crear videos tipo reel/short.

Características principales:
    - Generación de videos completos de sermones
    - Generación de clips cortos para ideas clave (reels/shorts)
    - Sincronización de audio con imágenes en movimiento
    - Adición de subtítulos basados en la transcripción
    - Adición de logos como marca de agua
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
import time
import numpy as np
import shutil

# Añadir directorio padre al path para poder importar correctamente
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

# Importamos los módulos que ya hemos creado
from src.image_gen.image_generator import ImageGenerator, create_sermon_directory
from src.image_gen.video_animator import VideoAnimator

class SermonVideoCreator:
    """
    Clase para coordinar la creación de videos de sermones y clips para redes sociales.
    
    Esta clase utiliza los generadores de imágenes y animadores de video para
    producir los videos finales del sermón.
    
    Atributos:
        project_dir (str): Directorio raíz del proyecto
        sermon_dir (str): Directorio del sermón
        logos_paths (list): Lista de rutas a los logos
        use_cache (bool): Si se debe utilizar caché para las imágenes
    """
    
    def __init__(self, project_dir=None, sermon_name=None, logos_paths=None, use_cache=True):
        """
        Inicializa el creador de videos con las configuraciones necesarias.
        
        Args:
            project_dir (str): Directorio raíz del proyecto
            sermon_name (str): Nombre del sermón (para crear una carpeta específica)
            logos_paths (list): Lista de rutas a los logos para marca de agua
            use_cache (bool): Si se debe utilizar caché para las imágenes
        """
        # Si no se especifica, usar la raíz del proyecto actual
        if project_dir is None:
            # Determinar la raíz del proyecto (donde está setup.py o README.md)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(os.path.dirname(script_dir))
            
            # Verificar si estamos en la raíz del proyecto
            if not os.path.exists(os.path.join(project_dir, "output_transcriptions")):
                # Estamos en src/image_gen, subir un nivel más
                project_dir = os.path.dirname(project_dir)
        
        self.project_dir = project_dir
        self.logos_paths = logos_paths or []
        self.use_cache = use_cache
        
        # Directorios de entrada existentes
        self.input_dir = os.path.join(project_dir, "output_transcriptions")
        self.corrected_dir = os.path.join(self.input_dir, "corrected")
        
        # Verificar que existen los directorios de entrada
        if not os.path.exists(self.input_dir):
            raise ValueError(f"El directorio de transcripciones no existe: {self.input_dir}")
        
        if not os.path.exists(self.corrected_dir):
            raise ValueError(f"El directorio de transcripciones corregidas no existe: {self.corrected_dir}")
        
        # Crear directorio para el sermón específico si no se proporciona
        if sermon_name:
            self.sermon_name = sermon_name
        else:
            # Usar un nombre basado en la fecha actual
            from datetime import datetime
            self.sermon_name = f"sermon_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Crear estructura de directorios para el sermón
        self.sermon_dir = create_sermon_directory(self.sermon_name)
        
        # Inicializar generador de imágenes y animador de video
        self.image_generator = ImageGenerator(sermon_dir=self.sermon_dir, use_cache=use_cache)
        self.video_animator = VideoAnimator(sermon_dir=self.sermon_dir)
        
        # Directorios específicos dentro de la estructura
        self.images_dir = os.path.join(self.sermon_dir, "imagenes")
        self.videos_dir = os.path.join(self.sermon_dir, "videos")
        self.audio_dir = os.path.join(self.sermon_dir, "audio")
        self.trans_dir = os.path.join(self.sermon_dir, "transcripcion")
        self.ideas_dir = os.path.join(self.sermon_dir, "ideas_clave")
        
        print(f"SermonVideoCreator inicializado para: {self.sermon_name}")
        print(f"Leyendo datos desde: {self.input_dir}")
        print(f"Almacenando resultados en: {self.sermon_dir}")
    
    def copy_existing_files(self):
        """
        Copia los archivos existentes de transcripciones y audio a la estructura del sermón.
        
        Returns:
            tuple: (audio_path, transcript_path, ideas_path)
        """
        # Rutas a los archivos existentes
        existing_audio = os.path.join(self.input_dir, "sermon_recortado_audio.wav")
        existing_transcript = os.path.join(self.corrected_dir, "sermon_recortado_transcript_corregido_lineas.txt")
        existing_ideas_json = os.path.join(self.corrected_dir, "sermon_recortado_transcript_corregido_lineas_ideas_clave.json")
        existing_ideas_editable = os.path.join(self.corrected_dir, "sermon_recortado_transcript_corregido_lineas_ideas_clave_editable.txt")
        
        # Rutas de destino
        dest_audio = os.path.join(self.audio_dir, "sermon_audio.wav")
        dest_transcript = os.path.join(self.trans_dir, "transcripcion_corregida.txt")
        dest_ideas_json = os.path.join(self.ideas_dir, "ideas_clave.json")
        dest_ideas_editable = os.path.join(self.ideas_dir, "ideas_clave_editable.txt")
        
        # Copiar archivos si existen
        audio_path = None
        if os.path.exists(existing_audio):
            shutil.copy2(existing_audio, dest_audio)
            audio_path = dest_audio
            print(f"Audio copiado a: {dest_audio}")
        else:
            print(f"No se encontró el archivo de audio: {existing_audio}")
        
        transcript_path = None
        if os.path.exists(existing_transcript):
            shutil.copy2(existing_transcript, dest_transcript)
            transcript_path = dest_transcript
            print(f"Transcripción copiada a: {dest_transcript}")
        else:
            print(f"No se encontró el archivo de transcripción corregida: {existing_transcript}")
        
        ideas_path = None
        if os.path.exists(existing_ideas_json):
            shutil.copy2(existing_ideas_json, dest_ideas_json)
            ideas_path = dest_ideas_json
            print(f"Ideas clave JSON copiadas a: {dest_ideas_json}")
        else:
            print(f"No se encontró el archivo JSON de ideas clave: {existing_ideas_json}")
        
        if os.path.exists(existing_ideas_editable):
            shutil.copy2(existing_ideas_editable, dest_ideas_editable)
            print(f"Ideas clave editables copiadas a: {dest_ideas_editable}")
        
        return audio_path, transcript_path, ideas_path
    
    def generate_subtitles_from_transcript(self, transcript_path, audio_path, output_path=None):
        """
        Genera un archivo de subtítulos SRT a partir de la transcripción y el audio.
        
        Args:
            transcript_path (str): Ruta al archivo de transcripción
            audio_path (str): Ruta al archivo de audio (para determinar duración)
            output_path (str, opcional): Ruta para el archivo SRT
            
        Returns:
            str: Ruta al archivo SRT generado
        """
        if not os.path.exists(transcript_path):
            print(f"El archivo de transcripción no existe: {transcript_path}")
            return None
        
        if not output_path:
            base_name = os.path.splitext(os.path.basename(transcript_path))[0]
            output_path = os.path.join(self.videos_dir, f"{base_name}_subtitles.srt")
        
        # Leer el contenido de la transcripción
        with open(transcript_path, 'r', encoding='utf-8') as file:
            transcript_text = file.read()
        
        # Obtener la duración total del audio
        ffprobe_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
        ]
        try:
            duration_str = subprocess.check_output(ffprobe_cmd).decode('utf-8').strip()
            total_duration = float(duration_str)
            print(f"Duración total del audio: {total_duration} segundos")
        except subprocess.CalledProcessError:
            print("Error al determinar la duración del audio.")
            return None
        
        # Eliminar posibles encabezados de la transcripción
        lines = transcript_text.split('\n')
        content_start = 0
        for i, line in enumerate(lines):
            if "==========" in line:
                content_start = i + 1
                break
        
        # Tomar solo el contenido real de la transcripción
        content = '\n'.join(lines[content_start:])
        content = content.replace('\n\n', ' ').replace('\n', ' ')
        
        # Dividir en frases (puntos, interrogaciones, exclamaciones)
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Verificar que hay frases para generar subtítulos
        if not sentences:
            print("No se encontraron frases en la transcripción para generar subtítulos.")
            return None
        
        # Calcular tiempo aproximado por frase
        time_per_sentence = total_duration / len(sentences)
        
        # Generar archivo SRT
        with open(output_path, 'w', encoding='utf-8') as srt_file:
            for i, sentence in enumerate(sentences):
                start_time = i * time_per_sentence
                end_time = (i + 1) * time_per_sentence
                
                # Formatear tiempos para SRT (HH:MM:SS,mmm)
                start_formatted = self._format_srt_time(start_time)
                end_formatted = self._format_srt_time(end_time)
                
                # Escribir entrada de subtítulo
                srt_file.write(f"{i+1}\n")
                srt_file.write(f"{start_formatted} --> {end_formatted}\n")
                srt_file.write(f"{sentence}\n\n")
        
        print(f"Archivo de subtítulos generado: {output_path}")
        return output_path
    
    def _format_srt_time(self, seconds):
        """
        Formatea un tiempo en segundos al formato SRT (HH:MM:SS,mmm).
        
        Args:
            seconds (float): Tiempo en segundos
            
        Returns:
            str: Tiempo formateado para SRT
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def add_subtitles_to_video(self, video_path, subtitles_path, output_path=None):
        """
        Añade subtítulos a un video.
        
        Args:
            video_path (str): Ruta al video
            subtitles_path (str): Ruta al archivo SRT de subtítulos
            output_path (str, opcional): Ruta para el video con subtítulos
            
        Returns:
            str: Ruta al video con subtítulos
        """
        if not os.path.exists(video_path) or not os.path.exists(subtitles_path):
            print("No se encontró el video o los subtítulos.")
            return video_path
        
        if not output_path:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(os.path.dirname(video_path), f"{base_name}_with_subs.mp4")
        
        # Añadir subtítulos al video usando FFmpeg
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"subtitles={subtitles_path}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=4,Outline=1,Shadow=0,MarginV=30'",
            '-c:a', 'copy',
            output_path
        ]
        
        print(f"Añadiendo subtítulos al video...")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Video con subtítulos generado: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Error al añadir subtítulos: {e}")
            return video_path
    
    def generate_images_for_sermon(self, transcript_path, num_images=15):
        """
        Genera imágenes para el video completo del sermón.
        
        Args:
            transcript_path (str): Ruta al archivo de transcripción
            num_images (int): Número de imágenes a generar
            
        Returns:
            list: Lista de rutas a las imágenes generadas
        """
        if not os.path.exists(transcript_path):
            print(f"El archivo de transcripción no existe: {transcript_path}")
            return []
        
        # Leer la transcripción
        with open(transcript_path, 'r', encoding='utf-8') as file:
            transcript_text = file.read()
        
        # Eliminar posibles encabezados
        lines = transcript_text.split('\n')
        content_start = 0
        for i, line in enumerate(lines):
            if "==========" in line:
                content_start = i + 1
                break
        
        # Tomar solo el contenido real
        content = '\n'.join(lines[content_start:])
        
        # Dividir en segmentos aproximadamente iguales
        words = content.split()
        if len(words) == 0:
            print("Advertencia: La transcripción está vacía o no contiene palabras")
            return []
            
        words_per_segment = max(1, len(words) // num_images)
        segments = []
        
        for i in range(num_images):
            start_idx = i * words_per_segment
            end_idx = min((i + 1) * words_per_segment, len(words))
            
            # Si es el último segmento, incluir todas las palabras restantes
            if i == num_images - 1:
                end_idx = len(words)
            
            # Asegurarse de que tenemos un segmento no vacío
            if start_idx < end_idx:
                segment = ' '.join(words[start_idx:end_idx])
                segments.append(segment)
        
        # Generar una imagen para cada segmento
        image_paths = []
        
        for i, segment in enumerate(segments):
            try:
                print(f"Generando imagen {i+1}/{len(segments)}...")
                image_path = self.image_generator.generate_image(
                    segment,
                    f"sermon_image_{i+1:02d}"
                )
                
                if image_path:
                    image_paths.append(image_path)
                    
            except Exception as e:
                print(f"Error al generar imagen {i+1}: {e}")
        
        # Asegurarse de que generamos al menos una imagen
        if not image_paths:
            print("ADVERTENCIA: No se pudo generar ninguna imagen para el sermón.")
            
            # Intentar usar las imágenes de las ideas clave si están disponibles
            ideas_path = os.path.join(self.ideas_dir, "ideas_clave.json")
            if os.path.exists(ideas_path):
                print("Intentando usar imágenes de ideas clave como alternativa...")
                ideas_with_images = self.generate_images_for_key_ideas(ideas_path)
                
                # Extraer rutas de imágenes
                for idea in ideas_with_images:
                    if 'image_path' in idea and idea['image_path']:
                        image_paths.append(idea['image_path'])
        
        print(f"Se generaron {len(image_paths)} imágenes para el sermón completo.")
        return image_paths
    
    def generate_images_for_key_ideas(self, ideas_json_path):
        """
        Genera imágenes para las ideas clave.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON de ideas clave
            
        Returns:
            dict: Diccionario con ideas clave e imágenes generadas
        """
        if not os.path.exists(ideas_json_path):
            print(f"El archivo de ideas clave no existe: {ideas_json_path}")
            return {}
        
        # Leer el archivo JSON de ideas clave
        with open(ideas_json_path, 'r', encoding='utf-8') as file:
            ideas = json.load(file)
        
        # Generar una imagen para cada idea clave
        ideas_with_images = []
        
        for i, idea in enumerate(ideas):
            idea_text = idea.get('texto', '')
            context = idea.get('contexto', '')
            acto = idea.get('acto', 1)
            
            # Crear prompt específico según el acto y estilo
            prompt_text = f"{idea_text} {context}"
            
            # Estilo según el acto narrativo
            styles = {
                1: "inspiring landscape, aerial view, soft drone movement, golden hour lighting,",
                2: "dramatic nature scene, aerial view, soft movement, emotional lighting,",
                3: "hopeful natural vista, aerial shot, soft drone perspective, sunrise colors,"
            }
            
            style_prefix = styles.get(acto, styles[1])
            
            try:
                print(f"Generando imagen para idea clave {i+1}/{len(ideas)} (Acto {acto})...")
                image_path = self.image_generator.generate_image(
                    prompt_text,
                    f"idea_{i+1:02d}_acto{acto}",
                    style_prefix
                )
                
                if image_path:
                    idea['image_path'] = image_path
                    ideas_with_images.append(idea)
                    
            except Exception as e:
                print(f"Error al generar imagen para idea {i+1}: {e}")
                idea['image_path'] = None
                ideas_with_images.append(idea)
        
        print(f"Se generaron imágenes para {len(ideas_with_images)} ideas clave.")
        return ideas_with_images
    
    def create_full_sermon_video(self, audio_path, images, output_filename="sermon_completo.mp4"):
        """
        Crea el video completo del sermón con imágenes, audio y subtítulos.
        
        Args:
            audio_path (str): Ruta al archivo de audio del sermón
            images (list): Lista de rutas a las imágenes a usar
            output_filename (str): Nombre del archivo de salida
            
        Returns:
            str: Ruta al video final
        """
        if not audio_path or not os.path.exists(audio_path):
            print("No se proporcionó un archivo de audio válido.")
            return None
        
        if not images:
            print("No se proporcionaron imágenes para el video.")
            return None
        
        # Ruta para el video final
        output_path = os.path.join(self.videos_dir, output_filename)
        
        # Crear video completo con audio
        print("Creando video completo del sermón...")
        video_path = self.video_animator.create_sermon_video(
            images,
            audio_path,
            output_path,
            segment_duration=30.0,  # 30 segundos por imagen
            logos_paths=self.logos_paths
        )
        
        # Generar subtítulos si hay transcripción
        transcript_path = os.path.join(self.trans_dir, "transcripcion_corregida.txt")
        if os.path.exists(transcript_path):
            print("Generando subtítulos a partir de la transcripción...")
            
            # Generar archivo SRT
            subtitles_path = self.generate_subtitles_from_transcript(
                transcript_path,
                audio_path
            )
            
            if subtitles_path:
                # Añadir subtítulos al video
                final_video_path = self.add_subtitles_to_video(
                    video_path,
                    subtitles_path,
                    os.path.join(self.videos_dir, f"sermon_completo_con_subtitulos.mp4")
                )
                
                print(f"Video completo con subtítulos generado: {final_video_path}")
                return final_video_path
        
        print(f"Video completo generado: {video_path}")
        return video_path
    
    def create_key_idea_videos(self, ideas_with_images, audio_path):
        """
        Crea videos cortos para cada idea clave.
        
        Args:
            ideas_with_images (list): Lista de ideas clave con sus imágenes
            audio_path (str): Ruta al archivo de audio completo
            
        Returns:
            list: Lista de rutas a los videos generados
        """
        if not ideas_with_images:
            print("No se proporcionaron ideas clave con imágenes.")
            return []
        
        if not audio_path or not os.path.exists(audio_path):
            print("No se proporcionó un archivo de audio válido.")
            return []
        
        # Generar videos para cada idea clave
        idea_videos = []
        
        for i, idea in enumerate(ideas_with_images):
            image_path = idea.get('image_path')
            
            if not image_path or not os.path.exists(image_path):
                print(f"No se encontró imagen para la idea {i+1}. Saltando...")
                continue
            
            idea_text = idea.get('texto', '')
            pos_relativa = idea.get('posicion_relativa', i / len(ideas_with_images))
            duracion = idea.get('duracion_aproximada', 30.0)  # 30 segundos por defecto
            
            # Obtener duración total del audio
            ffprobe_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
            ]
            try:
                duration_str = subprocess.check_output(ffprobe_cmd).decode('utf-8').strip()
                total_duration = float(duration_str)
                
                # Calcular posición en el audio según la posición relativa de la idea
                audio_position = pos_relativa * total_duration
                
                # Ajustar para no exceder los límites del audio
                audio_position = max(0, min(audio_position, total_duration - duracion))
                
            except subprocess.CalledProcessError:
                print(f"Error al determinar la duración del audio. Usando posición genérica.")
                audio_position = i * 60  # 1 minuto por idea (posición genérica)
            
            # Extraer segmento de audio para esta idea
            audio_segment = self.video_animator.extract_audio_segment(
                audio_path,
                audio_position,
                duracion,
                os.path.join(self.videos_dir, f"idea_{i+1:02d}_audio.m4a")
            )
            
            if not audio_segment:
                print(f"Error al extraer segmento de audio para la idea {i+1}. Saltando...")
                continue
            
            # Crear video para esta idea
            output_filename = f"idea_{i+1:02d}_video.mp4"
            idea_video = self.video_animator.create_key_idea_video(
                image_path,
                audio_segment,
                idea_text,
                os.path.join(self.videos_dir, output_filename),
                duracion
            )
            
            # Añadir logos si están disponibles
            if idea_video and self.logos_paths:
                idea_video_with_logos = self.video_animator.add_logos_to_video(
                    idea_video,
                    self.logos_paths,
                    os.path.join(self.videos_dir, f"idea_{i+1:02d}_final.mp4")
                )
                
                idea_videos.append(idea_video_with_logos)
            elif idea_video:
                idea_videos.append(idea_video)
        
        print(f"Se generaron {len(idea_videos)} videos para ideas clave.")
        return idea_videos
    
    def process_sermon(self, num_images=15):
        """
        Procesa el sermón completo, generando imágenes y videos.
        
        Args:
            num_images (int): Número de imágenes a generar para el video completo
            
        Returns:
            tuple: (video_sermón, videos_ideas_clave)
        """
        print(f"Procesando sermón en: {self.sermon_dir}")
        
        # Paso 1: Copiar archivos existentes
        audio_path, transcript_path, ideas_path = self.copy_existing_files()
        
        if not audio_path:
            print("No se encontró archivo de audio para el sermón. Abortando.")
            return None, []
        
        # Paso 2: Generar imágenes para el sermón completo
        if transcript_path:
            print(f"Generando {num_images} imágenes para el sermón completo...")
            sermon_images = self.generate_images_for_sermon(transcript_path, num_images)
        else:
            print("No se encontró transcripción. No se pueden generar imágenes para el sermón completo.")
            sermon_images = []
        
        # Paso 3: Generar imágenes para ideas clave
        if ideas_path:
            print("Generando imágenes para ideas clave...")
            ideas_with_images = self.generate_images_for_key_ideas(ideas_path)
        else:
            print("No se encontró archivo de ideas clave. No se pueden generar videos cortos.")
            ideas_with_images = []
        
        # Paso 4: Crear video completo del sermón
        sermon_video = None
        if sermon_images:
            print("Creando video completo del sermón...")
            sermon_video = self.create_full_sermon_video(audio_path, sermon_images)
        
        # Paso 5: Crear videos cortos para ideas clave
        idea_videos = []
        if ideas_with_images:
            print("Creando videos para ideas clave...")
            idea_videos = self.create_key_idea_videos(ideas_with_images, audio_path)
        
        return sermon_video, idea_videos


def main():
    """Función principal para uso por línea de comandos."""
    parser = argparse.ArgumentParser(description='Crear videos de sermones y clips para redes sociales')
    parser.add_argument('--project-dir', type=str, help='Directorio raíz del proyecto')
    parser.add_argument('--sermon-name', type=str, help='Nombre para la carpeta del sermón')
    parser.add_argument('--logos', type=str, nargs='+', help='Rutas a los logos (separadas por espacios)')
    parser.add_argument('--num-images', type=int, default=15, help='Número de imágenes para el video completo')
    parser.add_argument('--no-cache', action='store_true', help='Desactivar caché de imágenes')
    
    args = parser.parse_args()
    
    # Verificar que existen los logos
    logos_paths = []
    
    # Calcular la raíz del proyecto
    if args.project_dir:
        project_dir = args.project_dir
    else:
        # Intentar determinar automáticamente la raíz del proyecto
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))
        
        # Verificar si estamos en la raíz del proyecto
        if not os.path.exists(os.path.join(project_dir, "output_transcriptions")):
            # Estamos en src/image_gen, subir un nivel más
            project_dir = os.path.dirname(project_dir)
    
    if args.logos:
        for logo_path in args.logos:
            if os.path.exists(logo_path):
                logos_paths.append(logo_path)
            else:
                print(f"Logo no encontrado: {logo_path}")
    else:
        # Buscar logos en la ubicación predeterminada
        logos_dir = os.path.join(project_dir, "assets", "logos")
        if os.path.exists(logos_dir):
            for logo_file in os.listdir(logos_dir):
                if logo_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    logos_paths.append(os.path.join(logos_dir, logo_file))
            
            if logos_paths:
                print(f"Se encontraron {len(logos_paths)} logos en {logos_dir}")
    
    # Crear el generador de videos
    try:
        creator = SermonVideoCreator(
            project_dir=project_dir,
            sermon_name=args.sermon_name,
            logos_paths=logos_paths,
            use_cache=not args.no_cache
        )
        
        # Procesar el sermón
        sermon_video, idea_videos = creator.process_sermon(num_images=args.num_images)
        
        if sermon_video:
            print(f"\nVideo completo del sermón generado: {sermon_video}")
        
        if idea_videos:
            print(f"\nVideos de ideas clave generados:")
            for video in idea_videos:
                print(f"- {video}")
        
        print("\n¡Proceso completado!")
        
    except Exception as e:
        print(f"Error durante el procesamiento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
