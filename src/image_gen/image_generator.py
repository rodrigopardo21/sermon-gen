"""
Módulo de generación de imágenes para sermones usando APIs externas.

Este módulo proporciona funcionalidades para generar imágenes basadas en el 
contenido de sermones, utilizando APIs de generación de imágenes como Stability AI
para crear recursos visuales que acompañen tanto a videos largos como a clips cortos.

Características principales:
    - Generación de imágenes inspiradas en el contenido del sermón
    - Personalización de estilos visuales según el contexto y la temática
    - Integración con el sistema de procesamiento de sermones existente
    - Sistema de caché para optimizar el uso de créditos API
"""

import os
import sys
import subprocess
from pathlib import Path
import time
from dotenv import load_dotenv
import requests
from PIL import Image
from io import BytesIO
import base64
import json

# Cargar variables de entorno
load_dotenv()

class ImageGenerator:
    """
    Clase para generar imágenes basadas en el contenido de sermones usando APIs externas.
    
    Esta clase proporciona métodos para generar imágenes utilizando
    servicios de IA como Stability AI, adaptados al estilo visual 
    necesario para acompañar sermones.
    
    Atributos:
        api_key (str): Clave API para el servicio de generación
        output_dir (str): Directorio donde se guardarán las imágenes generadas
        use_cache (bool): Si se debe utilizar caché para optimizar créditos
        image_cache (dict): Diccionario para almacenar prompts y rutas de imágenes
    """
    
    def __init__(self, output_dir="output_images", api_key=None, use_cache=True, sermon_dir=None):
        """
        Inicializa el generador de imágenes con las configuraciones necesarias.
        
        Args:
            output_dir (str): Directorio donde se guardarán las imágenes
            api_key (str): Clave de API para el servicio (si se proporciona)
            use_cache (bool): Si se debe utilizar caché para reutilizar imágenes similares
            sermon_dir (str): Directorio específico del sermón (si se proporciona)
        """
        self.api_key = api_key or os.getenv('STABILITY_API_KEY')
        
        # Si se proporciona un directorio de sermón, usarlo para organizar las imágenes
        if sermon_dir:
            self.output_dir = os.path.join(sermon_dir, "imagenes")
        else:
            self.output_dir = output_dir
            
        self.use_cache = use_cache
        self.cache_file = os.path.join(self.output_dir, "image_cache.json")
        self.image_cache = self._load_cache()
        
        # Crear directorio de salida si no existe
        os.makedirs(self.output_dir, exist_ok=True)
        
        if not self.api_key:
            print("ADVERTENCIA: No se encontró la clave API de Stability AI. Configura STABILITY_API_KEY en el archivo .env")
    
    def _load_cache(self):
        """
        Carga la caché de imágenes si existe.
        
        Returns:
            dict: Diccionario con prompts como claves y rutas de imágenes como valores
        """
        if os.path.exists(self.cache_file) and self.use_cache:
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al cargar la caché: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Guarda la caché de imágenes en un archivo JSON."""
        if self.use_cache:
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump(self.image_cache, f, indent=2)
            except Exception as e:
                print(f"Error al guardar la caché: {e}")
    
    def _get_cached_image(self, prompt):
        """
        Busca una imagen en caché basada en un prompt similar.
        
        Args:
            prompt (str): El prompt para el que buscar imágenes similares
            
        Returns:
            str or None: Ruta a la imagen en caché o None si no se encuentra
        """
        if not self.use_cache:
            return None
            
        # Simplificamos el prompt para comparación
        simple_prompt = ' '.join(sorted(set(prompt.lower().split())))
        
        # Buscamos prompts similares
        for cached_prompt, image_path in self.image_cache.items():
            cached_simple = ' '.join(sorted(set(cached_prompt.lower().split())))
            # Calculamos similitud básica (podría mejorarse)
            common_words = set(simple_prompt.split()) & set(cached_simple.split())
            if not common_words:
                continue
                
            similarity = len(common_words) / max(len(simple_prompt.split()), len(cached_simple.split()))
            
            # Si la similitud es alta y el archivo existe, reutilizamos
            if similarity > 0.7 and os.path.exists(image_path):
                print(f"Reutilizando imagen en caché para prompt similar (similitud: {similarity:.2f})")
                return image_path
        
        return None
    
    def _create_prompt(self, text, style_prefix=""):
        """
        Crea un prompt efectivo para la generación de imágenes más naturales.
        
        Args:
            text (str): Texto que inspira la imagen
            style_prefix (str): Prefijo que define el estilo visual
            
        Returns:
            str, str: Prompt optimizado y negative prompt para la generación de imágenes
        """
        # Extraer palabras clave del texto
        keywords = self._extract_keywords(text)
        
        # Estilo base mejorado para paisajes naturales
        if not style_prefix:
            style_prefix = "beautiful natural landscape, aerial drone photography, "
            style_prefix += "golden hour lighting, real photograph, stunning nature, "
            style_prefix += "National Geographic style, photorealistic, "
        
        # Categorías basadas en palabras clave
        nature_terms = {"cielo": "sky", "montaña": "mountains", "mar": "ocean", 
                       "océano": "sea", "río": "river", "bosque": "forest", 
                       "árbol": "trees", "naturaleza": "nature", "agua": "water",
                       "playa": "beach", "lago": "lake", "amanecer": "sunrise",
                       "atardecer": "sunset"}
        
        # Identificar términos de naturaleza presentes
        nature_keywords = []
        for keyword in keywords:
            for spanish, english in nature_terms.items():
                if spanish in keyword.lower():
                    nature_keywords.append(english)
                    break
        
        # Si no hay términos específicos de naturaleza, usamos algunos genéricos
        if not nature_keywords:
            nature_keywords = ["mountains", "forest", "sky"]
        
        # Combinar con palabras clave de naturaleza
        keyword_text = ", ".join(nature_keywords)
        
        prompt = f"{style_prefix} beautiful natural landscape with {keyword_text}, real photograph"
        
        # Negative prompt más específico
        negative_prompt = "digital art, 3D rendering, cartoon, illustration, painting, drawing, artificial structures, buildings, temple, mosque, church, CGI, low quality, text, watermark"
        
        return prompt, negative_prompt
    
    def _extract_keywords(self, text, max_keywords=5):
        """
        Extrae palabras clave significativas del texto.
        
        Args:
            text (str): Texto del segmento
            max_keywords (int): Número máximo de palabras clave
            
        Returns:
            list: Lista de palabras clave
        """
        # Lista de palabras vacías en español
        stop_words = set([
            "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "si",
            "de", "del", "a", "ante", "con", "en", "para", "por", "según", "sin", "sobre",
            "tras", "durante", "mediante", "que", "quien", "cuyo", "como", "cuando", "donde",
            "cual", "esto", "esta", "estos", "estas", "ese", "esa", "esos", "esas"
        ])
        
        # Dividir el texto en palabras y filtrar palabras vacías
        words = text.lower().split()
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Contar frecuencias
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Ordenar por frecuencia y tomar las top N
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, count in sorted_words[:max_keywords]]
        
        # Agregar palabras bíblicas relevantes si están presentes
        biblical_terms = ["dios", "jesús", "cristo", "espíritu", "santo", "biblia", 
                         "oración", "fe", "amor", "esperanza", "paz", "gloria", "salvación"]
        
        for term in biblical_terms:
            if term in text.lower() and term not in keywords:
                keywords.append(term)
        
        return keywords[:max_keywords]  # Limitar a max_keywords
    
    def generate_image_with_stability(self, text, filename_prefix, style_prefix=""):
        """
        Genera una imagen usando la API de Stability AI con soporte de caché.
        
        Args:
            text (str): Texto que inspira la imagen
            filename_prefix (str): Prefijo para el nombre del archivo
            style_prefix (str): Prefijo que define el estilo visual
            
        Returns:
            str: Ruta a la imagen generada
        """
        if not self.api_key:
            raise ValueError("Se requiere una clave API de Stability AI. Configura STABILITY_API_KEY en el archivo .env")
        
        # Crear prompt optimizado
        prompt, negative_prompt = self._create_prompt(text, style_prefix)
        
        print(f"Generando imagen para: {filename_prefix}")
        print(f"Prompt: {prompt}")
        
        # Verificar si tenemos una imagen en caché
        cached_image = self._get_cached_image(prompt)
        if cached_image:
            print(f"Usando imagen en caché: {cached_image}")
            
            # Copiamos la imagen en caché a la ubicación esperada para este prefijo
            output_path = os.path.join(self.output_dir, f"{filename_prefix}.png")
            if cached_image != output_path:
                import shutil
                shutil.copy2(cached_image, output_path)
                
            return output_path
        
        # Configuración para la API de Stability AI
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Usamos 1024x1024 que es una dimensión permitida
        body = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                },
                {
                    "text": negative_prompt,
                    "weight": -0.7  # Mayor peso para el negativo para evitar estructuras artificiales
                }
            ],
            "cfg_scale": 7.5,
            "height": 1024,
            "width": 1024,  # Dimensiones permitidas por la API
            "samples": 1,
            "steps": 30,
            "style_preset": "photographic"  # Forzar estilo fotográfico
        }
        
        # Realizar la solicitud a la API
        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()  # Verificar si hay errores en la respuesta
            
            data = response.json()
            
            # Procesar la respuesta
            for i, image_data in enumerate(data["artifacts"]):
                # Guardar la imagen
                image_bytes = base64.b64decode(image_data["base64"])
                image = Image.open(BytesIO(image_bytes))
                
                # Opcionalmente, redimensionar a la relación de aspecto deseada
                if filename_prefix.startswith("test"):
                    # Para pruebas mantenemos el tamaño original
                    resized_image = image
                else:
                    # Para uso en video, redimensionamos a 16:9
                    resized_image = image.resize((1280, 720), Image.LANCZOS)
                
                output_path = os.path.join(self.output_dir, f"{filename_prefix}.png")
                resized_image.save(output_path)
                
                # Añadir a la caché
                self.image_cache[prompt] = output_path
                self._save_cache()
                
                print(f"Imagen guardada en: {output_path}")
                return output_path
                
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud a la API: {e}")
            # Si es un error de respuesta, mostrar detalles
            if hasattr(e, 'response') and e.response is not None:
                print(f"Código de estado: {e.response.status_code}")
                print(f"Respuesta: {e.response.text}")
            raise
        
        return None
    
    def generate_image(self, text, filename_prefix, style_prefix=""):
        """
        Genera una imagen basada en el texto proporcionado.
        
        Este método es un wrapper para el método específico de generación.
        
        Args:
            text (str): Texto que inspira la imagen
            filename_prefix (str): Prefijo para el nombre del archivo
            style_prefix (str): Prefijo que define el estilo visual
            
        Returns:
            str: Ruta a la imagen generada
        """
        # Por defecto usamos la API de Stability AI
        return self.generate_image_with_stability(text, filename_prefix, style_prefix)


# Función para verificar que la API key está configurada
def setup_stability_api_key():
    """
    Solicita y configura la clave API de Stability AI si no está configurada.
    
    Returns:
        bool: True si la clave está configurada, False en caso contrario
    """
    api_key = os.getenv('STABILITY_API_KEY')
    
    if not api_key:
        print("\n===== Configuración de Stability AI =====")
        print("Para generar imágenes, necesitas una clave API de Stability AI.")
        print("Puedes obtener una clave registrándote en: https://platform.stability.ai/")
        print("\nUna vez que tengas tu clave, puedes:")
        print("1. Añadirla al archivo .env con la forma: STABILITY_API_KEY=tu-clave-api")
        print("2. O ingresarla a continuación.\n")
        
        user_key = input("Ingresa tu clave API de Stability AI (o presiona Enter para omitir): ").strip()
        
        if user_key:
            # Guardar la clave en el archivo .env
            env_file = ".env"
            if os.path.exists(env_file):
                with open(env_file, "r") as f:
                    env_content = f.read()
                
                # Verificar si ya existe la variable
                if "STABILITY_API_KEY=" in env_content:
                    env_content = "\n".join([
                        line for line in env_content.split("\n") 
                        if not line.startswith("STABILITY_API_KEY=")
                    ])
                
                with open(env_file, "w") as f:
                    f.write(f"{env_content}\nSTABILITY_API_KEY={user_key}\n")
            else:
                with open(env_file, "w") as f:
                    f.write(f"STABILITY_API_KEY={user_key}\n")
            
            print("Clave API guardada correctamente en el archivo .env")
            # Recargar las variables de entorno
            load_dotenv(override=True)
            return True
        else:
            print("No se proporcionó una clave API. La generación de imágenes no estará disponible.")
            return False
    
    return True

# Función para crear estructura de directorios para un sermón
def create_sermon_directory(sermon_name, base_dir="sermons"):
    """
    Crea la estructura de directorios para un nuevo sermón.
    
    Args:
        sermon_name (str): Nombre o identificador del sermón
        base_dir (str): Directorio base donde se crearán las carpetas
        
    Returns:
        str: Ruta al directorio del sermón creado
    """
    # Crear directorio base si no existe
    os.makedirs(base_dir, exist_ok=True)
    
    # Crear directorio específico para este sermón
    sermon_dir = os.path.join(base_dir, sermon_name)
    os.makedirs(sermon_dir, exist_ok=True)
    
    # Crear subdirectorios para diferentes tipos de archivos
    subdirs = [
        os.path.join(sermon_dir, "audio"),
        os.path.join(sermon_dir, "transcripcion"),
        os.path.join(sermon_dir, "ideas_clave"),
        os.path.join(sermon_dir, "imagenes"),
        os.path.join(sermon_dir, "videos")
    ]
    
    for subdir in subdirs:
        os.makedirs(subdir, exist_ok=True)
    
    print(f"Creada estructura de directorios para el sermón: {sermon_name}")
    return sermon_dir

# Función para probar el generador independientemente
def test_image_generator():
    """Prueba simple del generador de imágenes con optimización de créditos."""
    # Verificar y configurar la clave API si es necesario
    if not setup_stability_api_key():
        print("No se puede realizar la prueba sin una clave API.")
        return
    
    # Crear directorio de sermón para la prueba
    sermon_dir = create_sermon_directory("sermon_prueba")
    
    # Crear generador con directorio específico del sermón
    generator = ImageGenerator(sermon_dir=sermon_dir, use_cache=True)
    
    # Primera imagen de prueba con estilo más natural
    test_text = "El amor de Dios es como un río que fluye hacia nosotros, llenándonos de paz y esperanza. Jesús nos mostró el camino a través de su sacrificio en la cruz."
    
    try:
        print("Generando imagen de prueba con estilo natural...")
        style_prefix = "beautiful landscape photography, aerial view, drone photography, "
        style_prefix += "golden hour, mountains and forests, National Geographic style, "
        style_prefix += "natural scenery, 8k, detailed, realistic, "
        
        image_path = generator.generate_image(
            test_text,
            "paisaje_natural",
            style_prefix
        )
        
        if image_path:
            print(f"Imagen generada en: {image_path}")
            
            # Segunda imagen con texto similar (debería usar caché)
            print("\nGenerando segunda imagen con texto similar (debería usar caché)...")
            similar_text = "El amor divino es como agua que fluye, dándonos paz. Cristo nos mostró el camino con su sacrificio."
            image_path2 = generator.generate_image(
                similar_text,
                "paisaje_natural_2",
                style_prefix
            )
            
            if image_path2:
                print(f"Segunda imagen generada/reutilizada en: {image_path2}")
            
        else:
            print("No se pudo generar la imagen.")
        
    except Exception as e:
        print(f"Error en la prueba: {str(e)}")

if __name__ == "__main__":
    # Si se ejecuta este archivo directamente, realizar una prueba
    test_image_generator()
