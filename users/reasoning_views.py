"""
Views for AI reasoning functionality.
"""

import json
import logging
from typing import Dict, Any

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Project, UserProfile, ReasoningSession, ReasoningStep
from .ai_reasoning import AIReasoning

logger = logging.getLogger(__name__)


@login_required
def reasoning_dashboard(request, pk):
    """
    Display the reasoning dashboard for a project.
    
    Args:
        request: HTTP request
        pk: Project ID
        
    Returns:
        Rendered dashboard template
    """
    project = get_object_or_404(Project, pk=pk, user=request.user)
    sessions = ReasoningSession.objects.filter(project=project).order_by('-created_at')
    
    return render(request, 'users/reasoning_dashboard.html', {
        'project': project,
        'sessions': sessions
    })


@login_required
def reasoning_session_detail(request, pk, session_id):
    """
    Display details of a reasoning session.
    
    Args:
        request: HTTP request
        pk: Project ID
        session_id: Reasoning session ID
        
    Returns:
        Rendered session detail template
    """
    project = get_object_or_404(Project, pk=pk, user=request.user)
    session = get_object_or_404(ReasoningSession, pk=session_id, project=project)
    steps = session.steps.all().order_by('step_number')
    
    return render(request, 'users/reasoning_session_detail.html', {
        'project': project,
        'session': session,
        'steps': steps
    })


