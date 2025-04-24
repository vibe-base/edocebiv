from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Project
from .forms import ProjectForm

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
    return render(request, 'users/project_detail.html', {'project': project})
