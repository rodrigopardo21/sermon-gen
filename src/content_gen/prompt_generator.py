"""
Módulo para la generación de prompts para nim.video.

Este módulo toma las ideas clave extraídas de un sermón y genera
prompts detallados para crear videos en nim.video, tanto para
el sermón completo como para reels/shorts de las ideas clave.
"""

import os
import json
import random

class PromptGenerator:
    """
    Generador de prompts para nim.video basados en las ideas clave de un sermón.
    
    Esta clase genera dos tipos de prompts:
    1. Para videos largos (sermón completo)
    2. Para videos cortos (reels/shorts con las 7 ideas clave)
    """
    
    def __init__(self):
        """Inicializa el generador de prompts con plantillas base."""
        # Plantillas de escenarios para cada tipo de mensaje
        self.scenario_templates = {
            "planteamiento": [
                "Un amanecer sereno sobre {lugar}, donde {sujeto} {acción} mientras {complemento}. La cámara {movimiento_camara}.",
                "Una vista panorámica de {lugar} al {momento_dia}, donde {sujeto} {acción} con {emocion}. La cámara {movimiento_camara}.",
                "Un paisaje de {lugar} con {elemento_natural} moviéndose suavemente, mientras {sujeto} {acción}. La cámara {movimiento_camara}."
            ],
            "desafio": [
                "Un sendero desafiante en {lugar}, donde {sujeto} {acción} con determinación. La cámara {movimiento_camara}.",
                "Una escena de {lugar} durante {condicion_climatica}, donde {sujeto} {acción} a pesar de las dificultades. La cámara {movimiento_camara}.",
                "Un escenario de {lugar} con {elemento_desafiante}, mientras {sujeto} {acción} mostrando fortaleza. La cámara {movimiento_camara}."
            ],
            "resolucion": [
                "Un espacio de {lugar} iluminado por {fuente_luz}, donde {sujeto} {acción} con {emocion_positiva}. La cámara {movimiento_camara}.",
                "Una comunidad reunida en {lugar}, donde las personas {acción_comunidad} juntas con esperanza. La cámara {movimiento_camara}.",
                "Una vista de {lugar} transformada por {elemento_transformador}, mientras {sujeto} {acción} con paz. La cámara {movimiento_camara}."
            ]
        }
        
        # Elementos para rellenar las plantillas
        self.elementos = {
            "lugar": [
                "montañas majestuosas", "un valle verde", "una playa serena", "un bosque frondoso", 
                "una iglesia rural", "una pradera extensa", "un lago tranquilo", "colinas ondulantes",
                "un jardín floreciente", "un río serpenteante", "un santuario natural", "un prado abierto"
            ],
            "sujeto": [
                "una persona solitaria", "un pequeño grupo de personas", "una familia", "un caminante",
                "un peregrino", "un pastor", "un feligrés", "unos niños", "una congregación",
                "un viajero", "un grupo de amigos", "una comunidad"
            ],
            "acción": [
                "contempla el horizonte", "ora en silencio", "camina con propósito", "levanta las manos",
                "medita tranquilamente", "comparte testimonios", "estudia las escrituras", "adora con devoción",
                "escala con determinación", "navega aguas turbulentas", "planta semillas", "construye con paciencia"
            ],
            "complemento": [
                "reflexiona sobre su fe", "busca sabiduría divina", "encuentra paz interior", 
                "descubre esperanza renovada", "siente la presencia divina", "recibe consuelo espiritual",
                "encuentra fortaleza en la adversidad", "celebra las bendiciones recibidas"
            ],
            "movimiento_camara": [
                "se mueve suavemente alrededor capturando la serenidad", "se acerca lentamente revelando detalles",
                "se eleva suavemente mostrando la grandeza", "gira lentamente capturando el contexto",
                "se aleja para revelar la escena completa", "realiza un paneo suave siguiendo el movimiento",
                "captura un primer plano que transmite emoción", "transita con fluidez entre elementos visuales"
            ],
            "momento_dia": [
                "amanecer", "atardecer", "mediodía", "crepúsculo", "primera luz", "ocaso dorado"
            ],
            "elemento_natural": [
                "hojas", "olas", "nubes", "hierba", "árboles", "flores", "agua", "viento"
            ],
            "condicion_climatica": [
                "una suave lluvia", "un viento persistente", "niebla matutina", "un clima cambiante",
                "nubes de tormenta", "nieve ligera", "luz filtrada", "sol radiante"
            ],
            "elemento_desafiante": [
                "un camino empinado", "obstáculos naturales", "terreno rocoso", "corrientes fuertes",
                "vegetación densa", "alturas imponentes", "desafíos aparentes"
            ],
            "emocion": [
                "reflexión", "determinación", "esperanza", "fe", "introspección", "asombro"
            ],
            "emocion_positiva": [
                "gozo", "paz", "satisfacción", "gratitud", "júbilo", "serenidad", "esperanza"
            ],
            "fuente_luz": [
                "rayos de sol", "un resplandor divino", "luz dorada", "destellos naturales",
                "iluminación suave", "luz filtrada entre nubes", "un brillo celestial"
            ],
            "acción_comunidad": [
                "comparten testimonios", "se animan unas a otras", "oran juntas", "celebran su fe",
                "estudian escrituras", "sirven", "adoran", "construyen vínculos"
            ],
            "elemento_transformador": [
                "luz reveladora", "bondad evidente", "gracia restauradora", "amor transformador",
                "fe inquebrantable", "esperanza renovada", "verdad liberadora"
            ]
        }
    
    def _seleccionar_elemento(self, categoria):
        """Selecciona aleatoriamente un elemento de una categoría."""
        return random.choice(self.elementos.get(categoria, ["elemento"]))
    
    def _generar_descripcion_escena(self, tipo_escena, idea_clave):
        """
        Genera la descripción de una escena basada en el tipo y la idea clave.
        
        Args:
            tipo_escena (str): Tipo de escena (planteamiento, desafio, resolucion)
            idea_clave (dict): Diccionario con la información de la idea clave
            
        Returns:
            str: Descripción de la escena generada
        """
        # Seleccionamos una plantilla para el tipo de escena
        plantillas = self.scenario_templates.get(tipo_escena, self.scenario_templates["planteamiento"])
        plantilla = random.choice(plantillas)
        
        # Rellenamos la plantilla con elementos aleatorios
        escena = plantilla.format(
            lugar=self._seleccionar_elemento("lugar"),
            sujeto=self._seleccionar_elemento("sujeto"),
            acción=self._seleccionar_elemento("acción"),
            complemento=self._seleccionar_elemento("complemento"),
            movimiento_camara=self._seleccionar_elemento("movimiento_camara"),
            momento_dia=self._seleccionar_elemento("momento_dia"),
            elemento_natural=self._seleccionar_elemento("elemento_natural"),
            condicion_climatica=self._seleccionar_elemento("condicion_climatica"),
            elemento_desafiante=self._seleccionar_elemento("elemento_desafiante"),
            emocion=self._seleccionar_elemento("emocion"),
            emocion_positiva=self._seleccionar_elemento("emocion_positiva"),
            fuente_luz=self._seleccionar_elemento("fuente_luz"),
            acción_comunidad=self._seleccionar_elemento("acción_comunidad"),
            elemento_transformador=self._seleccionar_elemento("elemento_transformador")
        )
        
        # Añadimos el texto de la idea clave
        texto_idea = idea_clave.get("texto", "").strip()
        referencia = idea_clave.get("referencia_biblica", "").strip()
        
        if referencia and referencia != "No especificada":
            texto_con_referencia = f'"{texto_idea}" ({referencia})'
        else:
            texto_con_referencia = f'"{texto_idea}"'
        
        return f"{escena} Texto superpuesto dice: {texto_con_referencia}"
    
    def generar_prompt_video_corto(self, ideas_clave, titulo_sermon=None, duracion_audio="00:01:10"):
        """
        Genera un prompt para video corto (reel/short) basado en las 7 ideas clave.
        
        Args:
            ideas_clave (list): Lista de ideas clave extraídas del sermón
            titulo_sermon (str, optional): Título del sermón
            duracion_audio (str): Duración del audio de ideas clave en formato "HH:MM:SS"
            
        Returns:
            str: Prompt generado para nim.video
        """
        if not ideas_clave or len(ideas_clave) == 0:
            return "No se encontraron ideas clave para generar el prompt."
        
        # Ordenamos las ideas por acto y orden
        ideas_clave.sort(key=lambda x: (x.get("acto", 1), x.get("orden", 1)))
        
        # Título para el prompt
        if titulo_sermon:
            titulo_prompt = f"Indicaciones para Video de {titulo_sermon} - Escenas Naturales con Temas Bíblicos"
        else:
            titulo_prompt = "Indicaciones para Video de Escenas Naturales con Temas Bíblicos"
        
        # Instrucciones de configuración para nim.video
        instrucciones = f"""
/* INSTRUCCIONES PARA NIM.VIDEO - NO INCLUIR EN EL PROMPT */
CONFIGURACIÓN RECOMENDADA PARA NIM.VIDEO:
1. Seleccionar "Text-to-Video" (NO text-to-image)
2. Aspect ratio: 9:16 (VERTICAL para Reels/Shorts)
3. Duración: {duracion_audio} (duración del audio de las 7 ideas clave)
4. Después de generar el video:
   - Subir el archivo "sermon_nombre_ideas_clave.wav" de la carpeta 02_audio como audio
   - Subir el archivo "sermon_nombre_ideas_clave_subtitles.srt" de la carpeta 01_transcription como subtítulos
   - Subir los logos de la carpeta 03_images/logos
5. Asegurarse de que haya 7 escenas distintas (una para cada idea)
/* FIN DE INSTRUCCIONES - NO INCLUIR EN EL PROMPT */

"""
        
        # Generamos las descripciones de escenas
        escenas = []
        for i, idea in enumerate(ideas_clave, 1):
            acto = idea.get("acto", 1)
            tipo_escena = "planteamiento"
            if acto == 2:
                tipo_escena = "desafio"
            elif acto == 3:
                tipo_escena = "resolucion"
            
            descripcion = self._generar_descripcion_escena(tipo_escena, idea)
            escenas.append(f"**Escena {i}:** {descripcion}")
        
        # Creamos el prompt completo
        prompt = instrucciones + titulo_prompt + "\n"
        prompt += "\n".join(escenas)
        prompt += "\n\nEsta secuencia entrelaza creativamente la naturaleza, los deportes, temas espirituales y la comunidad, formateado para un carrete de redes sociales cautivador. No olvides añadir los logos de la iglesia en la esquina inferior derecha de cada escena."
        
        return prompt

    def generar_prompt_video_largo(self, titulo_sermon, duracion_aprox, temas_clave=None):
        """
        Genera un prompt para video largo (sermón completo) con instrucciones para nim.video.
        
        Args:
            titulo_sermon (str): Título del sermón
            duracion_aprox (str): Duración aproximada del video (en formato HH:MM:SS)
            temas_clave (list, optional): Lista de temas clave del sermón
            
        Returns:
            str: Prompt generado para nim.video
        """
        # Temas predeterminados si no se proporcionan
        if not temas_clave or len(temas_clave) == 0:
            temas_clave = ["fe cristiana", "esperanza", "vida espiritual", "crecimiento personal"]
        
        # Convertir duración a minutos para el prompt (formato más natural)
        duracion_minutos = "30-40 minutos"  # Valor por defecto
        if duracion_aprox:
            # Intentar convertir HH:MM:SS a minutos aproximados
            try:
                partes = duracion_aprox.split(":")
                if len(partes) == 3:
                    horas = int(partes[0])
                    minutos = int(partes[1])
                    total_minutos = (horas * 60) + minutos
                    if total_minutos < 60:
                        duracion_minutos = f"{total_minutos} minutos"
                    else:
                        duracion_minutos = f"{horas} hora(s) y {minutos} minutos"
            except:
                pass
        
        # Número de escenas recomendado basado en la duración
        num_escenas = max(15, int(float(duracion_minutos.split()[0]) / 2))
        
        # Instrucciones de configuración para nim.video
        instrucciones = f"""
/* INSTRUCCIONES PARA NIM.VIDEO - NO INCLUIR EN EL PROMPT */
CONFIGURACIÓN RECOMENDADA PARA NIM.VIDEO:
1. Seleccionar "Text-to-Video" (NO text-to-image)
2. Aspect ratio: 16:9 (HORIZONTAL para YouTube)
3. Duración: {duracion_aprox} (duración completa del sermón)
4. Especificar explícitamente: "Video completo de {duracion_minutos} con múltiples escenas"
5. Después de generar el video:
   - Subir el archivo "sermon_nombre_audio.wav" de la carpeta 02_audio como audio
   - Subir el archivo "sermon_nombre_transcript_corregido_lineas.txt" de la carpeta 01_transcription como subtítulos
   - Subir los logos de la carpeta 03_images/logos
6. Si nim.video no puede generar un video tan largo, solicitar múltiples segmentos de 2-3 minutos y luego unirlos
/* FIN DE INSTRUCCIONES - NO INCLUIR EN EL PROMPT */

"""
        
        # Generar prompt
        prompt = instrucciones + f"# Instrucciones para Video Completo: {titulo_sermon}\n\n"
        prompt += "## Especificaciones Técnicas:\n"
        prompt += f"- **Duración Total:** {duracion_minutos}\n"
        prompt += "- **Resolución:** 1920x1080 (Full HD)\n"
        prompt += "- **Formato:** 16:9 para YouTube y plataformas de video estándar\n"
        prompt += "- **Logotipos:** Incluir logotipos de la iglesia en la esquina inferior derecha (tamaño aproximado 2cm x 2cm)\n"
        prompt += f"- **Número de escenas:** Crear aproximadamente {num_escenas}-{num_escenas+5} escenas distintas distribuidas uniformemente a lo largo del video\n\n"
        
        prompt += "## Estilo Visual:\n"
        prompt += "- Secuencias de escenas naturales inspiradoras que transmitan espiritualidad y esperanza\n"
        prompt += "- Transiciones suaves entre escenas (disolvencias, fundidos)\n"
        prompt += "- Paleta de colores cálida y reconfortante (tonos dorados, azules suaves, verdes naturales)\n"
        prompt += "- Movimientos de cámara lentos y contemplativos (paneos suaves, acercamientos graduales)\n\n"
        
        prompt += "## Temas Visuales a Incluir:\n"
        temas_visuales = [
            "Escenas de naturaleza (montañas, bosques, playas, amaneceres)",
            "Momentos de reflexión y oración",
            "Comunidad e interacción humana positiva",
            "Símbolos de esperanza y renovación",
            "Iglesias y espacios de adoración serenos"
        ]
        for tema in temas_visuales:
            prompt += f"- {tema}\n"
        prompt += "\n"
        
        prompt += "## Elementos a Integrar:\n"
        prompt += "- **Subtítulos:** Sincronizados con el audio del sermón, claros y legibles\n"
        prompt += "- **Audio Original:** Mantener el audio original del sermón como pista principal\n"
        prompt += "- **Música de Fondo:** (opcional) Música instrumental suave cuando sea apropiado\n\n"
        
        prompt += "## Temáticas del Sermón para Guiar la Selección Visual:\n"
        for tema in temas_clave:
            prompt += f"- {tema}\n"
        prompt += "\n"
        
        prompt += "## Notas Adicionales:\n"
        prompt += f"- Este video debe tener una duración total de {duracion_minutos} con múltiples escenas\n"
        prompt += "- Mantener un ritmo visual que complemente el ritmo del sermón\n"
        prompt += "- Evitar imágenes que distraigan del mensaje principal\n"
        prompt += "- Crear un ambiente visual que invite a la reflexión y conexión espiritual\n"
        prompt += "- Asegurar que los subtítulos sean claros y legibles en todas las escenas\n"
        
        return prompt

    def generar_prompts_para_sermon(self, archivo_ideas_clave, titulo_sermon=None, duracion_audio_completo=None, duracion_audio_ideas=None):
        """
        Genera ambos prompts (video corto y largo) para un sermón.
        
        Args:
            archivo_ideas_clave (str): Ruta al archivo JSON con las ideas clave
            titulo_sermon (str, optional): Título del sermón
            duracion_audio_completo (str): Duración del audio completo en formato "HH:MM:SS"
            duracion_audio_ideas (str): Duración del audio de ideas clave en formato "HH:MM:SS"
            
        Returns:
            tuple: (prompt_corto, prompt_largo, temas_detectados)
        """
        try:
            # Obtener duración si no se proporciona
            if not duracion_audio_completo:
                duracion_audio_completo = "00:30:00"  # Valor por defecto: 30 minutos
            
            if not duracion_audio_ideas:
                duracion_audio_ideas = "00:01:10"  # Valor por defecto: 1 minuto 10 segundos
            
            # Leer el archivo de ideas clave
            with open(archivo_ideas_clave, 'r', encoding='utf-8') as f:
                ideas_clave = json.load(f)
            
            # Si no se proporciona título, extraemos uno del nombre del archivo
            if not titulo_sermon:
                base_name = os.path.basename(archivo_ideas_clave)
                titulo_sermon = base_name.split('_ideas_clave')[0].replace('_', ' ').title()
            
            # Extraer temas clave de las ideas
            temas = set()
            for idea in ideas_clave:
                contexto = idea.get("contexto", "").lower()
                for palabra in contexto.split():
                    if len(palabra) > 5 and palabra not in ["sobre", "entre", "durante", "aunque", "mientras"]:
                        temas.add(palabra.strip(",.;:()[]{}"))
            
            # Generar los prompts
            prompt_corto = self.generar_prompt_video_corto(ideas_clave, titulo_sermon, duracion_audio_ideas)
            prompt_largo = self.generar_prompt_video_largo(titulo_sermon, duracion_audio_completo, list(temas)[:5])
            
            return prompt_corto, prompt_largo, list(temas)
            
        except Exception as e:
            print(f"Error al generar prompts: {str(e)}")
            return "Error al generar prompt para video corto.", "Error al generar prompt para video largo.", []

    def guardar_prompts(self, directorio_proyecto, prompt_corto, prompt_largo):
        """
        Guarda los prompts generados en archivos de texto en el directorio del proyecto.
        
        Args:
            directorio_proyecto (str): Ruta al directorio del proyecto
            prompt_corto (str): Prompt para video corto (reel/short)
            prompt_largo (str): Prompt para video largo (sermón completo)
            
        Returns:
            tuple: (ruta_prompt_corto, ruta_prompt_largo)
        """
        try:
            # Crear directorio para prompts si no existe
            prompts_dir = os.path.join(directorio_proyecto, "prompts")
            os.makedirs(prompts_dir, exist_ok=True)
            
            # Guardar prompt para video corto
            ruta_prompt_corto = os.path.join(prompts_dir, "prompt_video_corto.txt")
            with open(ruta_prompt_corto, 'w', encoding='utf-8') as f:
                f.write(prompt_corto)
            
            # Guardar prompt para video largo
            ruta_prompt_largo = os.path.join(prompts_dir, "prompt_video_largo.txt")
            with open(ruta_prompt_largo, 'w', encoding='utf-8') as f:
                f.write(prompt_largo)
            
            # También crear archivos de instrucciones limpios (sin comentarios)
            prompt_corto_limpio = prompt_corto.split("/* FIN DE INSTRUCCIONES - NO INCLUIR EN EL PROMPT */")[-1].strip()
            prompt_largo_limpio = prompt_largo.split("/* FIN DE INSTRUCCIONES - NO INCLUIR EN EL PROMPT */")[-1].strip()
            
            ruta_prompt_corto_limpio = os.path.join(prompts_dir, "prompt_video_corto_limpio.txt")
            with open(ruta_prompt_corto_limpio, 'w', encoding='utf-8') as f:
                f.write(prompt_corto_limpio)
                
            ruta_prompt_largo_limpio = os.path.join(prompts_dir, "prompt_video_largo_limpio.txt")
            with open(ruta_prompt_largo_limpio, 'w', encoding='utf-8') as f:
                f.write(prompt_largo_limpio)
            
            # Crear un archivo de instrucciones específico
            ruta_instrucciones = os.path.join(prompts_dir, "INSTRUCCIONES_NIMVIDEO.txt")
            instrucciones = """INSTRUCCIONES PARA USAR NIM.VIDEO CON ESTE PROYECTO

PARA EL VIDEO LARGO (SERMÓN COMPLETO):
1. Ir a nim.video y crear un nuevo proyecto
2. Seleccionar "Text-to-Video" (NO text-to-image)
3. Aspect ratio: 16:9 (HORIZONTAL para YouTube)
4. Abrir el archivo "prompt_video_largo_limpio.txt" y copiar todo su contenido
5. Pegar en el campo de prompt de nim.video
6. Generar el video
7. Después de generar:
   - Subir el archivo "sermon_audio.wav" de la carpeta 02_audio como audio
   - Subir el archivo "sermon_transcript_corregido_lineas.txt" de la carpeta 01_transcription como subtítulos
   - Subir los logos de la carpeta 03_images/logos
8. Descargar el video resultante y guardarlo en la carpeta 04_videos

PARA EL VIDEO CORTO (REEL/SHORT):
1. Ir a nim.video y crear un nuevo proyecto
2. Seleccionar "Text-to-Video" (NO text-to-image)
3. Aspect ratio: 9:16 (VERTICAL para Reels/Shorts)
4. Abrir el archivo "prompt_video_corto_limpio.txt" y copiar todo su contenido
5. Pegar en el campo de prompt de nim.video
6. Generar el video
7. Después de generar:
   - Subir el archivo "sermon_ideas_clave.wav" de la carpeta 02_audio como audio
   - Subir el archivo "sermon_ideas_clave_subtitles.srt" de la carpeta 01_transcription como subtítulos
   - Subir los logos de la carpeta 03_images/logos
8. Descargar el video resultante y guardarlo en la carpeta 04_videos
"""
            
            with open(ruta_instrucciones, 'w', encoding='utf-8') as f:
                f.write(instrucciones)
            
            print(f"Prompts guardados en el directorio: {prompts_dir}")
            print(f"Se ha creado un archivo de instrucciones detalladas: {ruta_instrucciones}")
            return ruta_prompt_corto, ruta_prompt_largo
                
        except Exception as e:
            print(f"Error al guardar prompts: {str(e)}")
            return None, None

# Ejemplo de uso
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python prompt_generator.py ruta/a/ideas_clave.json [directorio_salida]")
        sys.exit(1)
    
    archivo_ideas = sys.argv[1]
    directorio_salida = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(archivo_ideas)
    
    generator = PromptGenerator()
    prompt_corto, prompt_largo, temas = generator.generar_prompts_para_sermon(archivo_ideas)
    
    print("\n=== PROMPT PARA VIDEO CORTO (REEL/SHORT) ===")
    print(prompt_corto)
    
    print("\n=== PROMPT PARA VIDEO LARGO (SERMÓN COMPLETO) ===")
    print(prompt_largo)
    
    print("\n=== TEMAS DETECTADOS ===")
    print(", ".join(temas))
    
    generator.guardar_prompts(directorio_salida, prompt_corto, prompt_largo)
