"""
Módulo para la generación de videos basados en ideas clave extraídas.

Este módulo utiliza DALL-E para generar imágenes basadas en las ideas clave
y MoviePy para crear videos con efectos de movimiento suave y textos superpuestos.
"""

import os
import json
import time
import random
import requests
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from PIL import Image
from moviepy.editor import (
    TextClip, ImageClip, AudioFileClip, CompositeVideoClip, 
    concatenate_videoclips, ColorClip, vfx
)

# Cargamos las variables de entorno para acceder a las APIs
load_dotenv()

class VideoGenerator:
    """
    Clase para generar videos a partir de ideas clave y audio extraído.
    """
    
    def __init__(self, output_dir="output_videos"):
        """
        Inicializa el generador de videos.
        
        Args:
            output_dir (str): Directorio donde se guardarán los videos generados
        """
        self.output_dir = output_dir
        self.temp_dir = os.path.join(output_dir, "temp")
        
        # Crear directorios si no existen
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Inicializar cliente de OpenAI
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Configuraciones para los videos
        self.video_width = 1080  # Ancho para formato vertical (9:16)
        self.video_height = 1920  # Alto para formato vertical (9:16)
        self.fps = 30  # Cuadros por segundo

    def generate_image_prompt(self, idea, acto):
        """
        Genera un prompt optimizado para DALL-E basado en la idea clave.
        
        Args:
            idea (dict): Idea clave extraída
            acto (int): Número del acto (1, 2 o 3)
            
        Returns:
            str: Prompt optimizado para DALL-E
        """
        # Extraemos el texto y la referencia bíblica
        texto = idea["texto"]
        referencia = idea["referencia_biblica"]
        if referencia == "No especificada":
            referencia = ""
        
        # Base del prompt según el acto
        if acto == 1:  # Planteamiento del problema
            base_prompt = "Fotografía cinematográfica dramática de {}, iluminación tenue, atmósfera introspectiva."
            temas = ["acantilado erosionado", "mar tormentoso", "camino pedregoso", "desierto solitario", 
                    "ramas secas", "cielo nublado sobre una iglesia", "persona mirando al horizonte"]
        elif acto == 2:  # Desafío y propuesta
            base_prompt = "Fotografía inspiradora de {}, luz del amanecer, tonos cálidos, sensación de esperanza."
            temas = ["montaña majestuosa", "camino ascendente", "manos extendidas", "amanecer sobre el mar", 
                    "faro en la distancia", "bosque con rayos de luz", "puente sobre un abismo"]
        else:  # Resolución y compromiso
            base_prompt = "Fotografía sublime de {}, luz radiante, composición armoniosa, sensación de paz y plenitud."
            temas = ["cumbre de montaña", "mar en calma", "valle fértil", "familia reunida", "cruz en la cima", 
                    "sendero iluminado", "cielo estrellado sobre paisaje sereno"]
        
        # Seleccionar un tema aleatorio que corresponda al acto
        tema = random.choice(temas)
        
        # Crear el prompt completo
        prompt = base_prompt.format(tema)
        prompt += f" La imagen debe evocar la idea: '{texto}'"
        
        if referencia:
            prompt += f" Relacionado con {referencia}."
            
        # Añadir instrucciones para optimizar la composición
        prompt += " Estilo fotorrealista, formato vertical 9:16, calidad cinematográfica, adecuado para uso religioso cristiano."
        
        return prompt

    def generate_image_with_dalle(self, prompt, filename):
        """
        Genera una imagen usando DALL-E basada en el prompt.
        
        Args:
            prompt (str): Prompt descriptivo para DALL-E
            filename (str): Nombre del archivo donde guardar la imagen
            
        Returns:
            str: Ruta a la imagen generada
        """
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # Formato vertical optimizado para redes sociales
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Descargar la imagen
            image_path = os.path.join(self.temp_dir, filename)
            image_data = requests.get(image_url).content
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
                
            print(f"Imagen generada y guardada en: {image_path}")
            return image_path
            
        except Exception as e:
            print(f"Error generando imagen con DALL-E: {str(e)}")
            # Si falla, usamos una imagen de respaldo
            return None

    def extract_audio_segment(self, audio_path, start_time, duration, output_path):
        """
        Extrae un segmento de audio del sermón.
        
        Args:
            audio_path (str): Ruta al archivo de audio completo
            start_time (float): Tiempo de inicio del segmento (en segundos)
            duration (float): Duración del segmento (en segundos)
            output_path (str): Ruta donde guardar el segmento
            
        Returns:
            str: Ruta al segmento de audio extraído
        """
        try:
            audio = AudioFileClip(audio_path)
            segment = audio.subclip(start_time, start_time + duration)
            segment.write_audiofile(output_path, codec='aac')
            return output_path
        except Exception as e:
            print(f"Error extrayendo segmento de audio: {str(e)}")
            return None

    def create_text_overlay(self, text, width, height, font_size=60):
        """
        Crea un clip de texto con fondo beige semitransparente.
        
        Args:
            text (str): Texto a mostrar
            width (int): Ancho del video
            height (int): Alto del video
            font_size (int): Tamaño de la fuente
            
        Returns:
            CompositeVideoClip: Clip compuesto con el texto y su fondo
        """
        # Crear el clip de texto
        txt_clip = TextClip(
            text, 
            font='Arial-Bold', 
            fontsize=font_size, 
            color='black',
            align='center',
            method='caption',
            size=(width * 0.8, None)  # Limitar el ancho del texto
        )
        
        # Crear el fondo beige con un poco más de tamaño que el texto
        padding = 40
        bg_width = txt_clip.w + padding * 2
        bg_height = txt_clip.h + padding * 2
        bg_clip = ColorClip(
            size=(bg_width, bg_height),
            color=(240, 223, 185)  # Color beige
        )
        
        # Añadir bordes redondeados (simulados con opacidad)
        bg_clip = bg_clip.set_opacity(0.85)
        
        # Combinar el fondo y el texto
        text_composite = CompositeVideoClip([
            bg_clip,
            txt_clip.set_position(('center', 'center'))
        ])
        
        # Posicionar en la parte central inferior del video
        return text_composite.set_position(('center', 0.8), relative=True)

    def apply_ken_burns_effect(self, image_path, duration, zoom_direction):
        """
        Aplica efecto Ken Burns (zoom suave) a una imagen.
        
        Args:
            image_path (str): Ruta a la imagen
            duration (float): Duración del clip
            zoom_direction (str): 'in' para acercar, 'out' para alejar
            
        Returns:
            ImageClip: Clip con el efecto aplicado
        """
        img_clip = ImageClip(image_path)
        
        # Ajustar la imagen al tamaño del video manteniendo la proporción
        img_clip = img_clip.resize(height=self.video_height)
        
        # Si la imagen es más ancha que el video, recortarla
        if img_clip.w > self.video_width:
            img_clip = img_clip.crop(x1=(img_clip.w - self.video_width) / 2, 
                                    y1=0, 
                                    width=self.video_width, 
                                    height=self.video_height)
        
        # Aplicar efecto de zoom
        if zoom_direction == 'in':
            img_clip = img_clip.resize(lambda t: 1 + 0.05 * t)
        else:
            img_clip = img_clip.resize(lambda t: 1 + 0.05 * (1 - t))
            
        # Centrar la imagen y establecer la duración
        img_clip = img_clip.set_position('center').set_duration(duration)
        
        return img_clip

    def create_idea_clip(self, idea, audio_path, acto, index, estimated_duration=10):
        """
        Crea un clip para una idea específica con imagen, texto y audio.
        
        Args:
            idea (dict): Idea clave extraída
            audio_path (str): Ruta al archivo de audio del sermón
            acto (int): Número del acto (1, 2 o 3)
            index (int): Índice de la idea dentro del acto
            estimated_duration (float): Duración estimada del clip
            
        Returns:
            CompositeVideoClip: Clip compuesto con todos los elementos
        """
        # Generar nombre de archivo único para esta idea
        base_filename = f"acto{acto}_idea{index}"
        image_filename = f"{base_filename}.png"
        audio_filename = f"{base_filename}.aac"
        
        # Generar prompt y crear imagen con DALL-E
        prompt = self.generate_image_prompt(idea, acto)
        image_path = self.generate_image_with_dalle(prompt, image_filename)
        
        # Si no se pudo generar la imagen, usar una de respaldo
        if not image_path:
            # Aquí podrías tener imágenes de respaldo por tema o usar una genérica
            image_path = "path_to_backup_image.jpg"  # Ajustar esto según tu configuración
        
        # Extraer segmento de audio (aquí necesitarías determinar el tiempo de inicio)
        # Por simplicidad, usamos posiciones estimadas en el audio completo
        # En una implementación real, necesitarías un método para identificar estos segmentos
        audio_segment_path = os.path.join(self.temp_dir, audio_filename)
        # Posición relativa convertida a tiempo (ejemplo simple)
        start_time = idea.get("posicion_relativa", 0) * 60  # Asumiendo que el audio dura aproximadamente 60 segundos por cada "posición relativa"
        self.extract_audio_segment(audio_path, start_time, estimated_duration, audio_segment_path)
        
        # Cargar el segmento de audio
        audio_clip = AudioFileClip(audio_segment_path)
        
        # Actualizar la duración estimada basada en el audio real
        clip_duration = audio_clip.duration
        
        # Aplicar efecto Ken Burns
        zoom_direction = 'in' if random.random() > 0.5 else 'out'
        img_clip = self.apply_ken_burns_effect(image_path, clip_duration, zoom_direction)
        
        # Crear overlay de texto
        text_clip = self.create_text_overlay(idea["texto"], self.video_width, self.video_height)
        text_clip = text_clip.set_duration(clip_duration)
        
        # Añadir efecto de fade in/out al texto
        text_clip = text_clip.fadein(1).fadeout(1)
        
        # Combinar imagen y texto
        composite_clip = CompositeVideoClip([img_clip, text_clip])
        
        # Añadir audio
        final_clip = composite_clip.set_audio(audio_clip)
        
        # Añadir transiciones
        final_clip = final_clip.fadein(1).fadeout(1)
        
        return final_clip

    def create_complete_video(self, ideas_json_path, audio_path, output_filename):
        """
        Crea un video completo con todas las ideas clave.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con las ideas clave
            audio_path (str): Ruta al archivo de audio del sermón
            output_filename (str): Nombre del archivo de salida
            
        Returns:
            str: Ruta al video generado
        """
        try:
            # Cargar ideas del JSON
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Organizar ideas por acto
            ideas_por_acto = {1: [], 2: [], 3: []}
            for idea in ideas:
                acto = idea.get('acto', 1)
                ideas_por_acto[acto].append(idea)
            
            # Lista para almacenar todos los clips
            all_clips = []
            
            # Generar clips para cada acto
            for acto in [1, 2, 3]:
                acto_ideas = ideas_por_acto[acto]
                for i, idea in enumerate(acto_ideas):
                    clip = self.create_idea_clip(idea, audio_path, acto, i)
                    all_clips.append(clip)
            
            # Concatenar todos los clips
            final_video = concatenate_videoclips(all_clips, method="compose")
            
            # Ruta de salida para el video final
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Guardar el video
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                bitrate='5000k'
            )
            
            print(f"Video completo generado y guardado en: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error creando video completo: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def create_short_form_video(self, ideas_json_path, audio_path, output_dir=None):
        """
        Crea videos cortos (reels/shorts) para cada acto.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con las ideas clave
            audio_path (str): Ruta al archivo de audio del sermón
            output_dir (str, optional): Directorio de salida personalizado
            
        Returns:
            list: Lista de rutas a los videos generados
        """
        if output_dir is None:
            output_dir = self.output_dir
        
        try:
            # Cargar ideas del JSON
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Organizar ideas por acto
            ideas_por_acto = {1: [], 2: [], 3: []}
            for idea in ideas:
                acto = idea.get('acto', 1)
                ideas_por_acto[acto].append(idea)
            
            # Lista para almacenar rutas de videos generados
            generated_videos = []
            
            # Generar un video por cada acto
            for acto in [1, 2, 3]:
                acto_ideas = ideas_por_acto[acto]
                
                # Lista para almacenar clips de este acto
                acto_clips = []
                
                # Nombre descriptivo del acto
                if acto == 1:
                    acto_nombre = "planteamiento"
                elif acto == 2:
                    acto_nombre = "desafio"
                else:
                    acto_nombre = "resolucion"
                
                # Generar clips para cada idea del acto
                for i, idea in enumerate(acto_ideas):
                    clip = self.create_idea_clip(idea, audio_path, acto, i)
                    acto_clips.append(clip)
                
                # Si hay clips para este acto
                if acto_clips:
                    # Concatenar clips del acto
                    acto_video = concatenate_videoclips(acto_clips, method="compose")
                    
                    # Generar nombre de archivo para este acto
                    sermon_name = Path(ideas_json_path).stem.split('_')[0]  # Extraer nombre del sermón
                    output_filename = f"{sermon_name}_{acto_nombre}_short.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Guardar video de este acto
                    acto_video.write_videofile(
                        output_path,
                        fps=self.fps,
                        codec='libx264',
                        audio_codec='aac',
                        bitrate='5000k'
                    )
                    
                    generated_videos.append(output_path)
                    print(f"Video del acto {acto} ({acto_nombre}) generado: {output_path}")
            
            return generated_videos
            
        except Exception as e:
            print(f"Error creando videos cortos: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

# Función principal para uso directo desde línea de comandos
def main():
    """Función principal para uso en línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar videos a partir de ideas clave extraídas')
    parser.add_argument('--ideas', type=str, required=True, help='Ruta al archivo JSON con ideas clave')
    parser.add_argument('--audio', type=str, required=True, help='Ruta al archivo de audio del sermón')
    parser.add_argument('--output', type=str, default='video_sermon.mp4', help='Nombre del archivo de salida')
    parser.add_argument('--shorts', action='store_true', help='Generar videos cortos para redes sociales')
    
    args = parser.parse_args()
    
    generator = VideoGenerator()
    
    if args.shorts:
        print("Generando videos cortos para redes sociales...")
        generator.create_short_form_video(args.ideas, args.audio)
    else:
        print("Generando video completo...")
        generator.create_complete_video(args.ideas, args.audio, args.output)

if __name__ == "__main__":
    main()
