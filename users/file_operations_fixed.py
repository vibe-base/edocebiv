"""
File Operations OpenAI MCP Implementation.
This module provides file operation tools for the OpenAI API.
"""

import os
import shutil
import logging
from .openai_mcp_fixed import OpenAIMCP, register_tool

logger = logging.getLogger(__name__)

class FileOperationsMCP(OpenAIMCP):
    """File Operations OpenAI MCP Implementation."""
    
    def __init__(self, project, user):
        """Initialize with project and user."""
        self.project = project
        self.user = user
        self.data_dir = project.get_data_directory()
        super().__init__()  # Call parent init after setting up instance variables
    
    @register_tool(name="create_file", description="Create a new file in the project.")
    def create_file(self, file_path, content=""):
        """
        Create a new file in the project.
        
        :param file_path: Path to the file relative to the project root.
        :param content: Content for the new file.
        :return: Result of the operation.
        """
        logger.info(f"Creating file: {file_path} in project directory: {self.data_dir}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            logger.info(f"Full path for new file: {full_path}")
            
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                logger.error(f"Security check failed: {full_path} is outside project directory {self.data_dir}")
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }
            
            # Check if the file already exists
            if os.path.exists(full_path):
                logger.warning(f"File already exists: {full_path}")
                return {
                    'status': 'error',
                    'message': f'File {file_path} already exists.'
                }
            
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(full_path)
            logger.info(f"Creating directory if needed: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
            
            # Write the file
            logger.info(f"Writing content to file: {full_path}")
            with open(full_path, 'w') as f:
                f.write(content)
            
            # Verify the file was created
            if os.path.exists(full_path):
                logger.info(f"File created successfully: {full_path}")
                return {
                    'status': 'success',
                    'message': f'File {file_path} created successfully.',
                    'file_path': file_path
                }
            else:
                logger.error(f"File creation verification failed: {full_path} does not exist after write operation")
                return {
                    'status': 'error',
                    'message': f'File {file_path} could not be verified after creation.'
                }
        
        except Exception as e:
            logger.exception(f"Error creating file {file_path}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error creating file: {str(e)}'
            }
    
    @register_tool(name="update_file", description="Update the content of an existing file.")
    def update_file(self, file_path, content):
        """
        Update the content of an existing file.
        
        :param file_path: Path to the file relative to the project root.
        :param content: New content for the file.
        :return: Result of the operation.
        """
        logger.info(f"Updating file: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                logger.error(f"Security check failed: {full_path} is outside project directory {self.data_dir}")
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.warning(f"File does not exist: {full_path}")
                return {
                    'status': 'error',
                    'message': f'File {file_path} does not exist.'
                }
            
            # Check if it's a directory
            if os.path.isdir(full_path):
                logger.warning(f"Path is a directory, not a file: {full_path}")
                return {
                    'status': 'error',
                    'message': f'{file_path} is a directory, not a file.'
                }
            
            # Write the file
            logger.info(f"Writing content to file: {full_path}")
            with open(full_path, 'w') as f:
                f.write(content)
            
            return {
                'status': 'success',
                'message': f'File {file_path} updated successfully.',
                'file_path': file_path
            }
        
        except Exception as e:
            logger.exception(f"Error updating file {file_path}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error updating file: {str(e)}'
            }
    
    @register_tool(name="delete_file", description="Delete a file or directory.")
    def delete_file(self, file_path):
        """
        Delete a file or directory.
        
        :param file_path: Path to the file or directory relative to the project root.
        :return: Result of the operation.
        """
        logger.info(f"Deleting file or directory: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                logger.error(f"Security check failed: {full_path} is outside project directory {self.data_dir}")
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.warning(f"File does not exist: {full_path}")
                return {
                    'status': 'error',
                    'message': f'File {file_path} does not exist.'
                }
            
            # Delete the file or directory
            if os.path.isdir(full_path):
                logger.info(f"Deleting directory: {full_path}")
                shutil.rmtree(full_path)
                message = f'Directory {file_path} deleted successfully.'
            else:
                logger.info(f"Deleting file: {full_path}")
                os.remove(full_path)
                message = f'File {file_path} deleted successfully.'
            
            return {
                'status': 'success',
                'message': message,
                'file_path': file_path
            }
        
        except Exception as e:
            logger.exception(f"Error deleting {file_path}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error deleting file: {str(e)}'
            }
    
    @register_tool(name="read_file", description="Read the content of a file.")
    def read_file(self, file_path):
        """
        Read the content of a file.
        
        :param file_path: Path to the file relative to the project root.
        :return: Result of the operation with file content.
        """
        logger.info(f"Reading file: {file_path}")
        
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                logger.error(f"Security check failed: {full_path} is outside project directory {self.data_dir}")
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.warning(f"File does not exist: {full_path}")
                return {
                    'status': 'error',
                    'message': f'File {file_path} does not exist.'
                }
            
            # Check if it's a directory
            if os.path.isdir(full_path):
                logger.warning(f"Path is a directory, not a file: {full_path}")
                return {
                    'status': 'error',
                    'message': f'{file_path} is a directory, not a file.'
                }
            
            # Read the file
            logger.info(f"Reading content from file: {full_path}")
            with open(full_path, 'r') as f:
                content = f.read()
            
            return {
                'status': 'success',
                'message': f'File {file_path} read successfully.',
                'file_path': file_path,
                'content': content
            }
        
        except Exception as e:
            logger.exception(f"Error reading file {file_path}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error reading file: {str(e)}'
            }
    
    @register_tool(name="list_files", description="List files and directories in a directory.")
    def list_files(self, directory_path=""):
        """
        List files and directories in a directory.
        
        :param directory_path: Path to the directory relative to the project root. Defaults to project root.
        :return: Result of the operation with file list.
        """
        logger.info(f"Listing files in directory: {directory_path}")
        
        try:
            # Security check: make sure the directory is within the project directory
            full_path = os.path.join(self.data_dir, directory_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                logger.error(f"Security check failed: {full_path} is outside project directory {self.data_dir}")
                return {
                    'status': 'error',
                    'message': 'Invalid directory path. The directory must be within the project directory.'
                }
            
            # Check if the directory exists
            if not os.path.exists(full_path):
                logger.warning(f"Directory does not exist: {full_path}")
                return {
                    'status': 'error',
                    'message': f'Directory {directory_path} does not exist.'
                }
            
            # Check if it's a directory
            if not os.path.isdir(full_path):
                logger.warning(f"Path is a file, not a directory: {full_path}")
                return {
                    'status': 'error',
                    'message': f'{directory_path} is a file, not a directory.'
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
                    'name': item,
                    'path': item_path,
                    'is_dir': is_dir
                })
            
            # Sort items: directories first, then files, both alphabetically
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return {
                'status': 'success',
                'message': f'Directory {directory_path} listed successfully.',
                'directory_path': directory_path,
                'items': items
            }
        
        except Exception as e:
            logger.exception(f"Error listing directory {directory_path}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error listing directory: {str(e)}'
            }
