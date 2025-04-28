from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import TemplateView
import os
import shutil
import json
import logging
import requests
from .models import Project, UserProfile, ChatMessage
from .forms import ProjectForm, UserProfileForm
from .docker_utils import docker_manager

def test_view(request):
    """Simple test view to verify template rendering."""
    return render(request, 'users/test.html')

logger = logging.getLogger(__name__)

@login_required
def project_list(request):
    """View to display all projects for the logged-in user."""
    projects = Project.objects.filter(user=request.user)
    return render(request, 'users/project_list.html', {'projects': projects})

@login_required
def project_create(request):
    """View to create a new project."""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, 'Project created successfully!')
            return redirect('project_list')
    else:
        form = ProjectForm()

    return render(request, 'users/project_form.html', {
        'form': form,
        'title': 'Create Project'
    })

@login_required
def project_update(request, pk):
    """View to update an existing project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully!')
            return redirect('project_list')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'users/project_form.html', {
        'form': form,
        'project': project,
        'title': 'Edit Project'
    })

@login_required
def project_delete(request, pk):
    """View to delete a project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully!')
        return redirect('project_list')

    return render(request, 'users/project_confirm_delete.html', {'project': project})

@login_required
def project_detail(request, pk):
    """View to display details of a specific project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    # Check if Docker is available
    docker_available = docker_manager.is_available()

    # If the project has a container, get its current status
    if project.container_id and docker_available:
        current_status = docker_manager.get_container_status(project)
    else:
        current_status = None

    return render(request, 'users/project_detail.html', {
        'project': project,
        'docker_available': docker_available,
        'current_status': current_status
    })

@login_required
def profile_view(request):
    """View to display and update user profile."""
    profile = request.user.profile

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile_view')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'users/profile.html', {
        'form': form,
        'profile': profile
    })

@login_required
@require_POST
def save_preferences(request):
    """AJAX endpoint to save user preferences."""
    profile = request.user.profile

    # Get preferences from POST data
    is_assistant_window_open = request.POST.get('is_assistant_window_open') == 'true'
    is_reasoning_mode_on = request.POST.get('is_reasoning_mode_on') == 'true'

    # Get panel states if provided
    chat_panel_width = request.POST.get('chat_panel_width')
    terminal_height = request.POST.get('terminal_height')

    # Update profile
    profile.is_assistant_window_open = is_assistant_window_open
    profile.is_reasoning_mode_on = is_reasoning_mode_on

    # Update panel states if provided
    if chat_panel_width and chat_panel_width.isdigit():
        profile.chat_panel_width = int(chat_panel_width)

    if terminal_height and terminal_height.isdigit():
        profile.terminal_height = int(terminal_height)

    profile.save()

    return JsonResponse({
        'status': 'success',
        'message': 'Preferences saved successfully',
        'is_assistant_window_open': profile.is_assistant_window_open,
        'is_reasoning_mode_on': profile.is_reasoning_mode_on,
        'chat_panel_width': profile.chat_panel_width,
        'terminal_height': profile.terminal_height
    })

# Docker Container Management Views

@login_required
def container_create(request, pk):
    """Create a Docker container for the project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        # Check if Docker is available
        if not docker_manager.is_available():
            messages.error(request, 'Docker is not available. Please make sure Docker is running.')
            return redirect('project_detail', pk=project.pk)

        # Check if the project already has a container
        if project.container_id:
            messages.warning(request, 'This project already has a container.')
            return redirect('project_detail', pk=project.pk)

        # Create the container
        success = docker_manager.create_container(project)

        if success:
            messages.success(request, 'Container created successfully!')
        else:
            # Provide a more detailed error message
            messages.error(request,
                'Failed to create container. This could be due to the Docker image not being available '
                'or insufficient permissions. Please check that Docker is running properly and try again.'
            )

    return redirect('project_detail', pk=project.pk)

