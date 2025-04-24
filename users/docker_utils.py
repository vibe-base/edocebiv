import docker
import logging
import os
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

class DockerManager:
    """Utility class to manage Docker containers for projects."""
    
    def __init__(self):
        """Initialize the Docker client."""
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            self.client = None
    
    def is_available(self):
        """Check if Docker is available."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    def create_container(self, project):
        """Create a Docker container for the project."""
        if not self.is_available():
            logger.error("Docker is not available")
            return False
        
        try:
            # Get the project's data directory
            data_dir = project.get_data_directory()
            
            # Create a container with the project's data directory mounted
            container = self.client.containers.create(
                image=project.container_image,
                name=f"project_{project.id}_{project.title.lower().replace(' ', '_')}",
                command="tail -f /dev/null",  # Keep container running
                detach=True,
                volumes={
                    data_dir: {
                        'bind': '/app/data',
                        'mode': 'rw'
                    }
                },
                working_dir="/app",
                environment={
                    "PROJECT_ID": str(project.id),
                    "PROJECT_TITLE": project.title
                }
            )
            
            # Update the project with container information
            project.container_id = container.id
            project.container_status = "created"
            project.container_created_at = timezone.now()
            project.save()
            
            logger.info(f"Container created for project {project.id}: {container.id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create container for project {project.id}: {str(e)}")
            return False
    
    def start_container(self, project):
        """Start the Docker container for the project."""
        if not self.is_available() or not project.container_id:
            return False
        
        try:
            container = self.client.containers.get(project.container_id)
            container.start()
            
            # Update the project's container status
            project.container_status = "running"
            project.save()
            
            logger.info(f"Container started for project {project.id}: {project.container_id}")
            return True
        
        except docker.errors.NotFound:
            logger.error(f"Container not found for project {project.id}: {project.container_id}")
            project.container_id = None
            project.container_status = None
            project.save()
            return False
        
        except Exception as e:
            logger.error(f"Failed to start container for project {project.id}: {str(e)}")
            return False
    
    def stop_container(self, project):
        """Stop the Docker container for the project."""
        if not self.is_available() or not project.container_id:
            return False
        
        try:
            container = self.client.containers.get(project.container_id)
            container.stop()
            
            # Update the project's container status
            project.container_status = "stopped"
            project.save()
            
            logger.info(f"Container stopped for project {project.id}: {project.container_id}")
            return True
        
        except docker.errors.NotFound:
            logger.error(f"Container not found for project {project.id}: {project.container_id}")
            project.container_id = None
            project.container_status = None
            project.save()
            return False
        
        except Exception as e:
            logger.error(f"Failed to stop container for project {project.id}: {str(e)}")
            return False
    
    def remove_container(self, project):
        """Remove the Docker container for the project."""
        if not self.is_available() or not project.container_id:
            return False
        
        try:
            container = self.client.containers.get(project.container_id)
            
            # Stop the container if it's running
            if container.status == "running":
                container.stop()
            
            # Remove the container
            container.remove()
            
            # Update the project
            project.container_id = None
            project.container_status = None
            project.container_created_at = None
            project.save()
            
            logger.info(f"Container removed for project {project.id}")
            return True
        
        except docker.errors.NotFound:
            logger.error(f"Container not found for project {project.id}: {project.container_id}")
            project.container_id = None
            project.container_status = None
            project.save()
            return True  # Return True since the container is already gone
        
        except Exception as e:
            logger.error(f"Failed to remove container for project {project.id}: {str(e)}")
            return False
    
    def get_container_status(self, project):
        """Get the current status of the project's container."""
        if not self.is_available() or not project.container_id:
            return None
        
        try:
            container = self.client.containers.get(project.container_id)
            status = container.status
            
            # Update the project's container status if it's different
            if project.container_status != status:
                project.container_status = status
                project.save()
            
            return status
        
        except docker.errors.NotFound:
            logger.error(f"Container not found for project {project.id}: {project.container_id}")
            project.container_id = None
            project.container_status = None
            project.save()
            return None
        
        except Exception as e:
            logger.error(f"Failed to get container status for project {project.id}: {str(e)}")
            return None

# Create a singleton instance
docker_manager = DockerManager()
