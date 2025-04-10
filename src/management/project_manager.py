"""
Módulo para la gestión de proyectos de sermones.

Este módulo se encarga de organizar la estructura de carpetas y archivos
para cada sermón procesado, facilitando la organización y el seguimiento
de los proyectos de transcripción y generación de videos.
"""

import os
import shutil
import json
import datetime
import uuid
from pathlib import Path

class SermonProjectManager:
    """
    Gestor de proyectos para la transcripción y generación de videos de sermones.
    
    Esta clase se encarga de:
    1. Crear una estructura de carpetas para cada sermón
    2. Organizar los archivos generados en sus respectivas carpetas
    3. Llevar un registro de los sermones procesados
    """
    
    def __init__(self, base_dir, projetos_dir="sermon_projects"):
        """
        Inicializa el gestor de proyectos.
        
        Args:
            base_dir (str): Directorio base del proyecto
            projetos_dir (str): Nombre del directorio donde se guardarán los proyectos de sermones
        """
        self.base_dir = base_dir
        self.projects_dir = os.path.join(base_dir, projetos_dir)
        self.logs_dir = os.path.join(self.projects_dir, "_logs")
        self.logos_dir = os.path.join(base_dir, "src", "assets", "logos")
        
        # Crear directorios base si no existen
        os.makedirs(self.projects_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Ruta al archivo de registro de proyectos
        self.projects_registry = os.path.join(self.logs_dir, "projects_registry.json")
        
        # Cargar o crear el registro de proyectos
        self.load_projects_registry()
    
    def load_projects_registry(self):
        """Carga el registro de proyectos o crea uno nuevo si no existe."""
        if os.path.exists(self.projects_registry):
            try:
                with open(self.projects_registry, 'r', encoding='utf-8') as f:
                    self.registry = json.load(f)
            except Exception as e:
                print(f"Error al cargar el registro de proyectos: {e}")
                self.registry = {"projects": []}
        else:
            self.registry = {"projects": []}
            self.save_projects_registry()
    
    def save_projects_registry(self):
        """Guarda el registro de proyectos en el archivo JSON."""
        try:
            with open(self.projects_registry, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar el registro de proyectos: {e}")
    
    def create_project_structure(self, video_filename, sermon_title=None):
        """
        Crea la estructura de carpetas para un nuevo proyecto de sermón.
        
        Args:
            video_filename (str): Nombre del archivo de video original
            sermon_title (str, optional): Título del sermón. Si no se proporciona,
                                         se usará el nombre del archivo.
        
        Returns:
            dict: Diccionario con las rutas de las carpetas creadas y metadatos del proyecto
        """
        # Generar un ID único para el proyecto (usando timestamp y uuid)
        project_id = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Si no se proporciona un título, usamos el nombre del archivo sin extensión
        if not sermon_title:
            sermon_title = os.path.splitext(os.path.basename(video_filename))[0]
        
        # Crear nombre de carpeta (sanitizado)
        folder_name = f"{project_id}_{self._sanitize_filename(sermon_title)}"
        project_dir = os.path.join(self.projects_dir, folder_name)
        
        # Crear estructura de subcarpetas
        dirs = {
            "project": project_dir,
            "transcription": os.path.join(project_dir, "01_transcription"),
            "audio": os.path.join(project_dir, "02_audio"),
            "images": os.path.join(project_dir, "03_images"),
            "videos": os.path.join(project_dir, "04_videos"),
            "output": os.path.join(project_dir, "05_output"),
            "temp": os.path.join(project_dir, "temp")
        }
        
        # Crear todas las carpetas
        for dir_path in dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Copiar los logos al directorio del proyecto para tenerlos disponibles
        logos_dest = os.path.join(dirs["images"], "logos")
        os.makedirs(logos_dest, exist_ok=True)
        
        # Buscar archivos logo en la carpeta de logos
        if os.path.exists(self.logos_dir):
            logo_files = [f for f in os.listdir(self.logos_dir) if f.endswith('.png') or f.endswith('.jpg')]
            for logo_file in logo_files:
                try:
                    shutil.copy(
                        os.path.join(self.logos_dir, logo_file),
                        os.path.join(logos_dest, logo_file)
                    )
                    print(f"Logo copiado: {logo_file}")
                except Exception as e:
                    print(f"Error al copiar logo {logo_file}: {e}")
        
        # Crear archivo de metadatos del proyecto
        metadata = {
            "project_id": project_id,
            "sermon_title": sermon_title,
            "video_filename": video_filename,
            "creation_date": datetime.datetime.now().isoformat(),
            "status": "initialized",
            "directories": dirs
        }
        
        # Guardar metadatos en el proyecto
        metadata_path = os.path.join(project_dir, "project_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Registrar el proyecto en el registro global
        project_entry = {
            "project_id": project_id,
            "sermon_title": sermon_title,
            "folder_name": folder_name,
            "creation_date": metadata["creation_date"],
            "status": "initialized"
        }
        self.registry["projects"].append(project_entry)
        self.save_projects_registry()
        
        print(f"Proyecto creado: {sermon_title} (ID: {project_id})")
        print(f"Carpeta del proyecto: {project_dir}")
        
        return metadata
    
    def copy_input_file(self, input_path, project_metadata):
        """
        Copia el archivo de entrada al directorio del proyecto.
        
        Args:
            input_path (str): Ruta al archivo de entrada
            project_metadata (dict): Metadatos del proyecto
            
        Returns:
            str: Ruta al archivo copiado
        """
        # Verificar que el archivo exista
        if not os.path.exists(input_path):
            print(f"Error: El archivo {input_path} no existe")
            return None
        
        # Destino será la carpeta temporal del proyecto
        dest_path = os.path.join(
            project_metadata["directories"]["temp"],
            os.path.basename(input_path)
        )
        
        try:
            shutil.copy2(input_path, dest_path)
            print(f"Archivo copiado: {os.path.basename(input_path)}")
            return dest_path
        except Exception as e:
            print(f"Error al copiar el archivo: {e}")
            return None
    
    def organize_transcription_files(self, project_metadata, transcription_files):
        """
        Organiza los archivos de transcripción en la estructura del proyecto.
        
        Args:
            project_metadata (dict): Metadatos del proyecto
            transcription_files (dict): Diccionario con las rutas a los archivos de transcripción:
                {
                    "txt": "ruta/al/transcripcion.txt",
                    "json": "ruta/al/transcripcion.json",
                    "corrected": "ruta/al/transcripcion_corregida.txt",
                    "ideas_json": "ruta/al/ideas_clave.json",
                    "ideas_txt": "ruta/al/ideas_clave_editable.txt"
                }
        
        Returns:
            dict: Diccionario con las rutas actualizadas
        """
        transcription_dir = project_metadata["directories"]["transcription"]
        new_paths = {}
        
        for file_type, file_path in transcription_files.items():
            if file_path and os.path.exists(file_path):
                # Destino en la carpeta de transcripción
                dest_path = os.path.join(transcription_dir, os.path.basename(file_path))
                try:
                    shutil.copy2(file_path, dest_path)
                    new_paths[file_type] = dest_path
                    print(f"Archivo de transcripción copiado: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"Error al copiar archivo de transcripción: {e}")
                    new_paths[file_type] = file_path  # Mantener ruta original si falla
            else:
                new_paths[file_type] = None
        
        # Actualizar metadatos del proyecto
        self.update_project_status(project_metadata["project_id"], "transcription_completed", {
            "transcription_files": new_paths
        })
        
        return new_paths
    
    def organize_audio_files(self, project_metadata, audio_files):
        """
        Organiza los archivos de audio en la estructura del proyecto.
        
        Args:
            project_metadata (dict): Metadatos del proyecto
            audio_files (dict/list): Diccionario o lista con las rutas a los archivos de audio
            
        Returns:
            dict/list: Diccionario o lista con las rutas actualizadas
        """
        audio_dir = project_metadata["directories"]["audio"]
        
        # Si es un diccionario
        if isinstance(audio_files, dict):
            new_paths = {}
            for audio_type, audio_path in audio_files.items():
                if audio_path and os.path.exists(audio_path):
                    dest_path = os.path.join(audio_dir, os.path.basename(audio_path))
                    try:
                        shutil.copy2(audio_path, dest_path)
                        new_paths[audio_type] = dest_path
                        print(f"Archivo de audio copiado: {os.path.basename(audio_path)}")
                    except Exception as e:
                        print(f"Error al copiar archivo de audio: {e}")
                        new_paths[audio_type] = audio_path
                else:
                    new_paths[audio_type] = None
        
        # Si es una lista
        elif isinstance(audio_files, list):
            new_paths = []
            for audio_path in audio_files:
                if audio_path and os.path.exists(audio_path):
                    dest_path = os.path.join(audio_dir, os.path.basename(audio_path))
                    try:
                        shutil.copy2(audio_path, dest_path)
                        new_paths.append(dest_path)
                        print(f"Archivo de audio copiado: {os.path.basename(audio_path)}")
                    except Exception as e:
                        print(f"Error al copiar archivo de audio: {e}")
                        new_paths.append(audio_path)
                else:
                    new_paths.append(None)
        
        # Actualizar metadatos del proyecto
        self.update_project_status(project_metadata["project_id"], "audio_organized", {
            "audio_files": new_paths
        })
        
        return new_paths
    
    def organize_image_files(self, project_metadata, image_files, subfolder=None):
        """
        Organiza las imágenes generadas en la estructura del proyecto.
        
        Args:
            project_metadata (dict): Metadatos del proyecto
            image_files (dict/list): Diccionario o lista con las rutas a las imágenes
            subfolder (str, optional): Subcarpeta dentro de images para organizar las imágenes
            
        Returns:
            dict/list: Diccionario o lista con las rutas actualizadas
        """
        images_dir = project_metadata["directories"]["images"]
        
        # Si hay subfolder, la creamos
        if subfolder:
            images_dir = os.path.join(images_dir, subfolder)
            os.makedirs(images_dir, exist_ok=True)
        
        # Si es un diccionario
        if isinstance(image_files, dict):
            new_paths = {}
            for image_type, image_path in image_files.items():
                if image_path and os.path.exists(image_path):
                    dest_path = os.path.join(images_dir, os.path.basename(image_path))
                    try:
                        shutil.copy2(image_path, dest_path)
                        new_paths[image_type] = dest_path
                        print(f"Imagen copiada: {os.path.basename(image_path)}")
                    except Exception as e:
                        print(f"Error al copiar imagen: {e}")
                        new_paths[image_type] = image_path
                else:
                    new_paths[image_type] = None
        
        # Si es una lista
        elif isinstance(image_files, list):
            new_paths = []
            for image_path in image_files:
                if image_path and os.path.exists(image_path):
                    dest_path = os.path.join(images_dir, os.path.basename(image_path))
                    try:
                        shutil.copy2(image_path, dest_path)
                        new_paths.append(dest_path)
                        print(f"Imagen copiada: {os.path.basename(image_path)}")
                    except Exception as e:
                        print(f"Error al copiar imagen: {e}")
                        new_paths.append(image_path)
                else:
                    new_paths.append(None)
        
        # Actualizar metadatos del proyecto
        status_data = {"image_files": new_paths}
        if subfolder:
            status_data["subfolder"] = subfolder
            
        self.update_project_status(project_metadata["project_id"], "images_organized", status_data)
        
        return new_paths
    
    def organize_video_files(self, project_metadata, video_files, subfolder=None):
        """
        Organiza los videos generados en la estructura del proyecto.
        
        Args:
            project_metadata (dict): Metadatos del proyecto
            video_files (dict/list): Diccionario o lista con las rutas a los videos
            subfolder (str, optional): Subcarpeta dentro de videos para organizar los videos
            
        Returns:
            dict/list: Diccionario o lista con las rutas actualizadas
        """
        videos_dir = project_metadata["directories"]["videos"]
        
        # Si hay subfolder, la creamos
        if subfolder:
            videos_dir = os.path.join(videos_dir, subfolder)
            os.makedirs(videos_dir, exist_ok=True)
        
        # Si es un diccionario
        if isinstance(video_files, dict):
            new_paths = {}
            for video_type, video_path in video_files.items():
                if video_path and os.path.exists(video_path):
                    dest_path = os.path.join(videos_dir, os.path.basename(video_path))
                    try:
                        shutil.copy2(video_path, dest_path)
                        new_paths[video_type] = dest_path
                        print(f"Video copiado: {os.path.basename(video_path)}")
                    except Exception as e:
                        print(f"Error al copiar video: {e}")
                        new_paths[video_type] = video_path
                else:
                    new_paths[video_type] = None
        
        # Si es una lista
        elif isinstance(video_files, list):
            new_paths = []
            for video_path in video_files:
                if video_path and os.path.exists(video_path):
                    dest_path = os.path.join(videos_dir, os.path.basename(video_path))
                    try:
                        shutil.copy2(video_path, dest_path)
                        new_paths.append(dest_path)
                        print(f"Video copiado: {os.path.basename(video_path)}")
                    except Exception as e:
                        print(f"Error al copiar video: {e}")
                        new_paths.append(video_path)
                else:
                    new_paths.append(None)
        
        # Actualizar metadatos del proyecto
        status_data = {"video_files": new_paths}
        if subfolder:
            status_data["subfolder"] = subfolder
            
        self.update_project_status(project_metadata["project_id"], "videos_organized", status_data)
        
        return new_paths
    
    def save_final_output(self, project_metadata, output_files, output_type="final"):
        """
        Guarda los archivos finales en la carpeta de salida del proyecto.
        
        Args:
            project_metadata (dict): Metadatos del proyecto
            output_files (dict/list): Diccionario o lista con las rutas a los archivos finales
            output_type (str): Tipo de salida (final, youtube, reels, etc.)
            
        Returns:
            dict/list: Diccionario o lista con las rutas actualizadas
        """
        output_dir = project_metadata["directories"]["output"]
        
        # Crear subcarpeta según el tipo de salida
        output_subdir = os.path.join(output_dir, output_type)
        os.makedirs(output_subdir, exist_ok=True)
        
        # Si es un diccionario
        if isinstance(output_files, dict):
            new_paths = {}
            for file_type, file_path in output_files.items():
                if file_path and os.path.exists(file_path):
                    dest_path = os.path.join(output_subdir, os.path.basename(file_path))
                    try:
                        shutil.copy2(file_path, dest_path)
                        new_paths[file_type] = dest_path
                        print(f"Archivo final copiado: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"Error al copiar archivo final: {e}")
                        new_paths[file_type] = file_path
                else:
                    new_paths[file_type] = None
        
        # Si es una lista
        elif isinstance(output_files, list):
            new_paths = []
            for file_path in output_files:
                if file_path and os.path.exists(file_path):
                    dest_path = os.path.join(output_subdir, os.path.basename(file_path))
                    try:
                        shutil.copy2(file_path, dest_path)
                        new_paths.append(dest_path)
                        print(f"Archivo final copiado: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"Error al copiar archivo final: {e}")
                        new_paths.append(file_path)
                else:
                    new_paths.append(None)
        
        # Actualizar metadatos del proyecto
        self.update_project_status(project_metadata["project_id"], f"{output_type}_completed", {
            f"{output_type}_files": new_paths
        })
        
        return new_paths
    
    def update_project_status(self, project_id, status, additional_data=None):
        """
        Actualiza el estado de un proyecto y añade datos adicionales.
        
        Args:
            project_id (str): ID del proyecto
            status (str): Nuevo estado del proyecto
            additional_data (dict, optional): Datos adicionales a guardar
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        # Buscar el proyecto en el registro
        project_found = False
        for project in self.registry["projects"]:
            if project["project_id"] == project_id:
                project["status"] = status
                project["last_updated"] = datetime.datetime.now().isoformat()
                if additional_data:
                    for key, value in additional_data.items():
                        project[key] = value
                project_found = True
                break
        
        if not project_found:
            print(f"Error: No se encontró el proyecto con ID {project_id}")
            return False
        
        # Guardar el registro actualizado
        self.save_projects_registry()
        
        # Actualizar también el archivo de metadatos del proyecto
        folder_name = None
        for project in self.registry["projects"]:
            if project["project_id"] == project_id:
                folder_name = project["folder_name"]
                break
        
        if folder_name:
            project_dir = os.path.join(self.projects_dir, folder_name)
            metadata_path = os.path.join(project_dir, "project_metadata.json")
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    metadata["status"] = status
                    metadata["last_updated"] = datetime.datetime.now().isoformat()
                    
                    if additional_data:
                        for key, value in additional_data.items():
                            metadata[key] = value
                    
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                        
                    return True
                except Exception as e:
                    print(f"Error al actualizar metadatos del proyecto: {e}")
                    return False
        
        return True
    
    def get_project_metadata(self, project_id):
        """
        Obtiene los metadatos de un proyecto.
        
        Args:
            project_id (str): ID del proyecto
            
        Returns:
            dict: Metadatos del proyecto o None si no se encuentra
        """
        # Buscar el proyecto en el registro
        folder_name = None
        for project in self.registry["projects"]:
            if project["project_id"] == project_id:
                folder_name = project["folder_name"]
                break
        
        if folder_name:
            project_dir = os.path.join(self.projects_dir, folder_name)
            metadata_path = os.path.join(project_dir, "project_metadata.json")
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error al leer metadatos del proyecto: {e}")
                    return None
        
        print(f"Error: No se encontró el proyecto con ID {project_id}")
        return None
    
    def list_projects(self, status=None):
        """
        Lista los proyectos registrados, opcionalmente filtrados por estado.
        
        Args:
            status (str, optional): Estado por el cual filtrar
            
        Returns:
            list: Lista de proyectos que coinciden con el filtro
        """
        if status:
            return [p for p in self.registry["projects"] if p.get("status") == status]
        else:
            return self.registry["projects"]
    
    def _sanitize_filename(self, filename):
        """
        Sanitiza un nombre de archivo para que sea válido en el sistema de archivos.
        
        Args:
            filename (str): Nombre de archivo a sanitizar
            
        Returns:
            str: Nombre de archivo sanitizado
        """
        # Reemplazar caracteres inválidos
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Eliminar espacios al principio y al final
        sanitized = sanitized.strip()
        
        # Reemplazar espacios por guiones bajos
        sanitized = sanitized.replace(' ', '_')
        
        # Limitar longitud
        if len(sanitized) > 50:
            sanitized = sanitized[:47] + "..."
        
        return sanitized


# Ejemplo de uso:
if __name__ == "__main__":
    # Este código se ejecutará solo si se ejecuta este archivo directamente
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Crear un gestor de proyectos
    project_manager = SermonProjectManager(base_dir)
    
    # Crear un proyecto de ejemplo
    metadata = project_manager.create_project_structure(
        "ejemplo_sermon.mp4",
        "Sermón de Prueba - La Esperanza en Cristo"
    )
    
    # Imprimir información del proyecto
    print("\nProyectos registrados:")
    for project in project_manager.list_projects():
        print(f"- {project['sermon_title']} (ID: {project['project_id']}, Estado: {project['status']})")
