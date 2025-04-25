"""
File operations tools for the Model Context Protocol.
"""

import os
import shutil
import logging
import subprocess
import tempfile
import difflib
import re
from .mcp import MCP, tool
from .docker_utils import docker_manager

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
            # Normalize the file path to handle any path traversal attempts
            # Remove any leading slashes to ensure it's relative to the project root
            normalized_path = file_path.lstrip('/')

            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }

            # Check if the file already exists
            if os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {normalized_path} already exists."
                }

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write the file
            with open(full_path, 'w') as f:
                f.write(content)

            return {
                "status": "success",
                "message": f"File {normalized_path} created successfully.",
                "file_path": normalized_path
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
            # Normalize the file path to handle any path traversal attempts
            # Remove any leading slashes to ensure it's relative to the project root
            normalized_path = file_path.lstrip('/')

            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {normalized_path} does not exist."
                }

            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{normalized_path} is a directory, not a file."
                }

            # Write the file
            with open(full_path, 'w') as f:
                f.write(content)

            return {
                "status": "success",
                "message": f"File {normalized_path} updated successfully.",
                "file_path": normalized_path
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
            # Normalize the file path to handle any path traversal attempts
            # Remove any leading slashes to ensure it's relative to the project root
            normalized_path = file_path.lstrip('/')

            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {normalized_path} does not exist."
                }

            # Delete the file or directory
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
                message = f"Directory {normalized_path} deleted successfully."
            else:
                os.remove(full_path)
                message = f"File {normalized_path} deleted successfully."

            return {
                "status": "success",
                "message": message,
                "file_path": normalized_path
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
            # Normalize the file path to handle any path traversal attempts
            # Remove any leading slashes to ensure it's relative to the project root
            normalized_path = file_path.lstrip('/')

            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {normalized_path} does not exist."
                }

            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{normalized_path} is a directory, not a file."
                }

            # Read the file
            with open(full_path, 'r') as f:
                content = f.read()

            return {
                "status": "success",
                "message": f"File {normalized_path} read successfully.",
                "file_path": normalized_path,
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
            # Normalize the directory path to handle any path traversal attempts
            # Remove any leading slashes to ensure it's relative to the project root
            normalized_path = directory_path.lstrip('/')

            # Security check: make sure the directory is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid directory path. The directory must be within the project directory."
                }

            # Check if the directory exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"Directory {normalized_path} does not exist."
                }

            # Check if it's a directory
            if not os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{normalized_path} is a file, not a directory."
                }

            # List files and directories
            items = []
            for item in os.listdir(full_path):
                item_path = os.path.join(normalized_path, item)
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
                "message": f"Directory {normalized_path} listed successfully.",
                "directory_path": normalized_path,
                "items": items
            }

        except Exception as e:
            logger.exception(f"Error listing directory: {str(e)}")
            return {
                "status": "error",
                "message": f"Error listing directory: {str(e)}"
            }

    @tool(name="run_file", description="Run a file in the project's container")
    def run_file(self, file_path):
        """
        Run a file in the project's container.

        :param file_path: Path to the file to run relative to the project root
        """
        logger.info(f"Running file: {file_path}")

        try:
            # Normalize the file path to handle any path traversal attempts
            # Remove any leading slashes to ensure it's relative to the project root
            normalized_path = file_path.lstrip('/')

            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {normalized_path} does not exist."
                }

            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{normalized_path} is a directory, not a file."
                }

            # Check if the container is running
            container_status = docker_manager.get_container_status(self.project)
            if container_status != 'running':
                return {
                    "status": "error",
                    "message": f"Container is not running. Current status: {container_status}."
                }

            # Determine how to run the file based on its extension
            _, ext = os.path.splitext(normalized_path)
            ext = ext.lower()

            # Container path to the file
            container_file_path = f"/app/data/{normalized_path}"

            # Command to run based on file extension
            command = None
            if ext == '.py':
                command = f"python {container_file_path}"
            elif ext == '.js':
                command = f"node {container_file_path}"
            elif ext == '.sh':
                command = f"bash {container_file_path}"
            elif ext == '.php':
                command = f"php {container_file_path}"
            elif ext == '.rb':
                command = f"ruby {container_file_path}"
            elif ext == '.pl':
                command = f"perl {container_file_path}"
            elif ext == '.java':
                # For Java, we need to compile first
                java_class = os.path.basename(normalized_path).replace('.java', '')
                command = f"cd $(dirname {container_file_path}) && javac {os.path.basename(container_file_path)} && java {java_class}"
            elif ext == '.c':
                # For C, we need to compile first
                c_out = os.path.basename(normalized_path).replace('.c', '')
                command = f"cd $(dirname {container_file_path}) && gcc {os.path.basename(container_file_path)} -o {c_out} && ./{c_out}"
            elif ext == '.cpp':
                # For C++, we need to compile first
                cpp_out = os.path.basename(normalized_path).replace('.cpp', '')
                command = f"cd $(dirname {container_file_path}) && g++ {os.path.basename(container_file_path)} -o {cpp_out} && ./{cpp_out}"
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported file type: {ext}. Cannot determine how to run this file."
                }

            # Execute the command in the container
            container_id = self.project.container_id
            exec_command = ["docker", "exec", container_id, "bash", "-c", command]

            logger.info(f"Executing command in container: {' '.join(exec_command)}")

            # Run the command and capture output
            result = subprocess.run(
                exec_command,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            # Prepare the output
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode == 0:
                status = "success"
                if not stdout and not stderr:
                    message = f"File {normalized_path} executed successfully with no output."
                else:
                    message = f"File {normalized_path} executed successfully."
            else:
                status = "error"
                message = f"Error executing file {normalized_path}."

            return {
                "status": status,
                "message": message,
                "file_path": normalized_path,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": f"Execution timed out after 30 seconds.",
                "file_path": normalized_path,
                "command": command if 'command' in locals() else None
            }
        except Exception as e:
            logger.exception(f"Error running file: {str(e)}")
            return {
                "status": "error",
                "message": f"Error running file: {str(e)}",
                "file_path": normalized_path if 'normalized_path' in locals() else file_path
            }

    @tool(name="generate_diff", description="Generate a diff between original and new content")
    def generate_diff(self, original_content, new_content, file_path=None):
        """
        Generate a diff between original and new content.

        :param original_content: Original content string
        :param new_content: New content string
        :param file_path: Optional file path for context
        :return: Dict with diff result
        """
        logger.info(f"Generating diff for content" + (f" in file: {file_path}" if file_path else ""))

        try:
            # Split content into lines
            original_lines = original_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)

            # Generate unified diff
            diff = difflib.unified_diff(
                original_lines,
                new_lines,
                fromfile=f"original/{file_path}" if file_path else "original",
                tofile=f"new/{file_path}" if file_path else "new",
                n=3  # Context lines
            )

            # Convert diff iterator to string
            diff_text = ''.join(diff)

            # If there's no difference, return a message
            if not diff_text:
                return {
                    "status": "success",
                    "message": "No differences found between the contents.",
                    "file_path": file_path,
                    "diff": "",
                    "has_changes": False
                }

            return {
                "status": "success",
                "message": "Diff generated successfully.",
                "file_path": file_path,
                "diff": diff_text,
                "has_changes": True
            }

        except Exception as e:
            logger.exception(f"Error generating diff: {str(e)}")
            return {
                "status": "error",
                "message": f"Error generating diff: {str(e)}",
                "file_path": file_path
            }

    @tool(name="apply_patch", description="Apply a patch to a file")
    def apply_patch(self, file_path, patch_content):
        """
        Apply a patch to a file.

        :param file_path: Path to the file to patch
        :param patch_content: The patch content to apply
        :return: Dict with patching result
        """
        logger.info(f"Applying patch to file: {file_path}")

        try:
            # Normalize the file path
            normalized_path = file_path.lstrip('/')

            # Security check: make sure the file is within the project directory
            full_path = os.path.join(self.data_dir, normalized_path)
            if os.path.commonpath([full_path, self.data_dir]) != self.data_dir:
                return {
                    "status": "error",
                    "message": "Invalid file path. The file must be within the project directory."
                }

            # Check if the file exists
            if not os.path.exists(full_path):
                return {
                    "status": "error",
                    "message": f"File {normalized_path} does not exist."
                }

            # Check if it's a directory
            if os.path.isdir(full_path):
                return {
                    "status": "error",
                    "message": f"{normalized_path} is a directory, not a file."
                }

            # Read the current content of the file
            with open(full_path, 'r') as f:
                original_content = f.read()

            # Parse the patch to extract the changes
            # This is a simplified patch parser that handles unified diff format
            new_content = self._apply_unified_diff(original_content, patch_content)

            if new_content is None:
                return {
                    "status": "error",
                    "message": "Failed to apply patch. The patch format may be invalid or doesn't match the file."
                }

            # Write the patched content back to the file
            with open(full_path, 'w') as f:
                f.write(new_content)

            return {
                "status": "success",
                "message": f"Patch applied successfully to {normalized_path}.",
                "file_path": normalized_path,
                "original_content": original_content,
                "new_content": new_content
            }

        except Exception as e:
            logger.exception(f"Error applying patch: {str(e)}")
            return {
                "status": "error",
                "message": f"Error applying patch: {str(e)}",
                "file_path": file_path if 'file_path' in locals() else None
            }

    def _apply_unified_diff(self, original_content, patch_content):
        """
        Apply a unified diff to the original content.

        :param original_content: Original content string
        :param patch_content: Unified diff patch string
        :return: New content string or None if patch failed
        """
        try:
            # Split content into lines
            original_lines = original_content.splitlines()

            # Parse the patch
            current_line = 0
            new_lines = original_lines.copy()

            # Extract hunks from the patch
            hunks = []
            current_hunk = None

            for line in patch_content.splitlines():
                # Skip the header lines (starting with ---, +++ or @@)
                if line.startswith('---') or line.startswith('+++'):
                    continue

                # Start of a new hunk
                if line.startswith('@@'):
                    # Parse the hunk header to get line numbers
                    # Format: @@ -start,count +start,count @@
                    match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                    if not match:
                        continue

                    old_start = int(match.group(1))
                    old_count = int(match.group(2) or 1)
                    new_start = int(match.group(3))
                    new_count = int(match.group(4) or 1)

                    current_hunk = {
                        'old_start': old_start - 1,  # 0-based indexing
                        'old_count': old_count,
                        'new_start': new_start - 1,  # 0-based indexing
                        'new_count': new_count,
                        'lines': []
                    }
                    hunks.append(current_hunk)
                    continue

                # Add lines to the current hunk
                if current_hunk is not None:
                    current_hunk['lines'].append(line)

            # Apply hunks in reverse order to avoid line number changes
            for hunk in reversed(hunks):
                old_start = hunk['old_start']
                old_count = hunk['old_count']
                lines = hunk['lines']

                # Verify that the context lines match
                context_match = True
                old_index = old_start

                for line in lines:
                    if line.startswith(' '):  # Context line
                        if old_index >= len(original_lines) or original_lines[old_index] != line[1:]:
                            context_match = False
                            break
                        old_index += 1
                    elif line.startswith('-'):  # Removal line
                        if old_index >= len(original_lines) or original_lines[old_index] != line[1:]:
                            context_match = False
                            break
                        old_index += 1
                    # Skip addition lines for context matching

                if not context_match:
                    logger.warning("Patch context doesn't match the file content")
                    continue

                # Apply the hunk
                new_hunk_lines = []
                for line in lines:
                    if line.startswith('+'):  # Addition
                        new_hunk_lines.append(line[1:])
                    elif line.startswith(' '):  # Context
                        new_hunk_lines.append(line[1:])
                    # Skip removal lines

                # Replace the old lines with the new lines
                new_lines[old_start:old_start + old_count] = new_hunk_lines

            # Join the lines back into a string
            return '\n'.join(new_lines)

        except Exception as e:
            logger.exception(f"Error applying unified diff: {str(e)}")
            return None
