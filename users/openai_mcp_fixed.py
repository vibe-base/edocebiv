"""
OpenAI Model Context Protocol (MCP) Implementation.
This module provides a framework for registering functions as tools for OpenAI models.
"""

import inspect
import json
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Global registry to store tool definitions
_TOOL_REGISTRY = {}

def register_tool(name=None, description=None):
    """
    Decorator to register a method as a tool.
    
    Args:
        name (str, optional): Name of the tool. Defaults to the method name.
        description (str, optional): Description of the tool. Defaults to the method docstring.
    
    Returns:
        function: Decorator function.
    """
    def decorator(func):
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description provided."
        
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
        
        # Store in global registry
        _TOOL_REGISTRY[tool_name] = {
            'function': func,
            'definition': tool_def
        }
        
        logger.info(f"Registered tool: {tool_name}")
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        
        # Add metadata to the wrapper
        wrapper._is_tool = True
        wrapper._tool_name = tool_name
        
        return wrapper
    
    return decorator


class OpenAIMCP:
    """
    OpenAI Model Context Protocol (MCP) Implementation.
    Provides a framework for registering functions as tools for OpenAI models.
    """
    
    def __init__(self):
        """Initialize the MCP with tools from the registry."""
        self.tools = {}
        self.tool_definitions = []
        
        # Register tools from the global registry
        for tool_name, tool_info in _TOOL_REGISTRY.items():
            self.tools[tool_name] = getattr(self, tool_name, None)
            if self.tools[tool_name]:
                self.tool_definitions.append(tool_info['definition'])
            else:
                logger.warning(f"Tool {tool_name} registered but not found in class")
    
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
            # Call the tool method
            result = self.tools[tool_name](**arguments)
            logger.info(f"Tool execution result: {result}")
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error executing tool {tool_name}: {str(e)}'
            }
