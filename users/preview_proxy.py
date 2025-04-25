import logging
import requests
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Project

logger = logging.getLogger(__name__)

@login_required
def preview_proxy(request, project_id, path=''):
    """
    Proxy requests to the container's web server.
    
    Args:
        request: The HTTP request
        project_id: The project ID
        path: The path to forward to the container
        
    Returns:
        The proxied response
    """
    # Get the project
    project = get_object_or_404(Project, pk=project_id, user=request.user)
    
    # Check if the project has a web server port
    if not project.web_server_port:
        return HttpResponseNotFound("No web server port configured for this project.")
    
    # Check if the container is running
    if project.container_status != 'running':
        return HttpResponseNotFound(f"Container is not running. Current status: {project.container_status}")
    
    # Construct the target URL
    target_url = f"http://localhost:{project.web_server_port}/{path}"
    
    # Remove any double slashes in the URL
    target_url = target_url.replace("//", "/")
    # Add back the http:/ that was incorrectly replaced
    target_url = target_url.replace("http:/", "http://")
    
    logger.info(f"Proxying request to: {target_url}")
    
    try:
        # Forward the request to the container
        response = requests.request(
            method=request.method,
            url=target_url,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ['host']},
            data=request.body if request.method in ['POST', 'PUT', 'PATCH'] else None,
            params=request.GET,
            cookies=request.COOKIES,
            allow_redirects=False,
            timeout=10  # 10 second timeout
        )
        
        # Create Django response from the proxied response
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code
        )
        
        # Copy headers from proxied response
        for header, value in response.headers.items():
            if header.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']:
                django_response[header] = value
        
        return django_response
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error when proxying to {target_url}")
        return HttpResponseNotFound("Could not connect to the web server in the container.")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when proxying to {target_url}")
        return HttpResponseServerError("Request to the container timed out.")
    except Exception as e:
        logger.exception(f"Error proxying request to {target_url}: {str(e)}")
        return HttpResponseServerError(f"Error proxying request: {str(e)}")
