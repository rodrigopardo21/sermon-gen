# Sistema de Transcripción y Corrección de Sermones con IA

Un sistema automatizado para la transcripción y corrección de sermones utilizando tecnologías de IA.

## Características

- Transcripción automática de audio de videos usando OpenAI Whisper
- Corrección automática de transcripciones usando GPT-4
- Flujo de trabajo optimizado para procesamiento por lotes
- Interfaz simple de línea de comandos

## Tecnologías utilizadas

- Python 3.11
- OpenAI API (Whisper y GPT-4)
- Procesamiento de video y audio
- Control de versiones con Git

## Instalación

1. Clonar el repositorio
2. Crear un entorno virtual: `python -m venv venv`
3. Activar el entorno: `source venv/bin/activate` (Linux/Mac) o `venv\Scripts\activate` (Windows)
4. Instalar dependencias: `pip install -r requirements.txt`
5. Configurar variables de entorno en un archivo `.env` (ver `.env.example`)

## Uso

```bash
python main.py --input video.mp4
