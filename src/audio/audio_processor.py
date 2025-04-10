"""
Módulo para procesar archivos de audio.

Este módulo se encarga de extraer segmentos de audio basados en marcas de tiempo,
combinar segmentos y preparar archivos de audio para la generación de videos.
"""

import os
import json
import tempfile
import subprocess
from pathlib import Path

class AudioProcessor:
    """
    Procesador de archivos de audio para la generación de videos.
    
    Esta clase se encarga de:
    1. Extraer segmentos de audio basados en ideas clave
    2. Combinar segmentos para crear archivos de audio para videos cortos
    3. Optimizar archivos de audio para diferentes plataformas
    """
    
    def __init__(self, ffmpeg_path="ffmpeg"):
        """
        Inicializa el procesador de audio.
        
        Args:
            ffmpeg_path (str): Ruta al ejecutable de FFmpeg (por defecto usa el de PATH)
        """
        self.ffmpeg_path = ffmpeg_path
    
    def extract_audio_for_key_ideas(self, ideas_json_path, audio_file_path, output_path=None, padding_seconds=1.0):
        """
        Extrae segmentos de audio correspondientes a las ideas clave y los combina.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con las ideas clave
            audio_file_path (str): Ruta al archivo de audio completo
            output_path (str, optional): Ruta donde guardar el archivo de audio combinado
            padding_seconds (float): Segundos adicionales antes y después de cada segmento
            
        Returns:
            str: Ruta al archivo de audio generado o None si hay error
        """
        try:
            # Verificar que los archivos existen
            if not os.path.exists(ideas_json_path):
                print(f"Error: No se encontró el archivo de ideas: {ideas_json_path}")
                return None
                
            if not os.path.exists(audio_file_path):
                print(f"Error: No se encontró el archivo de audio: {audio_file_path}")
                return None
            
            # Cargar las ideas clave
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Verificar que hay ideas para procesar
            if not ideas or len(ideas) == 0:
                print("No se encontraron ideas clave en el archivo.")
                return None
            
            # Verificar que las ideas tienen marcas de tiempo
            has_timestamps = all('timestamp_start' in idea and 'timestamp_end' in idea for idea in ideas)
            
            if not has_timestamps:
                print("Las ideas clave no contienen marcas de tiempo. Se necesita enriquecer el JSON.")
                # Aquí podríamos llamar a una función que busque las marcas de tiempo
                # Por ahora, retornamos None
                return None
            
            # Crear directorio temporal para segmentos
            temp_dir = tempfile.mkdtemp()
            segment_files = []
            
            # Extraer cada segmento
            for i, idea in enumerate(ideas):
                start_time = max(0, idea['timestamp_start'] - padding_seconds)
                duration = (idea['timestamp_end'] - idea['timestamp_start']) + (padding_seconds * 2)
                
                # Ruta para el segmento temporal
                segment_path = os.path.join(temp_dir, f"segment_{i+1}.wav")
                
                # Extraer segmento usando FFmpeg
                cmd = [
                    self.ffmpeg_path,
                    "-i", audio_file_path,
                    "-ss", str(start_time),
                    "-t", str(duration),
                    "-c:a", "pcm_s16le",  # Codec de audio sin pérdida
                    "-y",  # Sobrescribir si existe
                    segment_path
                ]
                
                # Ejecutar comando
                try:
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    segment_files.append(segment_path)
                    print(f"Segmento {i+1} extraído: {start_time:.2f}s - {start_time + duration:.2f}s")
                except subprocess.CalledProcessError as e:
                    print(f"Error al extraer segmento {i+1}: {str(e)}")
                    continue
            
            # Si no hay segmentos, salir
            if not segment_files:
                print("No se pudo extraer ningún segmento de audio.")
                return None
            
            # Crear archivo de lista para concatenación
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")
            
            # Determinar ruta de salida si no se proporciona
            if not output_path:
                audio_dir = os.path.dirname(audio_file_path)
                audio_base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
                output_path = os.path.join(audio_dir, f"{audio_base_name}_ideas_clave.wav")
            
            # Combinar segmentos en un solo archivo
            concat_cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:a", "pcm_s16le",  # Codec de audio sin pérdida
                "-y",  # Sobrescribir si existe
                output_path
            ]
            
            try:
                subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                print(f"Audio para ideas clave generado: {output_path}")
                return output_path
            except subprocess.CalledProcessError as e:
                print(f"Error al combinar segmentos: {str(e)}")
                return None
                
        except Exception as e:
            print(f"Error en el procesamiento de audio: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def add_timestamps_to_ideas(self, ideas_json_path, transcription_json_path, output_path=None):
        """
        Añade marcas de tiempo a las ideas clave buscando coincidencias en la transcripción.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con las ideas clave
            transcription_json_path (str): Ruta al archivo JSON de transcripción con marcas de tiempo
            output_path (str, optional): Ruta donde guardar el JSON enriquecido
            
        Returns:
            str: Ruta al archivo JSON enriquecido o None si hay error
        """
        try:
            # Verificar que los archivos existen
            if not os.path.exists(ideas_json_path):
                print(f"Error: No se encontró el archivo de ideas: {ideas_json_path}")
                return None
                
            if not os.path.exists(transcription_json_path):
                print(f"Error: No se encontró el archivo de transcripción: {transcription_json_path}")
                return None
            
            # Cargar las ideas clave
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Cargar la transcripción
            with open(transcription_json_path, 'r', encoding='utf-8') as f:
                transcription = json.load(f)
            
            # Verificar que hay segmentos en la transcripción
            if not transcription or 'segments' not in transcription or not transcription['segments']:
                print("No se encontraron segmentos en la transcripción.")
                return None
            
            # Para cada idea, buscar coincidencias en los segmentos
            for idea in ideas:
                texto_idea = idea.get('texto', '').strip()
                if not texto_idea:
                    continue
                
                # Buscar coincidencias en los segmentos
                mejor_coincidencia = None
                mejor_puntuacion = 0
                
                for segment in transcription['segments']:
                    texto_segmento = segment.get('text', '').strip()
                    if not texto_segmento:
                        continue
                    
                    # Verificar si el texto de la idea está contenido en el segmento
                    if texto_idea in texto_segmento:
                        # Coincidencia exacta
                        mejor_coincidencia = segment
                        break
                    
                    # Calcular una puntuación de similitud simple
                    palabras_idea = set(texto_idea.lower().split())
                    palabras_segmento = set(texto_segmento.lower().split())
                    comunes = len(palabras_idea.intersection(palabras_segmento))
                    puntuacion = comunes / max(1, len(palabras_idea))
                    
                    if puntuacion > mejor_puntuacion:
                        mejor_puntuacion = puntuacion
                        mejor_coincidencia = segment
                
                # Si encontramos coincidencia, añadir marcas de tiempo
                if mejor_coincidencia and mejor_puntuacion > 0.7:
                    idea['timestamp_start'] = float(mejor_coincidencia.get('start', 0))
                    idea['timestamp_end'] = float(mejor_coincidencia.get('end', 0))
                    idea['segment_text'] = mejor_coincidencia.get('text', '')
                    idea['match_confidence'] = mejor_puntuacion
                else:
                    # Si no encontramos coincidencia, establecemos tiempos por defecto
                    # basados en la posición relativa de la idea
                    duration = float(transcription.get('duration', 0)) or 2000  # Default 2000 segundos
                    pos = idea.get('posicion_relativa', 0)
                    idea['timestamp_start'] = pos * duration
                    idea['timestamp_end'] = min(duration, (pos * duration) + 10)  # 10 segundos por defecto
                    idea['segment_text'] = "No encontrado"
                    idea['match_confidence'] = 0
            
            # Determinar ruta de salida si no se proporciona
            if not output_path:
                ideas_dir = os.path.dirname(ideas_json_path)
                ideas_base_name = os.path.splitext(os.path.basename(ideas_json_path))[0]
                output_path = os.path.join(ideas_dir, f"{ideas_base_name}_with_timestamps.json")
            
            # Guardar JSON enriquecido
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(ideas, f, ensure_ascii=False, indent=2)
            
            print(f"Ideas clave enriquecidas con marcas de tiempo: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error al añadir marcas de tiempo: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_subtitle_file(self, ideas_json_path, output_path=None, format_type="srt"):
        """
        Genera un archivo de subtítulos a partir de las ideas clave.
        
        Args:
            ideas_json_path (str): Ruta al archivo JSON con las ideas clave
            output_path (str, optional): Ruta donde guardar el archivo de subtítulos
            format_type (str): Formato del archivo de subtítulos (srt, vtt, txt)
            
        Returns:
            str: Ruta al archivo de subtítulos generado o None si hay error
        """
        try:
            # Verificar que el archivo existe
            if not os.path.exists(ideas_json_path):
                print(f"Error: No se encontró el archivo de ideas: {ideas_json_path}")
                return None
            
            # Cargar las ideas clave
            with open(ideas_json_path, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
            
            # Verificar que hay ideas para procesar
            if not ideas or len(ideas) == 0:
                print("No se encontraron ideas clave en el archivo.")
                return None
            
            # Verificar que las ideas tienen marcas de tiempo
            has_timestamps = all('timestamp_start' in idea and 'timestamp_end' in idea for idea in ideas)
            
            if not has_timestamps:
                print("Las ideas clave no contienen marcas de tiempo. No se puede generar subtítulos.")
                return None
            
            # Determinar ruta de salida si no se proporciona
            if not output_path:
                ideas_dir = os.path.dirname(ideas_json_path)
                ideas_base_name = os.path.splitext(os.path.basename(ideas_json_path))[0]
                output_path = os.path.join(ideas_dir, f"{ideas_base_name}_subtitles.{format_type}")
            
            # Ordenar ideas por tiempo de inicio
            ideas_sorted = sorted(ideas, key=lambda x: x.get('timestamp_start', 0))
            
            # Generar contenido de subtítulos según el formato
            if format_type == "srt":
                subtitle_content = self._generate_srt(ideas_sorted)
            elif format_type == "vtt":
                subtitle_content = self._generate_vtt(ideas_sorted)
            else:  # txt u otro formato
                subtitle_content = self._generate_txt(ideas_sorted)
            
            # Guardar archivo
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            print(f"Archivo de subtítulos generado: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error al generar archivo de subtítulos: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_srt(self, ideas):
        """Genera subtítulos en formato SRT."""
        srt_content = ""
        
        for i, idea in enumerate(ideas, 1):
            start_time = idea.get('timestamp_start', 0)
            end_time = idea.get('timestamp_end', 0)
            
            # Convertir a formato SRT (HH:MM:SS,mmm)
            start_str = self._format_time_srt(start_time)
            end_str = self._format_time_srt(end_time)
            
            # Añadir entrada de subtítulo
            srt_content += f"{i}\n"
            srt_content += f"{start_str} --> {end_str}\n"
            srt_content += f"{idea.get('texto', '')}\n\n"
        
        return srt_content
    
    def _generate_vtt(self, ideas):
        """Genera subtítulos en formato VTT."""
        vtt_content = "WEBVTT\n\n"
        
        for i, idea in enumerate(ideas, 1):
            start_time = idea.get('timestamp_start', 0)
            end_time = idea.get('timestamp_end', 0)
            
            # Convertir a formato VTT (HH:MM:SS.mmm)
            start_str = self._format_time_vtt(start_time)
            end_str = self._format_time_vtt(end_time)
            
            # Añadir entrada de subtítulo
            vtt_content += f"{i}\n"
            vtt_content += f"{start_str} --> {end_str}\n"
            vtt_content += f"{idea.get('texto', '')}\n\n"
        
        return vtt_content
    
    def _generate_txt(self, ideas):
        """Genera subtítulos en formato de texto simple."""
        txt_content = ""
        
        for idea in ideas:
            txt_content += f"{idea.get('texto', '')}\n\n"
        
        return txt_content
    
    def _format_time_srt(self, seconds):
        """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _format_time_vtt(self, seconds):
        """Convierte segundos a formato VTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"

    def get_audio_duration(self, audio_path):
        """
        Obtiene la duración de un archivo de audio en segundos.
        
        Args:
            audio_path (str): Ruta al archivo de audio
            
        Returns:
            float: Duración en segundos o None si hay error
        """
        try:
            if not os.path.exists(audio_path):
                print(f"Error: No existe el archivo de audio: {audio_path}")
                return None
                
            # Usar ffprobe para obtener la duración
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(result.stdout)
            
            if 'format' in data and 'duration' in data['format']:
                return float(data['format']['duration'])
            else:
                print("No se pudo obtener la duración del audio.")
                return None
                
        except Exception as e:
            print(f"Error al obtener la duración del audio: {str(e)}")
            return None
    
    def format_duration(self, seconds):
        """
        Formatea una duración en segundos a formato HH:MM:SS.
        
        Args:
            seconds (float): Duración en segundos
            
        Returns:
            str: Duración formateada como HH:MM:SS
        """
        if seconds is None:
            return "00:00:00"
            
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# Ejemplo de uso
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python audio_processor.py ideas_clave.json audio_file.wav")
        sys.exit(1)
    
    ideas_json = sys.argv[1]
    audio_file = sys.argv[2]
    
    processor = AudioProcessor()
    
    # Si hay un tercer argumento, es la transcripción JSON
    if len(sys.argv) > 3:
        transcription_json = sys.argv[3]
        enriched_json = processor.add_timestamps_to_ideas(ideas_json, transcription_json)
        
        if enriched_json:
            # Generar audio para ideas clave
            processor.extract_audio_for_key_ideas(enriched_json, audio_file)
            
            # Generar subtítulos SRT
            processor.generate_subtitle_file(enriched_json, format_type="srt")
    else:
        print("No se proporcionó archivo de transcripción JSON con marcas de tiempo.")