@login_required
def container_start(request, pk):
    """Start the Docker container for the project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        # Check if Docker is available
        if not docker_manager.is_available():
            messages.error(request, 'Docker is not available. Please make sure Docker is running.')
            return redirect('project_detail', pk=project.pk)

        # Check if the project has a container
        if not project.container_id:
            messages.warning(request, 'This project does not have a container.')
            return redirect('project_detail', pk=project.pk)

        # Start the container
        success = docker_manager.start_container(project)

        if success:
            messages.success(request, 'Container started successfully!')
        else:
            messages.error(request, 'Failed to start container. Please check the logs.')

    return redirect('project_detail', pk=project.pk)

@login_required
def container_stop(request, pk):
    """Stop the Docker container for the project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        # Check if Docker is available
        if not docker_manager.is_available():
            messages.error(request, 'Docker is not available. Please make sure Docker is running.')
            return redirect('project_detail', pk=project.pk)

        # Check if the project has a container
        if not project.container_id:
            messages.warning(request, 'This project does not have a container.')
            return redirect('project_detail', pk=project.pk)

        # Stop the container
        success = docker_manager.stop_container(project)

        if success:
            messages.success(request, 'Container stopped successfully!')
        else:
            messages.error(request, 'Failed to stop container. Please check the logs.')

    return redirect('project_detail', pk=project.pk)

@login_required
def container_remove(request, pk):
    """Remove the Docker container for the project."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        # Check if Docker is available
        if not docker_manager.is_available():
            messages.error(request, 'Docker is not available. Please make sure Docker is running.')
            return redirect('project_detail', pk=project.pk)

        # Check if the project has a container
        if not project.container_id:
            messages.warning(request, 'This project does not have a container.')
            return redirect('project_detail', pk=project.pk)

        # Remove the container
        success = docker_manager.remove_container(project)

        if success:
            messages.success(request, 'Container removed successfully!')
        else:
            messages.error(request, 'Failed to remove container. Please check the logs.')

    return redirect('project_detail', pk=project.pk)

@login_required
def container_status(request, pk):
    """Get the current status of the project's container."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    # Check if Docker is available
    if not docker_manager.is_available():
        return JsonResponse({'status': 'error', 'message': 'Docker is not available'})

    # Check if the project has a container
    if not project.container_id:
        return JsonResponse({'status': 'error', 'message': 'No container for this project'})

    # Get the container status
    status = docker_manager.get_container_status(project)

    if status is None:
        return JsonResponse({'status': 'error', 'message': 'Failed to get container status'})

    return JsonResponse({'status': 'success', 'container_status': status})

