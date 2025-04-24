"""
File operations tools for the Model Context Protocol.
"""

import os
import shutil
import logging
from .mcp import MCP, tool

logger = logging.getLogger(__name__)

class FileOperations(MCP):
    """File operations tools for the Model Context Protocol."""
    
    def __init__(self, project, user):
        """Initialize with project and user."""
        self.project = project
        self.user = user
        self.data_dir = project.get_data_directory()
        super().__init__()
    
    @tool(name="create_file", description="Create a new file in the project")
    def create_file(self, file_path, content=""):
        """
        Create a new file in the project.
        
        :param file_path: Path to the file relative to the project root
        :param content: Content for the new file
        """
        logger.info(f"Creating file: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }
            
            # Check if the file already exists
            if os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {file_path} already exists."
                }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write the file
            with open(full_path, 'w') as f:
                f.write(content)
            
            return {
                "status": "success",
                "message": f"File {file_path} created successfully.",
                "file_path": file_path
            }
        
        except Exception as e:
            logger.exception(f"Error creating file: {str(e)}")
            return {
                "status": "error",
                "message": f"Error creating file: {str(e)}"
            }
    
    @tool(name="update_file", description="Update the content of an existing file")
    def update_file(self, file_path, content):
        """
        Update the content of an existing file.
        
        :param file_path: Path to the file relative to the project root
        :param content: New content for the file
        """
        logger.info(f"Updating file: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }
            
            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {file_path} does not exist."
                }
            
            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{file_path} is a directory, not a file."
                }
            
            # Write the file
            with open(full_path, 'w') as f:
                f.write(content)
            
            return {
                "status": "success",
                "message": f"File {file_path} updated successfully.",
                "file_path": file_path
            }
        
        except Exception as e:
            logger.exception(f"Error updating file: {str(e)}")
            return {
                "status": "error",
                "message": f"Error updating file: {str(e)}"
            }
    
    @tool(name="delete_file", description="Delete a file or directory")
    def delete_file(self, file_path):
        """
        Delete a file or directory.
        
        :param file_path: Path to the file or directory relative to the project root
        """
        logger.info(f"Deleting file or directory: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }
            
            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {file_path} does not exist."
                }
            
            # Delete the file or directory
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
                message = f"Directory {file_path} deleted successfully."
            else:
                os.remove(full_path)
                message = f"File {file_path} deleted successfully."
            
            return {
                "status": "success",
                "message": message,
                "file_path": file_path
            }
        
        except Exception as e:
            logger.exception(f"Error deleting file: {str(e)}")
            return {
                "status": "error",
                "message": f"Error deleting file: {str(e)}"
            }
    
    @tool(name="read_file", description="Read the content of a file")
    def read_file(self, file_path):
        """
        Read the content of a file.
        
        :param file_path: Path to the file relative to the project root
        """
        logger.info(f"Reading file: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }
            
            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {file_path} does not exist."
                }
            
            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{file_path} is a directory, not a file."
                }
            
            # Read the file
            with open(full_path, 'r') as f:
                content = f.read()
            
            return {
                "status": "success",
                "message": f"File {file_path} read successfully.",
                "file_path": file_path,
                "content": content
            }
        
        except Exception as e:
            logger.exception(f"Error reading file: {str(e)}")
            return {
                "status": "error",
                "message": f"Error reading file: {str(e)}"
            }
    
    @tool(name="list_files", description="List files and directories in a directory")
    def list_files(self, directory_path=""):
        """
        List files and directories in a directory.
        
        :param directory_path: Path to the directory relative to the project root (defaults to project root)
        """
        logger.info(f"Listing files in directory: {directory_path}")
        
        try:
            # Security check: make sure the directory is within the project directory
            full_path = os.path.join(self.data_dir, directory_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid directory path. The directory must be within the project directory."
                }
            
            # Check if the directory exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"Directory {directory_path} does not exist."
                }
            
            # Check if it's a directory
            if not os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{directory_path} is a file, not a directory."
                }
            
            # List files and directories
            items = []
            for item in os.listdir(full_path):
                item_path = os.path.join(directory_path, item)
                item_full_path = os.path.join(self.data_dir, item_path)
                
                # Skip hidden files
                if item.startswith('.'):
                    continue
                
                is_dir = os.path.isdir(item_full_path)
                
                items.append({
                    "name": item,
                    "path": item_path,
                    "is_dir": is_dir
                })
            
            # Sort items: directories first, then files, both alphabetically
            items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return {
                "status": "success",
                "message": f"Directory {directory_path} listed successfully.",
                "directory_path": directory_path,
                "items": items
            }
        
        except Exception as e:
            logger.exception(f"Error listing directory: {str(e)}")
            return {
                "status": "error",
                "message": f"Error listing directory: {str(e)}"
            }
