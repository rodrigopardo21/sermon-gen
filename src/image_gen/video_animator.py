"""
Módulo para añadir animación y movimiento a imágenes estáticas.

Este módulo proporciona funcionalidades para convertir imágenes estáticas
en clips de video con movimiento suave similar al de un drone, combinando
múltiples clips y sincronizando con audio para crear videos completos.

Características principales:
    - Añadir efecto de movimiento suave tipo "drone" a imágenes estáticas
    - Combinar múltiples clips en un video completo
    - Sincronizar con el audio original del sermón
    - Añadir logos como marca de agua
"""

import os
import sys
import subprocess
from pathlib import Path
import numpy as np
import cv2
import json
import time
import shutil
from PIL import Image, ImageDraw, ImageFont

class VideoAnimator:
    """
    Clase para añadir movimiento a imágenes estáticas y crear videos.
    
    Esta clase proporciona métodos para transformar imágenes estáticas
    en clips de video con movimiento suave, combinarlos y añadir audio.
    
    Atributos:
        fps (int): Frames por segundo para los videos generados
        output_dir (str): Directorio donde se guardarán los videos generados
        temp_dir (str): Directorio para archivos temporales
    """
    
    def __init__(self, sermon_dir=None, temp_dir="temp_frames", fps=30):
        """
        Inicializa el animador de video con las configuraciones necesarias.
        
        Args:
            sermon_dir (str): Directorio del sermón (si se proporciona)
            temp_dir (str): Directorio para archivos temporales durante la generación
            fps (int): Frames por segundo para los videos
        """
        self.fps = fps
        
        # Si se proporciona un directorio de sermón, usarlo para organizar los videos
        if sermon_dir:
            self.output_dir = os.path.join(sermon_dir, "videos")
            self.images_dir = os.path.join(sermon_dir, "imagenes")
        else:
            self.output_dir = "output_videos"
            self.images_dir = "output_images"
            
        self.temp_dir = temp_dir
        
        # Crear directorios necesarios
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        print(f"VideoAnimator inicializado con {fps} FPS")
        print(f"Videos serán guardados en: {self.output_dir}")
    
    def add_motion_to_image(self, image_path, duration, output_video_path=None):
        """
        Añade movimiento suave tipo drone a una imagen estática.
        
        Args:
            image_path (str): Ruta a la imagen a animar
            duration (float): Duración del video en segundos
            output_video_path (str, opcional): Ruta donde guardar el video
            
        Returns:
            str: Ruta al video generado
        """
        # Si no se especifica ruta de salida, la generamos
        if not output_video_path:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_video_path = os.path.join(self.output_dir, f"{base_name}_motion.mp4")
        
        # Cargar la imagen
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"No se pudo cargar la imagen: {image_path}")
            
        # Obtener dimensiones
        h, w = img.shape[:2]
        
        # Crear directorio temporal para frames
        segment_id = os.path.basename(image_path).split('.')[0]
        segment_temp_dir = os.path.join(self.temp_dir, segment_id)
        os.makedirs(segment_temp_dir, exist_ok=True)
        
        # Calcular número total de frames
        total_frames = int(duration * self.fps)
        
        # Definir parámetros para el movimiento de cámara
        # Estos parámetros emulan el movimiento de drone del reel de referencia
        max_zoom = 1.1  # Zoom máximo
        max_shift_x = w * 0.05  # Desplazamiento horizontal máximo
        max_shift_y = h * 0.05  # Desplazamiento vertical máximo
        
        print(f"Generando {total_frames} frames con movimiento suave...")
        
        # Generar cada frame con una transformación ligeramente diferente
        for i in range(total_frames):
            # Calcular factores de transformación basados en funciones sinusoidales para suavidad
            t = i / total_frames  # Tiempo normalizado (0-1)
            
            # Zoom suave
            zoom_factor = 1 + (max_zoom - 1) * 0.5 * (1 + np.sin(t * 2 * np.pi - np.pi/2))
            
            # Desplazamiento suave
            shift_x = max_shift_x * np.sin(t * 1.5 * np.pi)
            shift_y = max_shift_y * np.sin(t * 1.7 * np.pi + np.pi/4)
            
            # Matriz de transformación
            M = np.float32([
                [zoom_factor, 0, shift_x + (1-zoom_factor)*w/2],
                [0, zoom_factor, shift_y + (1-zoom_factor)*h/2]
            ])
            
            # Aplicar transformación
            frame = cv2.warpAffine(img, M, (w, h))
            
            # Guardar frame
            output_frame_path = os.path.join(segment_temp_dir, f"frame_{i:04d}.jpg")
            cv2.imwrite(output_frame_path, frame)
            
            # Mostrar progreso
            if i % (total_frames // 10) == 0:
                print(f"Progreso: {i}/{total_frames} frames ({i/total_frames*100:.1f}%)")
        
        # Combinar frames en video usando FFmpeg
        frame_pattern = os.path.join(segment_temp_dir, "frame_%04d.jpg")
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(self.fps),
            '-i', frame_pattern,
            '-c:v', 'libx264',
            '-profile:v', 'high',
            '-crf', '22',
            '-pix_fmt', 'yuv420p',
            output_video_path
        ]
        
        print(f"Ejecutando FFmpeg para crear video...")
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Limpiar archivos temporales
        print(f"Limpiando frames temporales...")
        for file in os.listdir(segment_temp_dir):
            os.remove(os.path.join(segment_temp_dir, file))
        os.rmdir(segment_temp_dir)
        
        print(f"Video con movimiento generado: {output_video_path}")
        return output_video_path
    
    def add_logos_to_video(self, video_path, logos_paths, output_path=None):
        """
        Añade los logos como marca de agua al video.
        
        Args:
            video_path (str): Ruta al video original
            logos_paths (list): Lista de rutas a los logos
            output_path (str, opcional): Ruta para el video con logos
            
        Returns:
            str: Ruta al video con logos
        """
        if not logos_paths:
            print("No se proporcionaron logos. Usando video original.")
            return video_path
            
        # Verificar que existen los logos
        for logo_path in logos_paths:
            if not os.path.exists(logo_path):
                print(f"Logo no encontrado: {logo_path}")
                return video_path
        
        # Si no se especifica ruta de salida, la generamos
        if not output_path:
            basename = os.path.basename(video_path)
            name, ext = os.path.splitext(basename)
            output_path = os.path.join(os.path.dirname(video_path), f"{name}_with_logos{ext}")
        
        # Calcular posiciones para los logos (esquina inferior derecha, uno al lado del otro)
        filter_complex = ""
        
        # Redimensionar todos los logos para que tengan una altura de 40 píxeles
        scale_filters = []
        overlay_filters = []
        
        for i, logo_path in enumerate(logos_paths):
            # Primero escalamos cada logo
            scale_filters.append(f"[{i+1}:v]scale=-1:40[logo{i}]")
            
            # Luego posicionamos cada logo
            if i == 0:
                # El primer logo se posiciona en la esquina inferior derecha
                overlay_filters.append(f"[0:v][logo{i}]overlay=W-w-10:H-h-10:enable='between(t,0,999999)'[bg{i}]")
            else:
                # Los logos siguientes se posicionan a la izquierda del anterior
                # Usamos una fórmula para calcular la posición X
                # W-w-(10+w_prev+10) donde w_prev es el ancho del logo anterior
                overlay_filters.append(f"[bg{i-1}][logo{i}]overlay=W-w-{30 + 50*i}:H-h-10:enable='between(t,0,999999)'[bg{i}]")
        
        # Construir el filter_complex completo
        filter_complex = ";".join(scale_filters) + ";" + ";".join(overlay_filters)
        
        # Ajustar el nombre de la salida final para el último overlay
        if len(logos_paths) > 0:
            filter_complex = filter_complex.replace(f"[bg{len(logos_paths)-1}]", "[outv]")
        
        # Construir comando FFmpeg
        ffmpeg_cmd = ['ffmpeg', '-y', '-i', video_path]
        
        # Añadir cada logo como input
        for logo_path in logos_paths:
            ffmpeg_cmd.extend(['-i', logo_path])
        
        # Añadir filtro complejo y opciones de salida
        ffmpeg_cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '0:a',
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-crf', '23',
            output_path
        ])
        
        print(f"Ejecutando FFmpeg para añadir logos...")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Video con logos generado: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Error al añadir logos: {e}")
            return video_path
    
    def combine_video_with_audio(self, video_path, audio_path, output_path=None):
        """
        Combina un video (posiblemente sin audio) con una pista de audio.
        
        Args:
            video_path (str): Ruta al archivo de video
            audio_path (str): Ruta al archivo de audio
            output_path (str, opcional): Ruta para el video resultante
            
        Returns:
            str: Ruta al video con audio
        """
        # Si no se especifica ruta de salida, la generamos
        if not output_path:
            basename = os.path.basename(video_path)
            name, ext = os.path.splitext(basename)
            output_path = os.path.join(os.path.dirname(video_path), f"{name}_with_audio{ext}")
        
        # Ejecutar FFmpeg para combinar video y audio
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-map', '0:v',
            '-map', '1:a',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        
        print(f"Ejecutando FFmpeg para combinar video y audio...")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Video con audio generado: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Error al combinar video y audio: {e}")
            return video_path
    
    def extract_audio_segment(self, audio_path, start_time, duration, output_path=None):
        """
        Extrae un segmento de audio de un archivo más grande.
        
        Args:
            audio_path (str): Ruta al archivo de audio completo
            start_time (float): Tiempo de inicio en segundos
            duration (float): Duración del segmento en segundos
            output_path (str, opcional): Ruta para el archivo de audio resultante
            
        Returns:
            str: Ruta al segmento de audio extraído
        """
        # Si no se especifica ruta de salida, la generamos
        if not output_path:
            basename = os.path.basename(audio_path)
            name, ext = os.path.splitext(basename)
            output_path = os.path.join(self.output_dir, f"{name}_segment_{int(start_time)}{ext}")
        
        # Ejecutar FFmpeg para extraer el segmento de audio
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]
        
        print(f"Extrayendo segmento de audio de {start_time}s a {start_time + duration}s...")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Segmento de audio extraído: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Error al extraer segmento de audio: {e}")
            return None
    
    def concatenate_videos(self, video_paths, output_path):
        """
        Concatena múltiples videos en uno solo.
        
        Args:
            video_paths (list): Lista de rutas a los videos a concatenar
            output_path (str): Ruta para el video resultante
            
        Returns:
            str: Ruta al video concatenado
        """
        if len(video_paths) == 0:
            raise ValueError("La lista de videos está vacía")
        elif len(video_paths) == 1:
            print("Solo hay un video, copiando al destino")
            shutil.copy2(video_paths[0], output_path)
            return output_path
        
        # Crear archivo de lista para FFmpeg
        concat_file_path = os.path.join(self.temp_dir, "concat_list.txt")
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for video_path in video_paths:
                # Usar rutas absolutas para evitar problemas
                f.write(f"file '{os.path.abspath(video_path)}'\n")
        
        # Ejecutar FFmpeg para concatenar videos
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            '-c', 'copy',  # Copiar sin recodificar para mayor velocidad
            output_path
        ]
        
        print(f"Ejecutando FFmpeg para concatenar {len(video_paths)} videos...")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Video concatenado guardado en: {output_path}")
            
            # Limpiar archivo temporal
            os.remove(concat_file_path)
            
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Error al concatenar videos: {e}")
            # Limpiar archivo temporal incluso en caso de error
            if os.path.exists(concat_file_path):
                os.remove(concat_file_path)
            return None
    
    def create_key_idea_video(self, image_path, audio_path, idea_text, output_path=None, duration=None):
        """
        Crea un video para una idea clave específica.
        
        Args:
            image_path (str): Ruta a la imagen de fondo
            audio_path (str): Ruta al archivo de audio
            idea_text (str): Texto de la idea clave (para añadir como título)
            output_path (str, opcional): Ruta para el video resultante
            duration (float, opcional): Duración forzada (si no se especifica, se usa la duración del audio)
            
        Returns:
            str: Ruta al video generado
        """
        if not output_path:
            basename = os.path.basename(image_path)
            name, ext = os.path.splitext(basename)
            output_path = os.path.join(self.output_dir, f"{name}_key_idea.mp4")
        
        # Si no se especifica duración, obtenerla del archivo de audio
        if not duration and audio_path and os.path.exists(audio_path):
            ffprobe_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
            ]
            try:
                duration_str = subprocess.check_output(ffprobe_cmd).decode('utf-8').strip()
                duration = float(duration_str)
                print(f"Duración del audio: {duration} segundos")
            except subprocess.CalledProcessError:
                print("No se pudo determinar la duración del audio. Usando 30 segundos por defecto.")
                duration = 30.0
        elif not duration:
            duration = 30.0  # Duración predeterminada
        
        # Primero crear video con movimiento de la imagen
        video_with_motion = self.add_motion_to_image(
            image_path,
            duration,
            os.path.join(self.temp_dir, f"temp_motion_{os.path.basename(output_path)}")
        )
        
        # Combinar con audio si se proporciona
        if audio_path and os.path.exists(audio_path):
            video_with_audio = self.combine_video_with_audio(
                video_with_motion,
                audio_path,
                os.path.join(self.temp_dir, f"temp_audio_{os.path.basename(output_path)}")
            )
        else:
            video_with_audio = video_with_motion
        
        # Limpiar archivos temporales
        if video_with_motion != video_with_audio and os.path.exists(video_with_motion):
            os.remove(video_with_motion)
        
        # Copiar el resultado final
        shutil.copy2(video_with_audio, output_path)
        
        # Limpiar archivos temporales adicionales
        if os.path.exists(video_with_audio) and video_with_audio != output_path:
            os.remove(video_with_audio)
        
        print(f"Video para idea clave generado: {output_path}")
        return output_path
    
    def create_sermon_video(self, image_paths, audio_path, output_path, segment_duration=30.0, logos_paths=None):
        """
        Crea un video completo del sermón, combinando múltiples imágenes con movimiento.
        
        Args:
            image_paths (list): Lista de rutas a las imágenes para el video
            audio_path (str): Ruta al archivo de audio del sermón
            output_path (str): Ruta para el video final
            segment_duration (float): Duración de cada segmento de imagen
            logos_paths (list, opcional): Lista de rutas a los logos a añadir
            
        Returns:
            str: Ruta al video final
        """
        # Verificar que tenemos imágenes para procesar
        if not image_paths:
            print("No se proporcionaron imágenes para el video.")
            return None
        
        # Obtener duración total del audio
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
        
        # Calcular cuántos segmentos necesitamos
        num_segments = int(np.ceil(total_duration / segment_duration))
        
        # Si hay menos imágenes que segmentos, repetimos imágenes
        if len(image_paths) < num_segments:
            # Creamos una lista con suficientes imágenes repitiendo las disponibles
            extended_image_paths = []
            for i in range(num_segments):
                idx = i % len(image_paths)  # Esto crea un ciclo a través de las imágenes disponibles
                extended_image_paths.append(image_paths[idx])
            image_paths = extended_image_paths
        
        # Truncar la lista si hay más imágenes que segmentos
        image_paths = image_paths[:num_segments]
        
        print(f"Creando {num_segments} segmentos de video usando {len(image_paths)} imágenes...")
        
        # Crear cada segmento de video
        segment_videos = []
        
        for i in range(num_segments):
            # Calcular duración de este segmento
            segment_start = i * segment_duration
            
            # El último segmento puede ser más corto
            if i == num_segments - 1:
                segment_duration_actual = total_duration - segment_start
            else:
                segment_duration_actual = segment_duration
            
            print(f"Procesando segmento {i+1}/{num_segments} (duración: {segment_duration_actual:.2f}s)...")
            
            # Extraer segmento de audio
            audio_segment = self.extract_audio_segment(
                audio_path,
                segment_start,
                segment_duration_actual,
                os.path.join(self.temp_dir, f"audio_segment_{i}.m4a")
            )
            
            # Crear video con movimiento para este segmento
            image_path = image_paths[i]
            segment_video = self.add_motion_to_image(
                image_path,
                segment_duration_actual,
                os.path.join(self.temp_dir, f"video_segment_{i}.mp4")
            )
            
            # Combinar con el segmento de audio
            video_with_audio = self.combine_video_with_audio(
                segment_video,
                audio_segment,
                os.path.join(self.temp_dir, f"segment_with_audio_{i}.mp4")
            )
            
            segment_videos.append(video_with_audio)
            
            # Limpiar archivos temporales que ya no necesitamos
            if os.path.exists(segment_video) and segment_video != video_with_audio:
                os.remove(segment_video)
        
        # Concatenar todos los segmentos
        print("Concatenando todos los segmentos...")
        concatenated_video = self.concatenate_videos(
            segment_videos,
            os.path.join(self.temp_dir, "concatenated_sermon.mp4")
        )
        
        # Añadir logos si se proporcionan
        if logos_paths and concatenated_video:
            print("Añadiendo logos al video...")
            final_video = self.add_logos_to_video(
                concatenated_video,
                logos_paths,
                output_path
            )
        else:
            # Si no hay logos, simplemente copiar el video concatenado
            shutil.copy2(concatenated_video, output_path)
            final_video = output_path
        
        # Limpiar archivos temporales
        print("Limpiando archivos temporales...")
        for video in segment_videos:
            if os.path.exists(video):
                os.remove(video)
                
        if os.path.exists(concatenated_video) and concatenated_video != output_path:
            os.remove(concatenated_video)
        
        # Eliminar segmentos de audio
        for i in range(num_segments):
            audio_segment = os.path.join(self.temp_dir, f"audio_segment_{i}.m4a")
            if os.path.exists(audio_segment):
                os.remove(audio_segment)
        
        print(f"Video del sermón completo generado: {final_video}")
        return final_video


