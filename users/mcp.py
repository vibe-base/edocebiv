"""
Model Context Protocol (MCP) for OpenAI function calling.
A simple implementation for registering and executing tools with OpenAI.
"""

import json
import logging
import inspect
from functools import wraps

logger = logging.getLogger(__name__)

# Global registry for tool definitions
TOOL_REGISTRY = {}

def tool(name=None, description=None):
    """
    Decorator to register a function as a tool for OpenAI function calling.
    
    Args:
        name: Optional custom name for the tool (defaults to function name)
        description: Optional description (defaults to function docstring)
    """
    def decorator(func):
        # Get tool metadata
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description provided"
        
        # Extract parameter information
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter for methods
            if param_name == 'self':
                continue
                
            # Add parameter to properties
            properties[param_name] = {"type": "string"}
            
            # Add description if available in docstring
            if func.__doc__:
                param_marker = f":param {param_name}:"
                if param_marker in func.__doc__:
                    desc = func.__doc__.split(param_marker)[1].split("\n")[0].strip()
                    properties[param_name]["description"] = desc
            
            # Track required parameters
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        # Create OpenAI tool definition
        tool_def = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        
        # Register the tool
        TOOL_REGISTRY[tool_name] = {
            "function": func,
            "definition": tool_def
        }
        
        # Return the original function unchanged
        return func
    
    return decorator


class MCP:
    """
    Model Context Protocol for OpenAI function calling.
    Handles tool registration and execution.
    """
    
    def __init__(self):
        """Initialize the MCP with tools from the registry."""
        self.tools = {}
        self.tool_definitions = []
        
        # Find all tools defined in this class
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name in TOOL_REGISTRY:
                # Register the method as a tool
                self.tools[name] = method
                self.tool_definitions.append(TOOL_REGISTRY[name]["definition"])
                logger.info(f"Registered tool: {name}")
    
    def get_tools(self):
        """Get the list of tool definitions for OpenAI API."""
        return self.tool_definitions
    
    def execute_tool(self, name, arguments):
        """
        Execute a tool by name with the given arguments.
        
        Args:
            name: The name of the tool to execute
            arguments: The arguments to pass to the tool (dict or JSON string)
            
        Returns:
            The result of the tool execution
        """
        # Parse arguments if they're a string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": f"Invalid JSON arguments: {arguments}"
                }
        
        # Check if the tool exists
        if name not in self.tools:
            return {
                "status": "error",
                "message": f"Unknown tool: {name}"
            }
        
        # Execute the tool
        try:
            logger.info(f"Executing tool: {name} with arguments: {arguments}")
            result = self.tools[name](**arguments)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing tool: {str(e)}"
            }
