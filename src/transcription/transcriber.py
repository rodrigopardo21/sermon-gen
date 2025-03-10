"""
Módulo de transcripción de audio/video.

Este módulo proporciona funcionalidades para la transcripción de audio y video.
Para hacerlo, se utiliza el modelo Whisper de OpenAI.

Caracteristicas principales:
    - Procesamiento de archivos de video .mp4
    - Extracción de audio
    - Transcripción de audio a texto
    - Manejo de tiempos y segmentos
"""

import os
import ffmpeg
from openai import OpenAI
from datetime import datetime
import pandas as pd
import json

class SermonTranscriber:

    """
    Clase para manejar la transcripción de sermones.

    Esta clase proporciona una interfaz simplificada para:
    1. Procesar archivos de video
    2. Extraer el audio
    3. Realizar la transcripción
    4. Organizar los resultados

    Atributos:
        input_dir (str): Directorio donde se encuentran los videos a procesar
        output_dir (str): Directorio donde se guardarán las transcripciones
        api_key (str): Clave de API de OpenAI para acceder a Whisper
    """

    def __init__(self, input_dir, output_dir, api_key):
        """
        Inicializa el transcriptor con las configuraciones necesarias.

        Args:
            input_dir (str): Ruta al directorio de videos de entrada
            output_dir (str): Ruta al directorio donde se guardarán las transcripciones
            api_key (str): Clave de API de OpenAI
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.client = OpenAI(api_key=api_key)

        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)

    def extract_audio(self, video_path):
        """
        Extrae el audio de un archivo de video.
        
        Este método utiliza FFmpeg para procesar el archivo de video y extraer
        su contenido de audio. El audio extraído se guarda temporalmente
        como un archivo WAV, que es un formato óptimo para la transcripción.
        
        Args:
            video_path (str): Ruta completa al archivo de video
            
        Returns:
            str: Ruta al archivo de audio extraído
            
        Raises:
            FFmpegError: Si hay un problema durante la extracción del audio
        """
        # Construimos el nombre del archivo de audio basado en el video original
        video_filename = os.path.basename(video_path)
        audio_filename = os.path.splitext(video_filename)[0] + "_audio.wav"
        audio_path = os.path.join(self.output_dir, audio_filename)
        
        try:
            # Configuramos el proceso de FFmpeg para extraer audio
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, audio_path,
                                 acodec='pcm_s16le',  # Codec de audio sin pérdida
                                 ac=1,                 # Mono (1 canal)
                                 ar='16k')            # Frecuencia de muestreo de 16kHz
            
            # Ejecutamos el proceso de FFmpeg
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            return audio_path
            
        except ffmpeg.Error as e:
            error_message = f"Error al extraer audio de {video_path}: {str(e)}"
            raise Exception(error_message)

    def split_audio(self, audio_path, segment_duration=300):
        """
        Divide un archivo de audio en segmentos más pequeños.

        Args:
            audio_path (str): Ruta al archivo de audio completo
            segment_duration (int): Duración de cada segmento en segundos (default: 5 minutos)

        Returns:
            list: Lista de rutas a los segmentos de audio generados
        """
        try:
            # Obtenemos la duración del audio usando ffprobe
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            print(f"Duración total del audio: {duration} segundos")

            # Calculamos cuántos segmentos necesitamos
            num_segments = int(duration / segment_duration) + 1
            print(f"Dividiendo en {num_segments} segmentos de {segment_duration} segundos")

            # Creamos cada segmento
            segments = []
            for i in range(num_segments):
                start_time = i * segment_duration
                # Si es el último segmento, ajustamos la duración
                if i == num_segments - 1:
                    # No especificamos duración para el último segmento
                    output_segment = os.path.join(
                        self.output_dir,
                        f"{os.path.splitext(os.path.basename(audio_path))[0]}_segment_{i+1}.mp3"
                    )
                    # Usamos el formato mp3 para reducir tamaño
                    ffmpeg.input(audio_path, ss=start_time).output(
                        output_segment,
                        acodec='libmp3lame',
                        ac=1,
                        ar='16k',
                        ab='32k'
                    ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                else:
                    output_segment = os.path.join(
                        self.output_dir,
                        f"{os.path.splitext(os.path.basename(audio_path))[0]}_segment_{i+1}.mp3"
                    )
                    ffmpeg.input(audio_path, ss=start_time, t=segment_duration).output(
                        output_segment,
                        acodec='libmp3lame',
                        ac=1,
                        ar='16k',
                        ab='32k'
                    ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

                segments.append(output_segment)
                print(f"Creado segmento {i+1}/{num_segments}: {output_segment}")

            return segments

        except Exception as e:
            error_message = f"Error al dividir el audio {audio_path}: {str(e)}"
            print(error_message)
            raise Exception(error_message)

    def transcribe_audio(self, audio_path):
        """
        Transcribe un archivo de audio usando el modelo Whisper de OpenAI.
        
        Este método maneja el proceso de transcripción, enviando el audio
        a la API de OpenAI y procesando la respuesta. La transcripción
        incluye el texto y marcas de tiempo, lo que nos permitirá
        segmentar el contenido posteriormente.
        
        Args:
            audio_path (str): Ruta al archivo de audio a transcribir
            
        Returns:
            dict: Diccionario con la transcripción y metadatos asociados
        """
        try:
            # Abrimos el archivo de audio en modo binario
            with open(audio_path, 'rb') as audio_file:
                # Realizamos la transcripción usando la API de OpenAI
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",    # Modelo más reciente de Whisper
                    file=audio_file,      # Nuestro archivo de audio
                    language="es",        # Especificamos español
                    response_format="verbose_json"  # Incluye metadatos detallados
                )
            
            # Debug - imprimimos información sobre la respuesta
            print(f"Tipo de segments: {type(response.segments)}")
            if hasattr(response, 'segments') and len(response.segments) > 0:
                print(f"Cantidad de segmentos: {len(response.segments)}")
                
            # Procesamos la respuesta para extraer información útil
            # Convertimos los objetos TranscriptionSegment a diccionarios
            segments_list = []
            if hasattr(response, 'segments'):
                for seg in response.segments:
                    segment_dict = {
                        'start': float(seg.start),
                        'end': float(seg.end),
                        'text': seg.text
                    }
                    segments_list.append(segment_dict)
            
            transcription_data = {
                'text': response.text,  # Texto completo de la transcripción
                'segments': segments_list,  # Lista de diccionarios con segmentos
                'timestamp': datetime.now().isoformat(),  # Cuándo se realizó
                'audio_file': audio_path  # Referencia al archivo original
            }
            
            # Agregamos texto a la transcripción
            all_text = response.text.strip()
            print(f"Transcripción: \"{all_text[:100]}...\"")
            
            return transcription_data
            
        except Exception as e:
            error_message = f"Error durante la transcripción de {audio_path}: {str(e)}"
            raise Exception(error_message)

    def process_video(self, video_filename):
        """
        Procesa un video completo, desde la extracción de audio hasta la transcripción.
        
        Este método coordina el proceso completo de transcripción para un video,
        manejando cada paso del proceso y guardando los resultados.
        
        Args:
            video_filename (str): Nombre del archivo de video a procesar
            
        Returns:
            dict: Diccionario con la transcripción y toda la información asociada
        """
        try:
            # Construimos la ruta completa al archivo de video
            video_path = os.path.join(self.input_dir, video_filename)
            
            # Verificamos que el archivo existe
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"No se encontró el archivo: {video_path}")
            
            # Paso 1: Extraer el audio del video
            print(f"Extrayendo audio de {video_filename}...")
            audio_path = self.extract_audio(video_path)
            
            # Paso 2: Dividir el audio en segmentos manejables
            print(f"Dividiendo el audio en segmentos...")
            audio_segments = self.split_audio(audio_path)
            
            # Paso 3: Transcribir cada segmento
            print(f"Transcribiendo {len(audio_segments)} segmentos...")
            
            all_transcription_data = {
                'text': '',
                'segments': [],
                'audio_file': audio_path,
                'timestamp': datetime.now().isoformat()
            }
            
            # Procesamos cada segmento
            for i, segment_path in enumerate(audio_segments):
                print(f"Transcribiendo segmento {i+1}/{len(audio_segments)}...")
                try:
                    segment_data = self.transcribe_audio(segment_path)
                    
                    # Ajustamos las marcas de tiempo para los segmentos
                    segment_offset = i * 300  # 300 segundos = 5 minutos
                    for segment in segment_data['segments']:
                        # Ajustamos las marcas de tiempo
                        segment['start'] += segment_offset
                        segment['end'] += segment_offset
                        
                    # Añadimos el texto a la transcripción completa
                    all_transcription_data['text'] += ' ' + segment_data['text']
                    # Añadimos los segmentos a la lista completa
                    all_transcription_data['segments'].extend(segment_data['segments'])
                    
                except Exception as e:
                    print(f"Error transcribiendo segmento {i+1}: {str(e)}")
                    # Continuamos con el siguiente segmento incluso si este falla
            
            # Paso 4: Guardar los resultados
            output_filename = os.path.splitext(video_filename)[0] + "_transcription.json"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Añadimos información adicional útil
            all_transcription_data.update({
                'video_filename': video_filename,
                'processing_date': datetime.now().isoformat(),
                'video_path': video_path,
                'total_segments': len(audio_segments)
            })
            
            # Guardamos la transcripción en formato JSON
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_transcription_data, f, ensure_ascii=False, indent=4)
                print(f"Transcripción completada y guardada en: {output_path}")
                
                # Exportamos también como texto plano para revisión humana
                self.export_plain_text(all_transcription_data)
            except Exception as e:
                print(f"Error al guardar el archivo JSON: {str(e)}")
            
            return all_transcription_data
            
        except Exception as e:
            error_message = f"Error procesando el video {video_filename}: {str(e)}"
            print(error_message)
            raise Exception(error_message)

    def prepare_social_media_content(self, transcription_data):
        """
        Prepara el contenido transcrito para diferentes plataformas de redes sociales.
        
        Este método analiza la transcripción completa y la divide en segmentos
        apropiados para diferentes plataformas, considerando las limitaciones
        y requisitos específicos de cada una. Es como un editor experto que
        sabe exactamente cómo adaptar el contenido para cada audiencia y formato.
        
        Por ejemplo:
        - YouTube: Segmentos de 15-20 minutos
        - Instagram/Facebook Reels: 30-60 segundos
        - TikTok: 15-60 segundos
        
        Args:
            transcription_data (dict): Datos de la transcripción con segmentos
            
        Returns:
            dict: Contenido formateado para cada plataforma
        """
        # Creamos un diccionario para almacenar el contenido por plataforma
        social_media_content = {
            'youtube': [],
            'reels': [],
            'tiktok': []
        }
        
        # Verificamos que hay segmentos para procesar
        if 'segments' not in transcription_data or not transcription_data['segments']:
            print("No hay segmentos disponibles para procesar.")
            return social_media_content
        
        # Procesamos los segmentos de la transcripción
        segments = transcription_data['segments']
        current_youtube_segment = []
        current_duration = 0
        
        for segment in segments:
            # Cada segmento viene con un tiempo de inicio y fin
            segment_duration = segment['end'] - segment['start']
            
            # Preparamos contenido para YouTube (segmentos de 20 minutos)
            if current_duration + segment_duration <= 1200:  # 20 minutos en segundos
                current_youtube_segment.append(segment)
                current_duration += segment_duration
            else:
                # Guardamos el segmento actual y comenzamos uno nuevo
                if current_youtube_segment:
                    social_media_content['youtube'].append({
                        'segments': current_youtube_segment.copy(),
                        'duration': current_duration,
                        'text': ' '.join(seg['text'] for seg in current_youtube_segment)
                    })
                current_youtube_segment = [segment]
                current_duration = segment_duration
            
            # Identificamos segmentos cortos potenciales para Reels/TikTok
            # Buscamos frases completas entre 15 y 60 segundos
            if 15 <= segment_duration <= 60:
                # Si el segmento parece ser una frase completa
                if segment['text'].strip().endswith(('.', '!', '?')):
                    short_content = {
                        'segment': segment,
                        'duration': segment_duration,
                        'text': segment['text']
                    }
                    # Añadimos a Reels si es más largo, a TikTok si es más corto
                    if segment_duration >= 30:
                        social_media_content['reels'].append(short_content)
                    social_media_content['tiktok'].append(short_content)
        
        # No olvidemos el último segmento de YouTube si existe
        if current_youtube_segment:
            social_media_content['youtube'].append({
                'segments': current_youtube_segment,
                'duration': current_duration,
                'text': ' '.join(seg['text'] for seg in current_youtube_segment)
            })
        
        # Añadimos metadatos útiles
        social_media_content['metadata'] = {
            'original_video': transcription_data.get('video_filename', 'unknown'),
            'processing_date': datetime.now().isoformat(),
            'total_segments': {
                'youtube': len(social_media_content['youtube']),
                'reels': len(social_media_content['reels']),
                'tiktok': len(social_media_content['tiktok'])
            }
        }
        
        return social_media_content

    def export_plain_text(self, transcription_data, output_filename=None):
        """
        Exporta la transcripción a un archivo de texto plano para revisión humana.
        
        Args:
            transcription_data (dict): Datos de la transcripción
            output_filename (str, optional): Nombre del archivo de salida. Si es None,
                                            se deriva del nombre del video.
                                            
        Returns:
            str: Ruta al archivo de texto creado
        """
        if not output_filename:
            # Si no se proporciona un nombre, derivamos uno del nombre del archivo de audio
            base_name = os.path.basename(transcription_data['audio_file'])
            output_filename = os.path.splitext(base_name)[0].replace('_audio', '') + '_transcript.txt'
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Contenido para el archivo de texto
        content = []
        
        # Añadimos un encabezado
        content.append(f"TRANSCRIPCIÓN: {transcription_data.get('video_filename', 'Sermón')}")
        content.append(f"Fecha de procesamiento: {transcription_data.get('processing_date', 'Desconocida')}")
        content.append("")  # Línea en blanco
        content.append("=" * 80)  # Separador
        content.append("")  # Línea en blanco
        
        # Añadimos el texto principal
        content.append(transcription_data.get('text', '').strip())
        
        # Guardamos el contenido en el archivo
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        print(f"Transcripción en texto plano guardada en: {output_path}")
        return output_path