# Función para probar el animador independientemente
def test_video_animator():
    """Prueba simple del animador de video."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prueba el módulo VideoAnimator')
    parser.add_argument('--image', type=str, help='Ruta a una imagen para probar el movimiento')
    parser.add_argument('--duration', type=float, default=5.0, help='Duración del video en segundos')
    parser.add_argument('--sermon-dir', type=str, help='Directorio del sermón para pruebas')
    args = parser.parse_args()
    
    # Si se proporciona un directorio de sermón, usarlo
    if args.sermon_dir and os.path.exists(args.sermon_dir):
        animator = VideoAnimator(sermon_dir=args.sermon_dir)
        
        # Buscar automáticamente la primera imagen en el directorio de imágenes
        images_dir = os.path.join(args.sermon_dir, "imagenes")
        if os.path.exists(images_dir):
            images = [f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
            if images:
                image_path = os.path.join(images_dir, images[0])
                args.image = image_path
                print(f"Usando imagen encontrada: {image_path}")
    else:
        animator = VideoAnimator()
    
    if args.image and os.path.exists(args.image):
        # Probar añadir movimiento a una imagen
        try:
            print(f"Generando video de {args.duration} segundos a partir de la imagen...")
            video_path = animator.add_motion_to_image(
                args.image,
                duration=args.duration
            )
            print(f"Prueba exitosa. Video generado en: {video_path}")
            
            # Reproducir video automáticamente en Mac
            try:
                subprocess.run(['open', video_path])
            except Exception:
                print(f"No se pudo reproducir automáticamente. El video está en: {video_path}")
            
        except Exception as e:
            print(f"Error en la prueba: {str(e)}")
    else:
        print("Uso: python video_animator.py --image ruta/a/una/imagen.png [--duration 5.0]")
        print("No se proporcionó una imagen válida para pruebas.")

if __name__ == "__main__":
    # Si se ejecuta este archivo directamente, realizar pruebas
    test_video_animator()

