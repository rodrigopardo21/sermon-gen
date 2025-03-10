"""
Script Principal para Transcripción de Sermones
Este script demuestra el uso de nuestro sistema de transcripción y generación
de contenido para redes sociales. Actúa como un punto de entrada que coordina
todo el proceso de manera organizada y segura.
"""

import os
from dotenv import load_dotenv
from src.transcription.transcriber import SermonTranscriber

# Cargamos las variables de entorno para manejar información sensible de manera segura
load_dotenv()

def main():
    """
    Función principal que coordina el proceso de transcripción y generación de contenido.
    Esta función demuestra el flujo completo del proceso, desde la configuración
    inicial hasta la generación de contenido para redes sociales.
    """
    # Configuramos las rutas de los directorios de trabajo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, 'input_videos')
    output_dir = os.path.join(base_dir, 'output_transcriptions')

    # Creamos los directorios si no existen
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Obtenemos la clave de API de las variables de entorno
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("No se encontró la clave de API de OpenAI. Por favor, configura OPENAI_API_KEY en el archivo .env")

        # Inicializamos nuestro transcriptor
        transcriber = SermonTranscriber(
            input_dir=input_dir,
            output_dir=output_dir,
            api_key=api_key
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
            try:
                # Realizamos la transcripción
                transcription_data = transcriber.process_video(video_filename)
                
                # Preparamos contenido para redes sociales
                social_content = transcriber.prepare_social_media_content(transcription_data)
                
                # Mostramos un resumen de los resultados
                print("\nResumen de contenido generado:")
                print(f"- Segmentos para YouTube: {len(social_content['youtube'])}")
                print(f"- Clips para Reels: {len(social_content['reels'])}")
                print(f"- Clips para TikTok: {len(social_content['tiktok'])}")
                
            except Exception as e:
                print(f"Error procesando {video_filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print("\nAhora puedes revisar la transcripción en formato de texto plano en la carpeta output_transcriptions.")
        print("Una vez revisada y corregida, puedes continuar con la generación de contenido multimedia.")

        print("\n¡Proceso completado!")
        print(f"Las transcripciones se han guardado en: {output_dir}")

    except Exception as e:
        print(f"Error en la ejecución del programa: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
