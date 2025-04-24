"""
AI Protocol for interacting with the codebase.
This module provides tools for the AI assistant to interact with the codebase.
"""

import os
import re
import json
import logging
from django.shortcuts import get_object_or_404
from .models import Project

logger = logging.getLogger(__name__)

class AIProtocol:
    """Protocol for AI to interact with the codebase."""

    def __init__(self, project, user):
        """Initialize the protocol with a project and user."""
        self.project = project
        self.user = user
        self.data_dir = project.get_data_directory()

    def update_file(self, file_path, content):
        """Update the content of a file.

        Args:
            file_path (str): Path to the file relative to the project root.
            content (str): New content for the file.

        Returns:
            dict: Result of the operation.
        """
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write the file
            with open(full_path, 'w') as f:
                f.write(content)

            return {
                'status': 'success',
                'message': f'File {file_path} updated successfully.',
                'file_path': file_path
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error updating file: {str(e)}'
            }

    def create_file(self, file_path, content=""):
        """Create a new file.

        Args:
            file_path (str): Path to the file relative to the project root.
            content (str, optional): Content for the new file. Defaults to "".

        Returns:
            dict: Result of the operation.
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

    def delete_file(self, file_path):
        """Delete a file.

        Args:
            file_path (str): Path to the file relative to the project root.

        Returns:
            dict: Result of the operation.
        """
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    'status': 'error',
                    'message': f'File {file_path} does not exist.'
                }

            # Delete the file
            if os.path.isdir(full_path):
                import shutil
                shutil.rmtree(full_path)
                message = f'Directory {file_path} deleted successfully.'
            else:
                os.remove(full_path)
                message = f'File {file_path} deleted successfully.'

            return {
                'status': 'success',
                'message': message,
                'file_path': file_path
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error deleting file: {str(e)}'
            }

    def read_file(self, file_path):
        """Read the content of a file.

        Args:
            file_path (str): Path to the file relative to the project root.

        Returns:
            dict: Result of the operation with file content.
        """
        try:
            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    'status': 'error',
                    'message': 'Invalid file path. The file must be within the project directory.'
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    'status': 'error',
                    'message': f'File {file_path} does not exist.'
                }

            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    'status': 'error',
                    'message': f'{file_path} is a directory, not a file.'
                }

            # Read the file
            with open(full_path, 'r') as f:
                content = f.read()

            return {
                'status': 'success',
                'message': f'File {file_path} read successfully.',
                'file_path': file_path,
                'content': content
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error reading file: {str(e)}'
            }

    def list_files(self, directory_path=""):
        """List files in a directory.

        Args:
            directory_path (str, optional): Path to the directory relative to the project root. Defaults to "".

        Returns:
            dict: Result of the operation with file list.
        """
        try:
            # Security check: make sure the directory is within the project directory
            full_path = os.path.join(self.data_dir, directory_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    'status': 'error',
                    'message': 'Invalid directory path. The directory must be within the project directory.'
                }

            # Check if the directory exists
            if not os.path.exists(full_path):
                return {
                    'status': 'error',
                    'message': f'Directory {directory_path} does not exist.'
                }

            # Check if it's a directory
            if not os.path.isdir(full_path):
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
            return {
                'status': 'error',
                'message': f'Error listing directory: {str(e)}'
            }

    @staticmethod
    def parse_tools_from_message(message):
        """Parse tool calls from an AI message.

        Args:
            message (str): The AI message to parse.

        Returns:
            list: List of tool calls.
        """
        # Regular expression to match tool calls
        tool_pattern = r'```tool\s+([\s\S]*?)```'

        # Find all tool calls in the message
        tool_matches = re.findall(tool_pattern, message)

        tool_calls = []
        for tool_match in tool_matches:
            try:
                # Parse the tool call as JSON
                tool_call = json.loads(tool_match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                # If the tool call is not valid JSON, skip it
                continue

        return tool_calls

    def execute_tool(self, tool_call):
        """Execute a tool call.

        Args:
            tool_call (dict): The tool call to execute.

        Returns:
            dict: Result of the tool execution.
        """
        tool_name = tool_call.get('name')
        arguments = tool_call.get('arguments', {})

        # Map tool names to methods
        tools = {
            'update_file': self.update_file,
            'create_file': self.create_file,
            'delete_file': self.delete_file,
            'read_file': self.read_file,
            'list_files': self.list_files
        }

        # Check if the tool exists
        if tool_name not in tools:
            return {
                'status': 'error',
                'message': f'Unknown tool: {tool_name}'
            }

        # Execute the tool
        tool_method = tools[tool_name]
        return tool_method(**arguments)

    def process_message(self, message):
        """Process an AI message and execute any tool calls.

        Args:
            message (str): The AI message to process.

        Returns:
            tuple: (processed_message, tool_results)
        """
        # Parse tool calls from the message
        tool_calls = self.parse_tools_from_message(message)

        # If there are no tool calls, return the original message
        if not tool_calls:
            return message, []

        # Execute each tool call
        tool_results = []
        for tool_call in tool_calls:
            result = self.execute_tool(tool_call)
            tool_results.append({
                'tool': tool_call.get('name'),
                'arguments': tool_call.get('arguments', {}),
                'result': result
            })

        # Replace tool calls with their results in the message
        processed_message = message
        for i, tool_match in enumerate(re.finditer(r'```tool\s+([\s\S]*?)```', message)):
            if i < len(tool_results):
                result = tool_results[i]['result']
                tool_name = tool_results[i]['tool']
                status = result['status']
                result_message = result['message']

                # Create a more detailed replacement with tool name and status
                replacement = f'<div class="chat-tool-result {status}" data-tool-type="{tool_name}">\n'
                replacement += f"# Tool Result: {status.upper()}\n"
                replacement += f"# Tool: {tool_name}\n\n"
                replacement += f"{result_message}\n"

                # Add file path if available
                if 'file_path' in result:
                    replacement += f"\nFile: {result['file_path']}"

                replacement += "</div>"

                processed_message = processed_message.replace(tool_match.group(0), replacement, 1)

        # Log the tool results for debugging
        import logging
        logger = logging.getLogger(__name__)
        if tool_results:
            logger.info(f"Executed {len(tool_results)} tool calls: {[r['tool'] for r in tool_results]}")

        return processed_message, tool_results
