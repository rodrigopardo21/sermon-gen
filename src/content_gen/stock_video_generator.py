"""
Módulo para la generación de videos utilizando clips de stock.

Este módulo selecciona clips de video de una biblioteca local de stock,
añade textos superpuestos, logos institucionales y audio del sermón
para generar videos para diferentes plataformas.
"""

import os
import json
import random
import datetime
from pathlib import Path
import subprocess
from PIL import Image
import numpy as np
import cv2

class StockVideoGenerator:
    """
    Clase para generar videos utilizando clips de stock.
    """
    
    def __init__(self, base_dir=".", ffmpeg_bin="ffmpeg"):
        """
        Inicializa el generador de videos con stock.
        
        Args:
            base_dir (str): Directorio base del proyecto
            ffmpeg_bin (str): Ruta al ejecutable de FFmpeg
        """
        self.base_dir = Path(base_dir)
        self.ffmpeg_bin = ffmpeg_bin
        self.stock_dir = self.base_dir / "stock_videos"
        self.assets_dir = self.base_dir / "assets"
        self.sermones_dir = self.base_dir / "sermones"
        
        # Verificar que los logos existen
        self.npim_logo = self.assets_dir / "logos" / "npim_logo.png"
        self.profecias_logo = self.assets_dir / "logos" / "profecias_hoy_logo.png"
        
        if not self.npim_logo.exists() or not self.profecias_logo.exists():
            print("ADVERTENCIA: No se encontraron los logos institucionales.")
            print(f"Busqué en: {self.npim_logo} y {self.profecias_logo}")
    
    def crear_directorio_sermon(self, titulo_sermon, fecha=None):
        """
        Crea una estructura de directorios para un nuevo sermón.
        
        Args:
            titulo_sermon (str): Título del sermón (se normalizará para el nombre de directorio)
            fecha (str, opcional): Fecha en formato YYYY-MM-DD. Si es None, se usa la fecha actual.
            
        Returns:
            Path: Ruta al directorio creado para el sermón
        """
        # Normalizar el título para usarlo como nombre de directorio
        titulo_normalizado = self._normalizar_nombre(titulo_sermon)
        
        # Usar fecha actual si no se proporciona
        if fecha is None:
            fecha = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Crear nombre de directorio
        dir_name = f"{fecha}_{titulo_normalizado}"
        sermon_dir = self.sermones_dir / dir_name
        
        # Crear estructura de directorios
        (sermon_dir / "transcripcion").mkdir(parents=True, exist_ok=True)
        (sermon_dir / "ideas_clave").mkdir(exist_ok=True)
        (sermon_dir / "videos_cortos").mkdir(exist_ok=True)
        (sermon_dir / "video_largo").mkdir(exist_ok=True)
        
        print(f"Creado directorio para el sermón: {sermon_dir}")
        return sermon_dir
    
    def _normalizar_nombre(self, nombre):
        """
        Normaliza un nombre para usarlo como nombre de archivo/directorio.
        
        Args:
            nombre (str): Nombre a normalizar
            
        Returns:
            str: Nombre normalizado
        """
        # Convertir a minúsculas
        nombre = nombre.lower()
        
        # Reemplazar espacios por guiones bajos
        nombre = nombre.replace(" ", "_")
        
        # Eliminar caracteres especiales
        import re
        nombre = re.sub(r'[^a-z0-9_]', '', nombre)
        
        return nombre
    
    def seleccionar_clip_stock(self, categoria, duracion_min=5, duracion_max=15):
        """
        Selecciona un clip de video de stock aleatorio de la categoría especificada.
        
        Args:
            categoria (str): Categoría del video (naturaleza, simbolos, personas, fondos)
            duracion_min (int): Duración mínima del clip en segundos
            duracion_max (int): Duración máxima del clip en segundos
            
        Returns:
            str: Ruta al clip seleccionado o None si no se encuentra ninguno
        """
        categoria_dir = self.stock_dir / categoria
        
        if not categoria_dir.exists():
            print(f"ADVERTENCIA: No se encontró el directorio de categoría: {categoria_dir}")
            return None
        
        # Listar todos los archivos de video en el directorio
        clip_files = list(categoria_dir.glob("*.mp4")) + list(categoria_dir.glob("*.mov")) + list(categoria_dir.glob("*.avi"))
        
        if not clip_files:
            print(f"ADVERTENCIA: No se encontraron clips en la categoría: {categoria}")
            return None
        
        # Por ahora, simplemente seleccionamos un clip aleatorio
        # En una implementación más avanzada, podríamos filtrar por duración y otros criterios
        return str(random.choice(clip_files))
    
    def generar_video_idea(self, idea, audio_path, output_path, duracion=30):
        """
        Genera un video para una idea específica, usando un clip de stock.
        
        Args:
            idea (dict): Idea clave extraída (contiene texto, acto, etc.)
            audio_path (str): Ruta al archivo de audio para este clip
            output_path (str): Ruta donde guardar el video generado
            duracion (int): Duración deseada del video en segundos
            
        Returns:
            bool: True si se generó el video correctamente, False en caso contrario
        """
        try:
            # Seleccionar categoría según el acto
            acto = idea.get('acto', 1)
            if acto == 1:  # Planteamiento del problema
                categorias = ['naturaleza', 'simbolos']
            elif acto == 2:  # Desafío y propuesta
                categorias = ['personas', 'simbolos']
            else:  # Resolución y compromiso
                categorias = ['naturaleza', 'simbolos', 'personas']
            
            # Seleccionar un clip aleatorio de una categoría adecuada
            categoria = random.choice(categorias)
            clip_path = self.seleccionar_clip_stock(categoria)
            
            if not clip_path:
                print(f"No se pudo seleccionar un clip para la idea: {idea['texto'][:30]}...")
                return False
            
            # Preparar el texto para mostrar
            texto = idea['texto']
            
            # Texto de referencia bíblica (si existe y no es "No especificada")
            referencia = idea.get('referencia_biblica', '')
            if referencia and referencia != "No especificada":
                texto_completo = f'"{texto}"\n\n{referencia}'
            else:
                texto_completo = f'"{texto}"'
            
            # Creamos un archivo temporal con el texto
            texto_path = "temp_texto.txt"
            with open(texto_path, "w", encoding="utf-8") as f:
                f.write(texto_completo)
            
            # Comando FFmpeg para generar el video
            # Incluye:
            # 1. Clip de stock como fondo
            # 2. Texto superpuesto en un recuadro beige semitransparente
            # 3. Logos institucionales en la esquina superior derecha
            # 4. Audio del sermón
            cmd = [
                self.ffmpeg_bin,
                "-y",  # Sobrescribir si existe
                "-i", clip_path,  # Clip de stock
                "-i", audio_path,  # Audio
                "-i", str(self.npim_logo),  # Logo NPIM
                "-i", str(self.profecias_logo),  # Logo Profecías Hoy
                "-filter_complex",
                # Recortar el clip a la duración deseada y aplicar efecto Ken Burns
                f"[0:v]trim=duration={duracion},setpts=PTS-STARTPTS,scale=1080:1920,zoompan=z='min(zoom+0.0005,1.3)':d={duracion*25}:s=1080x1920[bg]; " +
                # Crear el recuadro beige para el texto
                f"color=c=beige@0.75:s=800x400,subtitles={texto_path}:force_style='FontSize=24,Alignment=10,BorderStyle=4,Outline=1,Shadow=0,MarginL=10,MarginR=10,MarginV=10'[txt]; " +
                # Redimensionar los logos
                "[2:v]scale=100:-1[logo1]; " +
                "[3:v]scale=100:-1[logo2]; " +
                # Combinar todo
                "[bg][txt]overlay=(W-w)/2:(H-h)/2[v1]; " +
                "[v1][logo1]overlay=W-w-10:10[v2]; " +
                "[v2][logo2]overlay=W-w-120:10[outv]",
                "-map", "[outv]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                "-t", str(duracion),
                output_path
            ]
            
            # Ejecutar el comando
            subprocess.run(cmd, check=True)
            
            # Eliminar el archivo temporal
            if os.path.exists(texto_path):
                os.remove(texto_path)
            
            print(f"Video generado correctamente: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando video para la idea: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def generar_videos_ideas(self, ideas_json_path, audio_path, output_dir):
        """
        Genera videos para todas las ideas clave extraídas.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con las ideas clave
            audio_path (str): Ruta al archivo de audio del sermón
            output_dir (str): Directorio donde guardar los videos generados
            
        Returns:
            list: Lista de rutas a los videos generados
        """
        try:
            # Cargar las ideas del archivo JSON
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Verificar que el directorio de salida existe
            os.makedirs(output_dir, exist_ok=True)
            
            # Lista para almacenar las rutas de los videos generados
            videos_generados = []
            
            # Generar un video para cada idea
            for i, idea in enumerate(ideas):
                # Nombrar el archivo de salida
                output_filename = f"idea_{i+1}_acto_{idea.get('acto', 0)}.mp4"
                output_path = os.path.join(output_dir, output_filename)
                
                # Definir la duración basada en el texto (aproximadamente 1 segundo por palabra)
                num_palabras = len(idea['texto'].split())
                duracion = max(10, min(60, num_palabras))  # Entre 10 y 60 segundos
                
                # Generar el video
                exito = self.generar_video_idea(idea, audio_path, output_path, duracion)
                
                if exito:
                    videos_generados.append(output_path)
            
            print(f"Se generaron {len(videos_generados)} videos de ideas clave.")
            return videos_generados
            
        except Exception as e:
            print(f"Error generando videos de ideas: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def generar_video_sermon_completo(self, video_path, transcripcion_path, output_path):
        """
        Genera un video completo del sermón con subtítulos y logos.
        
        Args:
            video_path (str): Ruta al video original del sermón
            transcripcion_path (str): Ruta al archivo de transcripción
            output_path (str): Ruta donde guardar el video generado
            
        Returns:
            bool: True si se generó el video correctamente, False en caso contrario
        """
        try:
            # Comprobar que los archivos existen
            if not os.path.exists(video_path):
                print(f"No se encontró el video original: {video_path}")
                return False
            
            if not os.path.exists(transcripcion_path):
                print(f"No se encontró el archivo de transcripción: {transcripcion_path}")
                return False
            
            # Crear un archivo de subtítulos a partir de la transcripción
            subtitle_path = os.path.splitext(transcripcion_path)[0] + ".srt"
            self._crear_subtitulos(transcripcion_path, subtitle_path)
            
            # Comando FFmpeg para generar el video
            cmd = [
                self.ffmpeg_bin,
                "-y",  # Sobrescribir si existe
                "-i", video_path,  # Video original
                "-i", str(self.npim_logo),  # Logo NPIM
                "-i", str(self.profecias_logo),  # Logo Profecías Hoy
                "-filter_complex",
                # Redimensionar los logos
                "[1:v]scale=120:-1[logo1]; " +
                "[2:v]scale=120:-1[logo2]; " +
                # Combinar todo
                "[0:v][logo1]overlay=W-w-10:10[v1]; " +
                "[v1][logo2]overlay=W-w-140:10[outv]",
                "-map", "[outv]",
                "-map", "0:a",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-vf", f"subtitles={subtitle_path}",
                output_path
            ]
            
            # Ejecutar el comando
            subprocess.run(cmd, check=True)
            
            print(f"Video completo generado correctamente: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando video completo: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _crear_subtitulos(self, transcripcion_path, output_path):
        """
        Crea un archivo de subtítulos SRT a partir de una transcripción.
        
        Esta es una implementación muy básica que divide el texto en segmentos
        de tamaño similar y les asigna tiempos estimados. En un sistema real,
        se utilizaría información de tiempo de la transcripción.
        
        Args:
            transcripcion_path (str): Ruta al archivo de transcripción
            output_path (str): Ruta donde guardar el archivo SRT
            
        Returns:
            bool: True si se creó el archivo correctamente, False en caso contrario
        """
        try:
            # Leer la transcripción
            with open(transcripcion_path, 'r', encoding='utf-8') as f:
                texto = f.read()
            
            # Dividir en oraciones (aproximadamente)
            import re
            oraciones = re.split(r'(?<=[.!?])\s+', texto)
            
            # Crear el archivo SRT
            with open(output_path, 'w', encoding='utf-8') as f:
                tiempo_inicio = 0
                
                for i, oracion in enumerate(oraciones, 1):
                    if not oracion.strip():
                        continue
                    
                    # Calcular duración basada en el número de palabras (aproximadamente)
                    num_palabras = len(oracion.split())
                    duracion = max(2, min(10, num_palabras * 0.4))  # Entre 2 y 10 segundos
                    
                    tiempo_fin = tiempo_inicio + duracion
                    
                    # Formatear los tiempos para SRT (HH:MM:SS,mmm)
                    inicio_str = self._formatear_tiempo_srt(tiempo_inicio)
                    fin_str = self._formatear_tiempo_srt(tiempo_fin)
                    
                    # Escribir la entrada SRT
                    f.write(f"{i}\n")
                    f.write(f"{inicio_str} --> {fin_str}\n")
                    f.write(f"{oracion}\n\n")
                    
                    tiempo_inicio = tiempo_fin
            
            print(f"Archivo de subtítulos creado: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creando subtítulos: {str(e)}")
            return False
    
    def _formatear_tiempo_srt(self, tiempo_segundos):
        """
        Formatea un tiempo en segundos al formato SRT (HH:MM:SS,mmm).
        
        Args:
            tiempo_segundos (float): Tiempo en segundos
            
        Returns:
            str: Tiempo formateado para SRT
        """
        horas = int(tiempo_segundos // 3600)
        minutos = int((tiempo_segundos % 3600) // 60)
        segundos = int(tiempo_segundos % 60)
        milisegundos = int((tiempo_segundos * 1000) % 1000)
        
        return f"{horas:02d}:{minutos:02d}:{segundos:02d},{milisegundos:03d}"


# Función principal para uso desde línea de comandos
def main():
    """Función principal para uso en línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar videos a partir de ideas clave y clips de stock')
    subparsers = parser.add_subparsers(dest='comando', help='Comando a ejecutar')
    
    # Comando para crear estructura de sermón
    crear_sermon = subparsers.add_parser('crear_sermon', help='Crear estructura de directorios para un nuevo sermón')
    crear_sermon.add_argument('--titulo', type=str, required=True, help='Título del sermón')
    crear_sermon.add_argument('--fecha', type=str, help='Fecha del sermón (YYYY-MM-DD)')
    
    # Comando para generar videos de ideas clave
    generar_videos = subparsers.add_parser('generar_videos', help='Generar videos para las ideas clave')
    generar_videos.add_argument('--ideas', type=str, required=True, help='Ruta al archivo JSON con ideas clave')
    generar_videos.add_argument('--audio', type=str, required=True, help='Ruta al archivo de audio')
    generar_videos.add_argument('--output', type=str, required=True, help='Directorio de salida para los videos')
    
    # Comando para generar video completo del sermón
    generar_completo = subparsers.add_parser('generar_completo', help='Generar video completo del sermón con subtítulos')
    generar_completo.add_argument('--video', type=str, required=True, help='Ruta al video original')
    generar_completo.add_argument('--transcripcion', type=str, required=True, help='Ruta al archivo de transcripción')
    generar_completo.add_argument('--output', type=str, required=True, help='Ruta de salida para el video')
    
    args = parser.parse_args()
    
    # Inicializar el generador
    generator = StockVideoGenerator()
    
    if args.comando == 'crear_sermon':
        generator.crear_directorio_sermon(args.titulo, args.fecha)
    elif args.comando == 'generar_videos':
        generator.generar_videos_ideas(args.ideas, args.audio, args.output)
    elif args.comando == 'generar_completo':
        generator.generar_video_sermon_completo(args.video, args.transcripcion, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
