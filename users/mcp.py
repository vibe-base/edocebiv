"""
Model Context Protocol (MCP) for AI interactions.
This module provides a framework for registering methods as tools for AI to use.
"""

import inspect
import json
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class ModelContextProtocol:
    """
    Model Context Protocol (MCP) for AI interactions.
    Provides a framework for registering methods as tools for AI to use.
    """
    
    def __init__(self):
        """Initialize the MCP with an empty tools registry."""
        self.tools = {}
        self.tool_descriptions = {}
    
    def register_tool(self, name=None, description=None):
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
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_info = {
                    "type": "string",  # Default type
                    "required": param.default == inspect.Parameter.empty
                }
                
                # Extract parameter description from docstring if available
                if func.__doc__:
                    param_desc_marker = f":param {param_name}:"
                    if param_desc_marker in func.__doc__:
                        param_desc = func.__doc__.split(param_desc_marker)[1].split("\n")[0].strip()
                        param_info["description"] = param_desc
                
                parameters[param_name] = param_info
            
            # Register the tool
            self.tools[tool_name] = func
            
            # Store tool description
            self.tool_descriptions[tool_name] = {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters
            }
            
            logger.info(f"Registered tool: {tool_name}")
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    def execute_tool(self, tool_call):
        """
        Execute a tool call.
        
        Args:
            tool_call (dict): The tool call to execute.
            
        Returns:
            dict: Result of the tool execution.
        """
        tool_name = tool_call.get('name')
        arguments = tool_call.get('arguments', {})
        
        if tool_name not in self.tools:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                'status': 'error',
                'message': f'Unknown tool: {tool_name}'
            }
        
        try:
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
            result = self.tools[tool_name](**arguments)
            logger.info(f"Tool execution result: {result}")
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error executing tool {tool_name}: {str(e)}'
            }
    
    def get_tool_descriptions(self):
        """
        Get descriptions of all registered tools.
        
        Returns:
            list: List of tool descriptions.
        """
        return list(self.tool_descriptions.values())
    
    def get_system_message(self):
        """
        Generate a system message describing how to use the tools.
        
        Returns:
            str: System message.
        """
        message = "You can use tools to interact with the system. To use a tool, include a code block with the tool name and arguments in JSON format:\n\n"
        message += "```tool\n{\n  \"name\": \"tool_name\",\n  \"arguments\": {\n    \"arg1\": \"value1\",\n    \"arg2\": \"value2\"\n  }\n}\n```\n\n"
        
        message += "Available tools:\n"
        
        for tool_name, description in self.tool_descriptions.items():
            message += f"- {tool_name}: {description['description'].split('.')[0]}.\n"
            message += "  Arguments:\n"
            
            for param_name, param_info in description['parameters'].items():
                required = "required" if param_info.get('required', False) else "optional"
                param_desc = param_info.get('description', 'No description')
                message += f"    - {param_name} ({required}): {param_desc}\n"
            
            message += "\n"
        
        message += "Examples:\n\n"
        
        # Add examples for each tool
        for tool_name, description in self.tool_descriptions.items():
            message += f"Example of using the {tool_name} tool:\n"
            message += "```tool\n{\n  \"name\": \"" + tool_name + "\",\n  \"arguments\": {\n"
            
            # Create example arguments
            example_args = []
            for param_name, param_info in description['parameters'].items():
                if param_info.get('required', False):
                    example_args.append(f"    \"{param_name}\": \"example_{param_name}\"")
            
            message += ",\n".join(example_args)
            message += "\n  }\n}\n```\n\n"
        
        message += "When a user asks you to perform operations, use these tools to help them. Always use the tools when appropriate rather than just describing what changes should be made.\n"
        
        return message
    
    def parse_tool_calls(self, message):
        """
        Parse tool calls from an AI message.
        
        Args:
            message (str): The AI message to parse.
            
        Returns:
            list: List of tool calls.
        """
        import re
        
        # Regular expression to match tool calls
        tool_pattern = r'```tool\s+([\s\S]*?)```'
        
        # Find all tool calls in the message
        tool_matches = re.findall(tool_pattern, message)
        
        tool_calls = []
        for tool_match in tool_matches:
            try:
                # Parse the tool call as JSON
                tool_call = json.loads(tool_match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                # If the tool call is not valid JSON, skip it
                continue
        
        return tool_calls
    
    def process_message(self, message):
        """
        Process an AI message and execute any tool calls.
        
        Args:
            message (str): The AI message to process.
            
        Returns:
            tuple: (processed_message, tool_results)
        """
        # Parse tool calls from the message
        tool_calls = self.parse_tool_calls(message)
        
        # If there are no tool calls, return the original message
        if not tool_calls:
            return message, []
        
        # Execute each tool call
        tool_results = []
        for tool_call in tool_calls:
            result = self.execute_tool(tool_call)
            tool_results.append({
                'tool': tool_call.get('name'),
                'arguments': tool_call.get('arguments', {}),
                'result': result
            })
        
        # Replace tool calls with their results in the message
        processed_message = message
        import re
        for i, tool_match in enumerate(re.finditer(r'```tool\s+([\s\S]*?)```', message)):
            if i < len(tool_results):
                result = tool_results[i]['result']
                tool_name = tool_results[i]['tool']
                status = result.get('status', 'unknown')
                result_message = result.get('message', 'No message provided')
                
                # Create a more detailed replacement with tool name and status
                replacement = f'<div class="chat-tool-result {status}" data-tool-type="{tool_name}">\n'
                replacement += f"# Tool Result: {status.upper()}\n"
                replacement += f"# Tool: {tool_name}\n\n"
                replacement += f"{result_message}\n"
                
                # Add file path if available
                if 'file_path' in result:
                    replacement += f"\nFile: {result['file_path']}"
                
                replacement += "</div>"
                
                processed_message = processed_message.replace(tool_match.group(0), replacement, 1)
        
        # Log the tool results for debugging
        if tool_results:
            logger.info(f"Executed {len(tool_results)} tool calls: {[r['tool'] for r in tool_results]}")
        
        return processed_message, tool_results
