"""
Módulo para la generación de videos con imágenes estáticas y texto superpuesto.

Este módulo utiliza DALL-E para generar imágenes estáticas apropiadas para cada
frase clave, y ffmpeg para combinarlas con texto y audio en videos finales.
"""

import os
import json
import time
import subprocess
import textwrap
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Cargamos las variables de entorno
load_dotenv()

class StaticImageGenerator:
    """
    Clase para generar videos basados en imágenes estáticas con texto superpuesto.
    """
    
    def __init__(self, base_dir=".", ffmpeg_bin="ffmpeg"):
        """
        Inicializa el generador de videos con imágenes estáticas.
        
        Args:
            base_dir (str): Directorio base del proyecto
            ffmpeg_bin (str): Ruta al ejecutable de FFmpeg
        """
        self.base_dir = Path(base_dir)
        self.ffmpeg_bin = ffmpeg_bin
        self.output_dir = self.base_dir / "output_videos"
        self.temp_dir = self.output_dir / "temp"
        self.assets_dir = self.base_dir / "assets"
        
        # Verificar que los logos existen
        self.npim_logo = self.assets_dir / "logos" / "npim_logo.png"
        self.profecias_logo = self.assets_dir / "logos" / "profecias_hoy_logo.png"
        
        if not self.npim_logo.exists() or not self.profecias_logo.exists():
            print("ADVERTENCIA: No se encontraron los logos institucionales.")
            print(f"Busqué en: {self.npim_logo} y {self.profecias_logo}")
        
        # Crear directorios si no existen
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Inicializar cliente de OpenAI para DALL-E
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generar_prompt_dalle(self, idea, acto):
        """
        Genera un prompt para DALL-E que describa una imagen apropiada para la idea.
        
        Args:
            idea (dict): Idea clave extraída (contiene texto, referencia, etc.)
            acto (int): Número del acto (1, 2 o 3)
            
        Returns:
            str: Prompt optimizado para DALL-E
        """
        # Extraer información relevante
        texto = idea["texto"]
        referencia = idea.get("referencia_biblica", "")
        if referencia == "No especificada":
            referencia = ""
        
        # Base del prompt según el acto
        if acto == 1:  # Planteamiento del problema
            estilo = "en estilo fotográfico dramático, iluminación tenue, atmósfera contemplativa"
            tema = "Escena cristiana evangélica mostrando reflexión o desafío espiritual"
        elif acto == 2:  # Desafío y propuesta
            estilo = "en estilo fotográfico inspirador, luz brillante, tonos cálidos"
            tema = "Escena cristiana evangélica mostrando transformación o llamado espiritual"
        else:  # Resolución y compromiso
            estilo = "en estilo fotográfico esperanzador, luz radiante, composición armoniosa"
            tema = "Escena cristiana evangélica mostrando paz, alegría o compromiso de fe"
        
        # Construir el prompt
        prompt = f"Crea una imagen {estilo}. {tema} que represente el concepto: '{texto}'"
        
        if referencia:
            prompt += f" relacionado con el versículo bíblico {referencia}."
        
        # Añadir restricciones para asegurar contenido apropiado
        prompt += " La imagen debe ser apropiada para una audiencia cristiana protestante/evangélica, "
        prompt += "evitando símbolos específicamente católicos, de testigos de Jehová u otras denominaciones. "
        prompt += "Usar simbolismo cristiano universal como la cruz, la Biblia abierta, o escenas de oración. "
        prompt += "Formato vertical 9:16 ideal para redes sociales, alta calidad fotográfica."
        
        return prompt
    
    def generar_imagen_dalle(self, prompt, output_path):
        """
        Genera una imagen con DALL-E 3 basada en el prompt.
        
        Args:
            prompt (str): Prompt descriptivo para DALL-E
            output_path (str): Ruta donde guardar la imagen generada
            
        Returns:
            bool: True si se generó la imagen correctamente, False en caso contrario
        """
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # Formato vertical para redes sociales
                quality="standard",
                n=1,
            )
            
            # Obtener la URL de la imagen generada
            image_url = response.data[0].url
            
            # Descargar la imagen
            import requests
            image_data = requests.get(image_url).content
            
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            print(f"Imagen generada y guardada en: {output_path}")
            return True
        
        except Exception as e:
            print(f"Error generando imagen con DALL-E: {str(e)}")
            return False
    
    def crear_video_idea(self, idea, audio_path, imagen_path, output_path, duracion=None):
        """
        Crea un video para una idea específica con imagen estática y texto superpuesto.
        
        Args:
            idea (dict): Idea clave
            audio_path (str): Ruta al archivo de audio
            imagen_path (str): Ruta a la imagen generada
            output_path (str): Ruta donde guardar el video
            duracion (float, optional): Duración en segundos. Si es None, se usa la duración del audio.
            
        Returns:
            bool: True si se generó el video correctamente, False en caso contrario
        """
        try:
            # Crear un archivo temporal con el texto
            texto = idea["texto"]
            referencia = idea.get("referencia_biblica", "")
            
            if referencia and referencia != "No especificada":
                texto_completo = f'"{texto}"\n\n{referencia}'
            else:
                texto_completo = f'"{texto}"'
            
            # Dividir el texto en líneas para mejor presentación
            texto_formateado = textwrap.fill(texto_completo, width=40)
            texto_path = os.path.join(self.temp_dir, "texto_temp.txt")
            
            with open(texto_path, "w", encoding="utf-8") as f:
                f.write(texto_formateado)
            
            # Generar el video con ffmpeg
            cmd = [
                self.ffmpeg_bin,
                "-y",  # Sobrescribir si existe
                "-loop", "1",  # Mantener la imagen estática
                "-i", imagen_path,  # Imagen
                "-i", audio_path,  # Audio
                "-i", str(self.npim_logo),  # Logo NPIM
                "-i", str(self.profecias_logo),  # Logo Profecías Hoy
                "-filter_complex",
                # Escalar los logos
                "[2:v]scale=100:-1[logo1]; " +
                "[3:v]scale=100:-1[logo2]; " +
                # Añadir logos a la imagen
                "[0:v][logo1]overlay=main_w-overlay_w-10:10[v1]; " +
                "[v1][logo2]overlay=main_w-overlay_w-120:10[v2]; " +
                # Añadir el texto con fondo beige
                f"[v2]drawtext=fontfile=/Library/Fonts/Arial.ttf:textfile={texto_path}:fontsize=48:fontcolor=black:box=1:boxcolor=beige@0.8:boxborderw=15:x=(w-text_w)/2:y=(h*0.75)[outv]",
                "-map", "[outv]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",  # Terminar cuando termine el audio
                output_path
            ]
            
            # Ejecutar el comando
            subprocess.run(cmd, check=True)
            
            print(f"Video de idea generado: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creando video para idea: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def generar_videos_ideas(self, ideas_json_path, audio_path, output_dir=None):
        """
        Genera videos para todas las ideas clave.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con ideas clave
            audio_path (str): Ruta al archivo de audio completo
            output_dir (str, optional): Directorio de salida personalizado
            
        Returns:
            list: Lista de rutas a los videos generados
        """
        if output_dir is None:
            output_dir = self.output_dir / "shorts"
            output_dir.mkdir(exist_ok=True)
        
        try:
            # Cargar ideas del JSON
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Lista para almacenar rutas de videos generados
            videos_generados = []
            
            # Para cada idea, generar una imagen y un video
            for i, idea in enumerate(ideas):
                print(f"\nProcesando idea {i+1}/{len(ideas)}...")
                
                # Obtener acto
                acto = idea.get('acto', 1)
                
                # Generar prompt para DALL-E
                prompt = self.generar_prompt_dalle(idea, acto)
                print(f"Prompt para DALL-E: {prompt[:100]}...")
                
                # Generar imagen
                imagen_path = os.path.join(self.temp_dir, f"imagen_idea_{i+1}.png")
                exito_imagen = self.generar_imagen_dalle(prompt, imagen_path)
                
                if not exito_imagen:
                    print(f"No se pudo generar imagen para idea {i+1}. Continuando con la siguiente.")
                    continue
                
                # Extraer segmento de audio (aproximadamente)
                # Esto es una simplificación. Idealmente, se debería usar la información de tiempo real.
                total_duration = 600  # Asumimos 10 minutos por defecto
                posicion_relativa = idea.get('posicion_relativa', i / len(ideas))
                
                # Estimar posición en el audio total
                start_pos = posicion_relativa * total_duration
                
                # Duración aproximada basada en el texto
                num_palabras = len(idea['texto'].split())
                duracion = max(10, min(60, num_palabras * 0.5))  # Entre 10 y 60 segundos
                
                # Extraer segmento de audio
                audio_segment_path = os.path.join(self.temp_dir, f"audio_idea_{i+1}.mp3")
                
                ffmpeg_extract = [
                    self.ffmpeg_bin,
                    "-y",
                    "-i", audio_path,
                    "-ss", str(start_pos),
                    "-t", str(duracion),
                    "-c:a", "aac",
                    audio_segment_path
                ]
                
                try:
                    subprocess.run(ffmpeg_extract, check=True)
                except Exception as e:
                    print(f"Error extrayendo segmento de audio: {str(e)}")
                    # Usar un archivo de audio alternativo silencioso
                    audio_segment_path = self.crear_audio_silencioso(duracion)
                
                # Generar video con la imagen y el segmento de audio
                output_filename = f"idea_{i+1}_acto_{acto}.mp4"
                output_path = os.path.join(output_dir, output_filename)
                
                exito_video = self.crear_video_idea(
                    idea,
                    audio_segment_path,
                    imagen_path,
                    output_path,
                    duracion
                )
                
                if exito_video:
                    videos_generados.append(output_path)
            
            print(f"\nGenerados {len(videos_generados)} videos de ideas clave.")
            return videos_generados
            
        except Exception as e:
            print(f"Error generando videos de ideas: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def crear_audio_silencioso(self, duracion):
        """
        Crea un archivo de audio silencioso para casos donde no se puede extraer audio.
        
        Args:
            duracion (float): Duración en segundos
            
        Returns:
            str: Ruta al archivo de audio generado
        """
        output_path = os.path.join(self.temp_dir, "silent_audio.mp3")
        
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duracion),
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return output_path
        except Exception as e:
            print(f"Error creando audio silencioso: {str(e)}")
            return None
    
    def generar_video_completo_subtitulos(self, video_path, transcription_path, output_path):
        """
        Genera un video completo con subtítulos sincronizados.
        
        Args:
            video_path (str): Ruta al video original
            transcription_path (str): Ruta al archivo de transcripción
            output_path (str): Ruta donde guardar el video generado
            
        Returns:
            bool: True si se generó el video correctamente, False en caso contrario
        """
        try:
            # Convertir la transcripción a formato SRT (subtítulos)
            srt_path = os.path.join(self.temp_dir, "subtitulos.srt")
            exito_srt = self.crear_archivo_srt(transcription_path, srt_path)
            
            if not exito_srt:
                print("No se pudo crear el archivo de subtítulos.")
                return False
            
            # Generar video con subtítulos y logos
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i", video_path,
                "-i", str(self.npim_logo),
                "-i", str(self.profecias_logo),
                "-filter_complex",
                # Escalar los logos
                "[1:v]scale=100:-1[logo1]; " +
                "[2:v]scale=100:-1[logo2]; " +
                # Añadir logos
                "[0:v][logo1]overlay=main_w-overlay_w-10:10[v1]; " +
                "[v1][logo2]overlay=main_w-overlay_w-120:10[outv]",
                "-vf", f"subtitles={srt_path}:force_style='FontSize=18,Alignment=2,Outline=1,Shadow=1'",
                "-map", "[outv]",
                "-map", "0:a",
                "-c:v", "libx264",
                "-c:a", "aac",
                output_path
            ]
            
            # Ejecutar el comando
            subprocess.run(cmd, check=True)
            
            print(f"Video completo con subtítulos generado: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generando video completo: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def crear_archivo_srt(self, transcription_path, output_path):
        """
        Convierte un archivo de transcripción a formato SRT para subtítulos.
        
        Args:
            transcription_path (str): Ruta al archivo de transcripción
            output_path (str): Ruta donde guardar el archivo SRT
            
        Returns:
            bool: True si se creó el archivo correctamente, False en caso contrario
        """
        try:
            # Leer la transcripción
            with open(transcription_path, 'r', encoding='utf-8') as f:
                transcripcion = f.read()
            
            # Dividir en oraciones
            import re
            oraciones = re.split(r'(?<=[.!?])\s+', transcripcion)
            
            # Crear archivo SRT
            with open(output_path, 'w', encoding='utf-8') as f:
                subtitulo_num = 1
                tiempo_inicio = 0
                
                for oracion in oraciones:
                    if not oracion.strip():
                        continue
                    
                    # Estimar duración basada en el número de palabras
                    palabras = oracion.split()
                    num_palabras = len(palabras)
                    
                    # Aproximadamente 0.4 segundos por palabra
                    duracion = max(2, min(7, num_palabras * 0.4))
                    
                    # Formatear tiempos para SRT (HH:MM:SS,mmm)
                    tiempo_fin = tiempo_inicio + duracion
                    inicio_str = self.formatear_tiempo_srt(tiempo_inicio)
                    fin_str = self.formatear_tiempo_srt(tiempo_fin)
                    
                    # Escribir entrada SRT
                    f.write(f"{subtitulo_num}\n")
                    f.write(f"{inicio_str} --> {fin_str}\n")
                    f.write(f"{oracion}\n\n")
                    
                    # Actualizar para el siguiente subtítulo
                    subtitulo_num += 1
                    tiempo_inicio = tiempo_fin
            
            print(f"Archivo SRT creado: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creando archivo SRT: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def formatear_tiempo_srt(self, segundos):
        """
        Formatea un tiempo en segundos al formato SRT (HH:MM:SS,mmm).
        
        Args:
            segundos (float): Tiempo en segundos
            
        Returns:
            str: Tiempo formateado para SRT
        """
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segundos_enteros = int(segundos % 60)
        milisegundos = int((segundos * 1000) % 1000)
        
        return f"{horas:02d}:{minutos:02d}:{segundos_enteros:02d},{milisegundos:03d}"


# Función principal para uso en línea de comandos
def main():
    """Función principal para uso en línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generador de videos con imágenes estáticas')
    subparsers = parser.add_subparsers(dest='comando', help='Comando a ejecutar')
    
    # Comando para generar videos de ideas clave
    generar_videos = subparsers.add_parser('generar_videos', help='Generar videos para las ideas clave')
    generar_videos.add_argument('--ideas', type=str, required=True, help='Ruta al archivo JSON con ideas clave')
    generar_videos.add_argument('--audio', type=str, required=True, help='Ruta al archivo de audio')
    generar_videos.add_argument('--output', type=str, help='Directorio de salida para los videos')
    
    # Comando para generar video completo con subtítulos
    generar_completo = subparsers.add_parser('generar_completo', help='Generar video completo con subtítulos')
    generar_completo.add_argument('--video', type=str, required=True, help='Ruta al video original')
    generar_completo.add_argument('--transcripcion', type=str, required=True, help='Ruta al archivo de transcripción')
    generar_completo.add_argument('--output', type=str, required=True, help='Ruta de salida para el video')
    
    args = parser.parse_args()
    
    generator = StaticImageGenerator()
    
    if args.comando == 'generar_videos':
        generator.generar_videos_ideas(args.ideas, args.audio, args.output)
    elif args.comando == 'generar_completo':
        generator.generar_video_completo_subtitulos(args.video, args.transcripcion, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
