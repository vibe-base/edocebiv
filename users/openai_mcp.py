"""
OpenAI Model Context Protocol (MCP) Implementation.
This module provides a framework for registering functions as tools for OpenAI models.
"""

import inspect
import json
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class OpenAIMCP:
    """
    OpenAI Model Context Protocol (MCP) Implementation.
    Provides a framework for registering functions as tools for OpenAI models.
    """

    def __init__(self):
        """Initialize the MCP with an empty tools registry."""
        self.tools = {}
        self.tool_definitions = []

        # Register all tools decorated with @register_tool
        self._register_tools()

    @classmethod
    def register_tool(cls, name=None, description=None):
        """
        Class method decorator to register a method as a tool.

        Args:
            name (str, optional): Name of the tool. Defaults to the method name.
            description (str, optional): Description of the tool. Defaults to the method docstring.

        Returns:
            function: Decorator function.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # The actual function execution happens here
                return func(self, *args, **kwargs)

            # Store metadata on the wrapper function for later registration
            wrapper._is_tool = True
            wrapper._tool_name = name or func.__name__
            wrapper._tool_description = description or func.__doc__ or "No description provided."

            return wrapper

        return decorator

    def _register_tools(self):
        """
        Register all methods decorated with @register_tool.
        This should be called during initialization.
        """
        for attr_name in dir(self):
            if attr_name.startswith('_'):
                continue

            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, '_is_tool') and attr._is_tool:
                self._register_single_tool(attr)

    def _register_single_tool(self, func):
        """Register a single tool function."""
        tool_name = func._tool_name
        tool_description = func._tool_description

        # Get the function signature
        sig = inspect.signature(func)
        parameters = {}
        required_params = []

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_info = {
                "type": "string"  # Default type
            }

            # Extract parameter description from docstring if available
            if func.__doc__:
                param_desc_marker = f":param {param_name}:"
                if param_desc_marker in func.__doc__:
                    param_desc = func.__doc__.split(param_desc_marker)[1].split("\n")[0].strip()
                    param_info["description"] = param_desc

            parameters[param_name] = param_info

            # Track required parameters
            if param.default == inspect.Parameter.empty:
                required_params.append(param_name)

        # Register the tool
        self.tools[tool_name] = func

        # Create OpenAI tool definition
        tool_def = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required_params
                }
            }
        }

        self.tool_definitions.append(tool_def)

        logger.info(f"Registered tool: {tool_name}")

    def get_tool_definitions(self):
        """
        Get OpenAI tool definitions for all registered tools.

        Returns:
            list: List of tool definitions in OpenAI format.
        """
        return self.tool_definitions

    def execute_tool(self, tool_call):
        """
        Execute a tool call from OpenAI.

        Args:
            tool_call (dict): The tool call from OpenAI.

        Returns:
            dict: Result of the tool execution.
        """
        tool_name = tool_call.get('name')
        arguments_str = tool_call.get('arguments', '{}')

        try:
            # Parse arguments if it's a string
            if isinstance(arguments_str, str):
                arguments = json.loads(arguments_str)
            else:
                arguments = arguments_str
        except json.JSONDecodeError:
            logger.error(f"Invalid arguments JSON: {arguments_str}")
            return {
                'status': 'error',
                'message': f'Invalid arguments JSON: {arguments_str}'
            }

        if tool_name not in self.tools:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                'status': 'error',
                'message': f'Unknown tool: {tool_name}'
            }

        try:
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
            # Call the tool method with self as the first argument
            result = self.tools[tool_name](**arguments)
            logger.info(f"Tool execution result: {result}")
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error executing tool {tool_name}: {str(e)}'
            }
