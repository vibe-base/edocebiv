class NoCacheMiddleware:
    """
    Middleware to add no-cache headers to specific responses.
    This prevents browsers from caching authentication-related pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only add no-cache headers to authentication-related pages
        path = request.path.lower()
        if path.startswith('/accounts/') or path == '/' or 'signup' in path or 'login' in path:
            # Add no-cache headers
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response
