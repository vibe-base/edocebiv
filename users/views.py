from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from .models import Project, UserProfile
from .forms import ProjectForm, UserProfileForm
from .docker_utils import docker_manager

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
            messages.error(request, 'Failed to create container. Please check the logs.')

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
