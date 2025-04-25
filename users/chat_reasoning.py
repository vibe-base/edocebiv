"""
Integration of chat and reasoning functionality.
"""

import json
import logging
from typing import Dict, Any, List

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Project, UserProfile, ChatMessage, ReasoningSession, ReasoningStep
from .ai_reasoning import AIReasoning
from .simple_reasoning import SimpleReasoning
from .file_operations import FileOperations

logger = logging.getLogger(__name__)


@login_required
@require_POST
@csrf_exempt
def chat_with_reasoning(request, pk):
    """
    Chat with OpenAI with reasoning capabilities.

    This endpoint combines the regular chat functionality with the reasoning chain.
    It detects when a complex task is requested and uses the reasoning chain to handle it.
    """
    try:
        # Get the project
        project = get_object_or_404(Project, pk=pk, user=request.user)

        # Get the user profile
        user_profile = get_object_or_404(UserProfile, user=request.user)

        # Check if the user has an OpenAI API key
        if not user_profile.openai_api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'No OpenAI API key found. Please add your API key in your profile settings.'
            }, status=400)

        # Parse the request body
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        current_file = data.get('current_file')
        current_file_content = data.get('current_file_content')
        use_reasoning = data.get('use_reasoning', False)

        if not message:
            return JsonResponse({
                'status': 'error',
                'message': 'Message is required'
            }, status=400)

        # Save the user's message to the database
        user_chat_message = ChatMessage.objects.create(
            project=project,
            user=request.user,
            role='user',
            content=message
        )

        # Get the last 10 messages for this project (excluding the one we just added)
        recent_messages = ChatMessage.objects.filter(
            project=project
        ).exclude(
            id=user_chat_message.id
        ).order_by('-timestamp')[:9]

        # Reverse the order to have oldest first
        recent_messages = list(reversed(recent_messages))

        # Determine if we should use reasoning based on the message complexity
        # or if the user explicitly requested it
        should_use_reasoning = use_reasoning or _is_complex_task(message)

        if should_use_reasoning:
            # Use the reasoning chain
            return _handle_reasoning_request(
                request, project, user_profile, message,
                current_file, current_file_content,
                user_chat_message, recent_messages
            )
        else:
            # Use regular chat
            from .views import chat_with_openai_internal
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
        logger.exception(f"Error in chat with reasoning: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def _is_complex_task(message: str) -> bool:
    """
    Determine if a message represents a complex task that would benefit from reasoning.

    Args:
        message: The user's message

    Returns:
        True if the message is a complex task, False otherwise
    """
    # Keywords that suggest a multi-step task
    complex_keywords = [
        "create and run",
        "write and execute",
        "implement and test",
        "build a",
        "develop a",
        "make a",
        "create a complete",
        "step by step",
        "sequence",
        "workflow",
        "pipeline",
        "multiple steps",
        "series of",
        "chain of",
        "first do",
        "then do",
        "after that",
        "finally",
        "multi-step",
        "multi step"
    ]

    # Check if any of the keywords are in the message
    message_lower = message.lower()
    for keyword in complex_keywords:
        if keyword in message_lower:
            return True

    # Check if the message contains multiple instructions (sentences with imperative verbs)
    sentences = [s.strip() for s in message.split('.') if s.strip()]
    imperative_count = 0
    imperative_verbs = ["create", "make", "build", "write", "implement", "add", "update",
                        "delete", "remove", "change", "modify", "run", "execute", "test",
                        "check", "verify", "generate", "install", "configure", "set up"]

    for sentence in sentences:
        words = sentence.lower().split()
        if words and words[0] in imperative_verbs:
            imperative_count += 1

    # If there are multiple imperative sentences, it's likely a complex task
    return imperative_count >= 2


def _handle_reasoning_request(
    request, project, user_profile, message,
    current_file, current_file_content,
    user_chat_message, recent_messages
) -> JsonResponse:
    """
    Handle a request using the reasoning chain.

    Args:
        request: The HTTP request
        project: The project
        user_profile: The user profile
        message: The user's message
        current_file: The current file being edited (if any)
        current_file_content: The content of the current file (if any)
        user_chat_message: The saved user message
        recent_messages: Recent chat messages

    Returns:
        JsonResponse with the reasoning results
    """
    # Create context for reasoning
    context = {
        'current_file': current_file,
        'current_file_content': current_file_content
    }

    try:
        # Initialize the AI reasoning system with a try/except block
        try:
            # First try with the LangChain-based reasoning
            try:
                # Try to initialize the AI reasoning system
                reasoning = AIReasoning(project, user_profile.openai_api_key)
            except Exception as e:
                # If there's any error with the LangChain-based reasoning, fall back to simple reasoning
                logger.warning(f"Falling back to simple reasoning due to error: {str(e)}")

                # Log a message to the user
                ChatMessage.objects.create(
                    project=project,
                    user=request.user,
                    role='system',
                    content="Using simplified reasoning system due to compatibility issues with the advanced system."
                )

                # Use the simple reasoning implementation instead
                reasoning = SimpleReasoning(project, user_profile.openai_api_key)
        except Exception as e:
            # If both reasoning systems fail, fall back to regular chat
            logger.error(f"Both reasoning systems failed: {str(e)}")
            error_message = f"The reasoning system encountered an initialization error: {str(e)}. Falling back to regular chat."

            # Save the error message as a system message
            ChatMessage.objects.create(
                project=project,
                user=request.user,
                role='system',
                content=error_message
            )

            # Fall back to regular chat
            from .views import chat_with_openai_internal
            return chat_with_openai_internal(
                request, project, user_profile, message,
                current_file, current_file_content,
                user_chat_message, recent_messages
            )

        # Execute the reasoning chain
        session = reasoning.execute_reasoning_chain(message, context)

        # Get all steps
        steps = session.steps.all().order_by('step_number')

        if not steps.exists():
            # If no steps were created, there was likely an error
            error_message = "The reasoning system encountered an error. Falling back to regular chat."
            logger.error(f"No reasoning steps created for session {session.id}")

            # Delete the empty session
            session.delete()

            # Fall back to regular chat
            from .views import chat_with_openai_internal
            return chat_with_openai_internal(
                request, project, user_profile, message,
                current_file, current_file_content,
                user_chat_message, recent_messages
            )
    except Exception as e:
        logger.exception(f"Error in reasoning system: {str(e)}")
        error_message = f"The reasoning system encountered an error: {str(e)}. Falling back to regular chat."

        # Save the error message as a system message
        ChatMessage.objects.create(
            project=project,
            user=request.user,
            role='system',
            content=error_message
        )

        # Fall back to regular chat
        from .views import chat_with_openai_internal
        return chat_with_openai_internal(
            request, project, user_profile, message,
            current_file, current_file_content,
            user_chat_message, recent_messages
        )

    # Format the response for the chat
    response_content = f"I've analyzed your request and broken it down into steps:\n\n"

    for step in steps:
        # Add step header
        response_content += f"**Step {step.step_number}: {step.step_type.replace('_', ' ').title()}**\n"

        # Add step response (truncated if too long)
        step_response = step.response
        if len(step_response) > 500:
            step_response = step_response[:500] + "...\n[Response truncated for readability]"

        response_content += f"{step_response}\n\n"

    # Add a link to the full reasoning session
    response_content += f"\nYou can view the full reasoning session here: [Reasoning Session #{session.id}](/users/projects/{project.id}/reasoning/sessions/{session.id}/)\n"

    # Save the assistant's response to the database
    ChatMessage.objects.create(
        project=project,
        user=request.user,
        role='assistant',
        content=response_content
    )

    # Get any tool results from the reasoning steps
    tool_results = []
    for step in steps:
        if step.tool_calls:
            for tool_call in step.tool_calls:
                tool_results.append({
                    'tool': tool_call.get('name', 'unknown'),
                    'arguments': tool_call.get('arguments', {}),
                    'result': tool_call.get('result', {})
                })

    # Return the response
    return JsonResponse({
        'status': 'success',
        'message': response_content,
        'reasoning_session_id': session.id,
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