@login_required
def code_editor(request, pk):
    """View for the code editor interface that resembles Visual Studio Code."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    # Get the user profile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Get the project's data directory
    data_dir = project.get_data_directory()

    # Get the list of files in the data directory
    import os

    # Function to recursively get all files and directories
    def get_directory_structure(root_path, relative_path=""):
        items = []
        full_path = os.path.join(root_path, relative_path)

        try:
            for item in os.listdir(full_path):
                item_relative_path = os.path.join(relative_path, item)
                item_full_path = os.path.join(root_path, item_relative_path)

                is_dir = os.path.isdir(item_full_path)

                # Skip hidden files and directories
                if item.startswith('.'):
                    continue

                if is_dir:
                    children = get_directory_structure(root_path, item_relative_path)
                    items.append({
                        'name': item,
                        'path': item_relative_path,
                        'is_dir': True,
                        'children': children
                    })
                else:
                    # Get file size
                    size = os.path.getsize(item_full_path)
                    # Format size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"

                    # Get file extension
                    _, ext = os.path.splitext(item)
                    ext = ext.lstrip('.')

                    items.append({
                        'name': item,
                        'path': item_relative_path,
                        'is_dir': False,
                        'size': size_str,
                        'extension': ext
                    })
        except FileNotFoundError:
            # If the directory doesn't exist yet, create it
            os.makedirs(full_path, exist_ok=True)
        except PermissionError:
            # Handle permission errors
            pass

        # Sort items: directories first, then files, both alphabetically
        return sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))

    # Get the directory structure
    directory_structure = get_directory_structure(data_dir)

    # Check if a file is being viewed
    file_path = request.GET.get('file')
    file_content = None
    current_file = None

    if file_path:
        try:
            full_file_path = os.path.join(data_dir, file_path)
            # Make sure the file is within the project directory (security check)
            if os.path.commonpath([full_file_path, data_dir]) == data_dir:
                with open(full_file_path, 'r') as f:
                    file_content = f.read()
                current_file = {
                    'name': os.path.basename(file_path),
                    'path': file_path,
                    'extension': os.path.splitext(file_path)[1].lstrip('.')
                }
        except (FileNotFoundError, PermissionError, IsADirectoryError, UnicodeDecodeError):
            file_content = None

    # Check if Docker is available and the container is running
    docker_available = docker_manager.is_available()
    container_running = False
    web_server_port = None

    if docker_available and project.container_id:
        container_status = docker_manager.get_container_status(project)
        container_running = container_status == 'running'

        # Get the web server port if the container is running
        if container_running and project.web_server_port:
            web_server_port = project.web_server_port

    return render(request, 'users/code_editor.html', {
        'project': project,
        'directory_structure': directory_structure,
        'file_content': file_content,
        'current_file': current_file,
        'docker_available': docker_available,
        'container_running': container_running,
        'web_server_port': web_server_port,
        'data_dir': data_dir,
        'user_profile': user_profile
    })

@login_required
def file_save(request, pk):
    """Save a file in the project's data directory."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    project = get_object_or_404(Project, pk=pk, user=request.user)
    data_dir = project.get_data_directory()

    try:
        file_path = request.POST.get('file_path')
        file_content = request.POST.get('file_content')

        if not file_path:
            return JsonResponse({'status': 'error', 'message': 'File path is required'}, status=400)

        # Security check: make sure the file is within the project directory
        full_file_path = os.path.join(data_dir, file_path)
        if os.path.commonpath([full_file_path, data_dir]) != data_dir:
            return JsonResponse({'status': 'error', 'message': 'Invalid file path'}, status=403)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)

        # Write the file
        with open(full_file_path, 'w') as f:
            f.write(file_content or '')

        return JsonResponse({'status': 'success', 'message': 'File saved successfully'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def file_create(request, pk):
    """Create a new file or directory in the project's data directory."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    project = get_object_or_404(Project, pk=pk, user=request.user)
    data_dir = project.get_data_directory()

    try:
        parent_path = request.POST.get('parent_path', '')
        name = request.POST.get('name')
        is_directory = request.POST.get('is_directory') == 'true'

        if not name:
            return JsonResponse({'status': 'error', 'message': 'Name is required'}, status=400)

        # Create the full path
        relative_path = os.path.join(parent_path, name) if parent_path else name
        full_path = os.path.join(data_dir, relative_path)

        # Security check: make sure the file is within the project directory
        if os.path.commonpath([full_path, data_dir]) != data_dir:
            return JsonResponse({'status': 'error', 'message': 'Invalid path'}, status=403)

        # Check if the file/directory already exists
        if os.path.exists(full_path):
            return JsonResponse({'status': 'error', 'message': 'File or directory already exists'}, status=400)

        if is_directory:
            # Create directory
            os.makedirs(full_path, exist_ok=True)
        else:
            # Create file
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write('')

        return JsonResponse({
            'status': 'success',
            'message': f"{'Directory' if is_directory else 'File'} created successfully",
            'item': {
                'name': name,
                'path': relative_path,
                'is_dir': is_directory,
                'size': '0 B' if not is_directory else None,
                'extension': os.path.splitext(name)[1].lstrip('.') if not is_directory else None,
                'children': [] if is_directory else None
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def file_delete(request, pk):
    """Delete a file or directory in the project's data directory."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    project = get_object_or_404(Project, pk=pk, user=request.user)
    data_dir = project.get_data_directory()

    try:
        file_path = request.POST.get('file_path')

        if not file_path:
            return JsonResponse({'status': 'error', 'message': 'File path is required'}, status=400)

        # Security check: make sure the file is within the project directory
        full_path = os.path.join(data_dir, file_path)
        if os.path.commonpath([full_path, data_dir]) != data_dir:
            return JsonResponse({'status': 'error', 'message': 'Invalid file path'}, status=403)

        # Check if the file/directory exists
        if not os.path.exists(full_path):
            return JsonResponse({'status': 'error', 'message': 'File or directory does not exist'}, status=404)

        import shutil

        if os.path.isdir(full_path):
            # Delete directory
            shutil.rmtree(full_path)
        else:
            # Delete file
            os.remove(full_path)

        return JsonResponse({'status': 'success', 'message': 'File or directory deleted successfully'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def file_rename(request, pk):
    """Rename a file or directory in the project's data directory."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    project = get_object_or_404(Project, pk=pk, user=request.user)
    data_dir = project.get_data_directory()

    try:
        file_path = request.POST.get('file_path')
        new_name = request.POST.get('new_name')

        if not file_path or not new_name:
            return JsonResponse({'status': 'error', 'message': 'File path and new name are required'}, status=400)

        # Security check: make sure the file is within the project directory
        full_path = os.path.join(data_dir, file_path)
        if os.path.commonpath([full_path, data_dir]) != data_dir:
            return JsonResponse({'status': 'error', 'message': 'Invalid file path'}, status=403)

        # Check if the file/directory exists
        if not os.path.exists(full_path):
            return JsonResponse({'status': 'error', 'message': 'File or directory does not exist'}, status=404)

        # Create the new path
        parent_dir = os.path.dirname(file_path)
        new_path = os.path.join(parent_dir, new_name)
        new_full_path = os.path.join(data_dir, new_path)

        # Security check: make sure the new path is within the project directory
        if os.path.commonpath([new_full_path, data_dir]) != data_dir:
            return JsonResponse({'status': 'error', 'message': 'Invalid new path'}, status=403)

        # Check if the new path already exists
        if os.path.exists(new_full_path):
            return JsonResponse({'status': 'error', 'message': 'A file or directory with that name already exists'}, status=400)

        # Rename the file/directory
        os.rename(full_path, new_full_path)

        is_dir = os.path.isdir(new_full_path)

        return JsonResponse({
            'status': 'success',
            'message': 'File or directory renamed successfully',
            'item': {
                'name': new_name,
                'path': new_path,
                'is_dir': is_dir,
                'size': '0 B' if not is_dir else None,
                'extension': os.path.splitext(new_name)[1].lstrip('.') if not is_dir else None,
                'children': [] if is_dir else None
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def chat_with_openai_internal(
    request, project, user_profile, message,
    current_file, current_file_content,
    user_chat_message, recent_messages
):
    """
    Internal function for chatting with OpenAI.

    This function is extracted from the chat_with_openai view to be reusable
    by other components like the reasoning integration.
    """
    try:
        # Create the MCP instance
        from .file_operations import FileOperations
        mcp = FileOperations(project, request.user)

        # Prepare the system message with context about the project
        system_message = f"You are an AI coding assistant helping with a project named '{project.title}'. "

        if project.description:
            system_message += f"Project description: {project.description}. "

        # Add additional guidance
        system_message += """
You can help the user by creating, reading, updating, and deleting files in their project.
Use the available tools when the user asks you to perform file operations.
Provide concise, helpful responses focused on coding assistance.
"""

        if current_file:
            system_message += f"The user is currently editing a file named '{current_file}'. "

        # Prepare the messages for the API
        messages = [
            {"role": "system", "content": system_message}
        ]

        # Add conversation history
        for msg in recent_messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the current message
        messages.append({"role": "user", "content": message})

        # If there's a current file, include its content
        if current_file and current_file_content:
            file_message = f"Here's the content of the file I'm working on ({current_file}):\n\n```\n{current_file_content}\n```"
            messages.insert(1, {"role": "user", "content": file_message})

        # Make the API request to OpenAI with tools
        headers = {
            "Authorization": f"Bearer {user_profile.openai_api_key}",
            "Content-Type": "application/json"
        }

        # Get tool definitions from MCP
        tools = mcp.get_tools()

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",  # Let the model decide when to use tools
            "temperature": 0.7,
            "max_tokens": 1500
        }

        logger.info(f"Sending request to OpenAI with {len(tools)} tools")

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        # Check if the request was successful
        if response.status_code != 200:
            error_message = response.json().get('error', {}).get('message', 'Unknown error')
            return JsonResponse({
                'status': 'error',
                'message': f"OpenAI API error: {error_message}"
            }, status=response.status_code)

        # Extract the assistant's response
        response_data = response.json()
        assistant_message = response_data['choices'][0]['message']

        # Initialize variables
        content = assistant_message.get('content', '')
        tool_calls = assistant_message.get('tool_calls', [])
        tool_results = []

        # Process any tool calls
        if tool_calls:
            logger.info(f"Received {len(tool_calls)} tool calls from OpenAI")

            for tool_call in tool_calls:
                function = tool_call.get('function', {})
                tool_name = function.get('name')
                arguments = function.get('arguments')

                logger.info(f"Executing tool call: {tool_name} with arguments: {arguments}")

                # Execute the tool
                result = mcp.execute_tool(tool_name, arguments)

                # Store the result
                tool_results.append({
                    'tool': tool_name,
                    'arguments': json.loads(arguments),
                    'result': result
                })

                # Add tool result to the content
                tool_result_text = f"\n\n<div class=\"chat-tool-result {result.get('status', 'unknown')}\" data-tool-type=\"{tool_name}\">\n"
                tool_result_text += f"# Tool Result: {result.get('status', 'unknown').upper()}\n"
                tool_result_text += f"# Tool: {tool_name}\n\n"
                tool_result_text += f"{result.get('message', 'No message provided')}\n"

                # Add file path if available
                if 'file_path' in result:
                    tool_result_text += f"\nFile: {result['file_path']}"

                tool_result_text += "</div>\n"

                if content:
                    content += tool_result_text
                else:
                    content = tool_result_text

        # Use the processed content
        processed_message = content

        # Save the assistant's response to the database
        ChatMessage.objects.create(
            project=project,
            user=request.user,
            role='assistant',
            content=processed_message
        )

        # Return the processed message, tool results, and conversation history
        return JsonResponse({
            'status': 'success',
            'message': processed_message,
            'tool_results': tool_results,
            'history': [
                {
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                } for msg in recent_messages + [user_chat_message]
            ]
        })

    except Exception as e:
        logger.exception(f"Error in chat with OpenAI: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_POST
@csrf_exempt
def chat_with_openai(request, pk):
    """Send a message to OpenAI API and get a response."""
    try:
        # Get the project and user profile
        project = get_object_or_404(Project, pk=pk, user=request.user)
        user_profile = UserProfile.objects.get(user=request.user)

        # Check if the user has an OpenAI API key
        if not user_profile.openai_api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'No OpenAI API key found. Please add your API key in your profile settings.'
            }, status=400)

        # Parse the request body
        data = json.loads(request.body)
        message = data.get('message')

        if not message:
            return JsonResponse({
                'status': 'error',
                'message': 'Message is required'
            }, status=400)

        # Save the user message to the database
        user_chat_message = ChatMessage.objects.create(
            project=project,
            user=request.user,
            role='user',
            content=message
        )

        # Get the current file content if provided
        current_file = data.get('current_file')
        current_file_content = data.get('current_file_content')

        # Get the last 10 messages for this project (excluding the one we just created)
        recent_messages = ChatMessage.objects.filter(
            project=project
        ).exclude(
            id=user_chat_message.id
        ).order_by('-timestamp')[:9]  # Get 9 to make room for the new message

        # Reverse the order to have oldest first
        recent_messages = list(reversed(recent_messages))

        # Call the internal function
        return chat_with_openai_internal(
            request, project, user_profile, message,
            current_file, current_file_content,
            user_chat_message, recent_messages
        )

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception(f"Error in chat with OpenAI view: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def get_file_tree(request, pk):
    """Get the file tree for a project."""
    try:
        # Get the project
        project = get_object_or_404(Project, pk=pk, user=request.user)

        # Get the project's data directory
        data_dir = project.get_data_directory()

        # Function to recursively get all files and directories
        def get_directory_structure(root_path, relative_path=""):
            items = []
            full_path = os.path.join(root_path, relative_path)

            try:
                for item in os.listdir(full_path):
                    item_relative_path = os.path.join(relative_path, item)
                    item_full_path = os.path.join(root_path, item_relative_path)

                    is_dir = os.path.isdir(item_full_path)

                    # Skip hidden files and directories
                    if item.startswith('.'):
                        continue

                    if is_dir:
                        children = get_directory_structure(root_path, item_relative_path)
                        items.append({
                            'name': item,
                            'path': item_relative_path,
                            'is_dir': True,
                            'children': children
                        })
                    else:
                        # Get file size
                        size = os.path.getsize(item_full_path)
                        # Format size
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"

                        # Get file extension
                        _, ext = os.path.splitext(item)
                        ext = ext.lstrip('.')

                        items.append({
                            'name': item,
                            'path': item_relative_path,
                            'is_dir': False,
                            'size': size_str,
                            'extension': ext
                        })
            except FileNotFoundError:
                # If the directory doesn't exist yet, create it
                os.makedirs(full_path, exist_ok=True)
            except PermissionError:
                # Handle permission errors
                pass

            # Sort items: directories first, then files, both alphabetically
            return sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))

        # Get the directory structure
        directory_structure = get_directory_structure(data_dir)

        # Return the directory structure as JSON
        return JsonResponse({
            'status': 'success',
            'directory_structure': directory_structure
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def chat_history(request, pk):
    """Get the chat history for a project."""
    try:
        # Get the project
        project = get_object_or_404(Project, pk=pk, user=request.user)

        # Get the last 10 messages for this project
        messages = ChatMessage.objects.filter(
            project=project
        ).order_by('-timestamp')[:10]

        # Reverse the order to have oldest first
        messages = list(reversed(messages))

        # Return the messages
        return JsonResponse({
            'status': 'success',
            'history': [
                {
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                } for msg in messages
            ]
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_POST
@csrf_exempt
def run_file(request, pk):
    """Run a file in the project's container."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    # Get the user profile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    try:
        # Parse the request body
        data = json.loads(request.body)
        file_path = data.get('file_path')

        if not file_path:
            return JsonResponse({
                'status': 'error',
                'message': 'No file path provided.'
            })

        # Create the MCP instance
        from .file_operations import FileOperations
        mcp = FileOperations(project, request.user)

        # Run the file
        result = mcp.run_file(file_path)

        # Return the result
        return JsonResponse({
            'status': result['status'],
            'message': result['message'],
            'command': result.get('command', ''),
            'stdout': result.get('stdout', ''),
            'stderr': result.get('stderr', ''),
            'return_code': result.get('return_code', -1)
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body.'
        })
    except Exception as e:
        logger.exception(f"Error running file: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error running file: {str(e)}'
        })