@login_required
@require_POST
@csrf_exempt
def start_reasoning(request, pk):
    """
    Start a new reasoning session.
    
    Args:
        request: HTTP request
        pk: Project ID
        
    Returns:
        JSON response with session details
    """
    try:
        # Get the project and user profile
        project = get_object_or_404(Project, pk=pk, user=request.user)
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Check if the user has an OpenAI API key
        if not user_profile.openai_api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'No OpenAI API key found. Please add your API key in your profile settings.'
            }, status=400)
        
        # Parse the request body
        data = json.loads(request.body)
        task = data.get('task')
        
        if not task:
            return JsonResponse({
                'status': 'error',
                'message': 'Task description is required'
            }, status=400)
        
        # Get context information
        context = {
            'current_file': data.get('current_file'),
            'current_file_content': data.get('current_file_content')
        }
        
        # Initialize the AI reasoning system
        reasoning = AIReasoning(project, user_profile.openai_api_key)
        
        # Create a new session
        session = reasoning.create_session(
            title=task[:100] + "..." if len(task) > 100 else task,
            description=task
        )
        
        # Return the session ID
        return JsonResponse({
            'status': 'success',
            'message': 'Reasoning session created',
            'session_id': session.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception(f"Error starting reasoning session: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_POST
@csrf_exempt
def execute_reasoning_step(request, pk, session_id):
    """
    Execute a step in a reasoning session.
    
    Args:
        request: HTTP request
        pk: Project ID
        session_id: Reasoning session ID
        
    Returns:
        JSON response with step results
    """
    try:
        # Get the project, session, and user profile
        project = get_object_or_404(Project, pk=pk, user=request.user)
        session = get_object_or_404(ReasoningSession, pk=session_id, project=project)
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Check if the session is already complete
        if session.is_complete:
            return JsonResponse({
                'status': 'error',
                'message': 'This reasoning session is already complete'
            }, status=400)
        
        # Check if the user has an OpenAI API key
        if not user_profile.openai_api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'No OpenAI API key found. Please add your API key in your profile settings.'
            }, status=400)
        
        # Parse the request body
        data = json.loads(request.body)
        step_type = data.get('step_type')
        prompt = data.get('prompt')
        
        if not step_type or not prompt:
            return JsonResponse({
                'status': 'error',
                'message': 'Step type and prompt are required'
            }, status=400)
        
        # Initialize the AI reasoning system
        reasoning = AIReasoning(project, user_profile.openai_api_key)
        
        # Execute the step
        step = reasoning.execute_step(session, step_type, prompt)
        
        # Return the step results
        return JsonResponse({
            'status': 'success',
            'message': 'Reasoning step executed',
            'step': {
                'id': step.id,
                'step_number': step.step_number,
                'step_type': step.step_type,
                'prompt': step.prompt,
                'response': step.response,
                'model_used': step.model_used,
                'is_complete': step.is_complete,
                'error': step.error
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception(f"Error executing reasoning step: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_POST
@csrf_exempt
def execute_full_reasoning(request, pk):
    """
    Execute a full reasoning chain.
    
    Args:
        request: HTTP request
        pk: Project ID
        
    Returns:
        JSON response with session details
    """
    try:
        # Get the project and user profile
        project = get_object_or_404(Project, pk=pk, user=request.user)
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Check if the user has an OpenAI API key
        if not user_profile.openai_api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'No OpenAI API key found. Please add your API key in your profile settings.'
            }, status=400)
        
        # Parse the request body
        data = json.loads(request.body)
        task = data.get('task')
        
        if not task:
            return JsonResponse({
                'status': 'error',
                'message': 'Task description is required'
            }, status=400)
        
        # Get context information
        context = {
            'current_file': data.get('current_file'),
            'current_file_content': data.get('current_file_content')
        }
        
        # Initialize the AI reasoning system
        reasoning = AIReasoning(project, user_profile.openai_api_key)
        
        # Execute the full reasoning chain
        session = reasoning.execute_reasoning_chain(task, context)
        
        # Get all steps
        steps = session.steps.all().order_by('step_number')
        
        # Return the session and steps
        return JsonResponse({
            'status': 'success',
            'message': 'Reasoning chain executed',
            'session': {
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'is_complete': session.is_complete,
                'created_at': session.created_at.isoformat(),
                'steps': [
                    {
                        'id': step.id,
                        'step_number': step.step_number,
                        'step_type': step.step_type,
                        'prompt': step.prompt,
                        'response': step.response,
                        'model_used': step.model_used,
                        'is_complete': step.is_complete,
                        'error': step.error
                    } for step in steps
                ]
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.exception(f"Error executing reasoning chain: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def get_reasoning_sessions(request, pk):
    """
    Get all reasoning sessions for a project.
    
    Args:
        request: HTTP request
        pk: Project ID
        
    Returns:
        JSON response with sessions
    """
    try:
        # Get the project
        project = get_object_or_404(Project, pk=pk, user=request.user)
        
        # Get all sessions
        sessions = ReasoningSession.objects.filter(project=project).order_by('-created_at')
        
        # Return the sessions
        return JsonResponse({
            'status': 'success',
            'sessions': [
                {
                    'id': session.id,
                    'title': session.title,
                    'description': session.description,
                    'is_complete': session.is_complete,
                    'created_at': session.created_at.isoformat(),
                    'step_count': session.steps.count()
                } for session in sessions
            ]
        })
        
    except Exception as e:
        logger.exception(f"Error getting reasoning sessions: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def get_reasoning_session(request, pk, session_id):
    """
    Get details of a reasoning session.
    
    Args:
        request: HTTP request
        pk: Project ID
        session_id: Reasoning session ID
        
    Returns:
        JSON response with session details
    """
    try:
        # Get the project and session
        project = get_object_or_404(Project, pk=pk, user=request.user)
        session = get_object_or_404(ReasoningSession, pk=session_id, project=project)
        
        # Get all steps
        steps = session.steps.all().order_by('step_number')
        
        # Return the session and steps
        return JsonResponse({
            'status': 'success',
            'session': {
                'id': session.id,
                'title': session.title,
                'description': session.description,
                'is_complete': session.is_complete,
                'created_at': session.created_at.isoformat(),
                'steps': [
                    {
                        'id': step.id,
                        'step_number': step.step_number,
                        'step_type': step.step_type,
                        'prompt': step.prompt,
                        'response': step.response,
                        'model_used': step.model_used,
                        'is_complete': step.is_complete,
                        'error': step.error
                    } for step in steps
                ]
            }
        })
        
    except Exception as e:
        logger.exception(f"Error getting reasoning session: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
