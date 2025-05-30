"""
A simplified version of the AI reasoning module that uses direct API calls instead of LangChain.
This is a fallback for when the LangChain integration has compatibility issues.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional

from .models import Project, ReasoningSession, ReasoningStep
from .file_operations import FileOperations

logger = logging.getLogger(__name__)

# System prompts for different reasoning steps
SYSTEM_PROMPTS = {
    "planning": """You are an expert software developer and AI assistant specialized in planning coding tasks.
Your job is to break down complex coding tasks into clear, actionable steps.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "introduction": "Brief introduction to the task",
    "steps": [
        {
            "title": "Step 1: [Step Title]",
            "description": "Detailed description of what this step involves",
            "files_involved": ["list", "of", "files", "to", "examine", "or", "modify"],
            "tools_needed": ["list", "of", "tools", "that", "might", "be", "needed"]
        },
        // Additional steps...
    ],
    "conclusion": "Brief conclusion or summary"
}

IMPORTANT: In this planning step, DO NOT actually execute any tools or implement any code. Your job is ONLY to create a plan that will be executed in later steps. DO NOT use any tool calls in this step.

The following tools will be available in later steps, but you should NOT use them now:
- read_file: Read the content of a file in the project
- write_file: Write content to a file in the project
- list_files: List files and directories in a directory
- run_file: Run a file in the project's container
- delete_file: Delete a file or directory in the project
- generate_diff: Generate a diff between original and new content
- apply_patch: Apply a patch to a file
- pip_install: Install Python packages using pip in the project's container

Be thorough but concise. Focus on creating a practical, step-by-step plan that will be executed in later steps.
""",

    "analysis": """You are an expert code analyst specialized in understanding codebases.
Examine the provided code carefully and provide insights on:
1. The overall structure and purpose
2. Key components and their relationships
3. Potential issues or areas for improvement
4. How the code relates to the user's request

You have access to the following tools that you MUST use to accomplish the task:
- read_file: Read the content of a file in the project
- list_files: List files and directories in a directory
- generate_diff: Generate a diff between original and new content

To use a tool, format your response like this:
```
<tool>
{
  "name": "read_file",
  "arguments": {
    "file_path": "example.py"
  }
}
</tool>
```

Be thorough and precise in your analysis. This will be used to guide further actions.
""",

    "code_generation": """You are an expert software developer specialized in writing high-quality code.
Generate code based on the provided specifications and analysis.
Your code should be:
1. Well-structured and organized
2. Properly commented
3. Following best practices for the language/framework
4. Compatible with the existing codebase

You have access to the following tools that you MUST use to accomplish the task:
- read_file: Read the content of a file in the project
- write_file: Write content to a file in the project
- list_files: List files and directories in a directory
- generate_diff: Generate a diff between original and new content
- apply_patch: Apply a patch to a file
- pip_install: Install Python packages using pip in the project's container

IMPORTANT: You MUST use the write_file tool to create files. DO NOT just describe the code.

To use a tool, format your response like this:
```
I'll create a Python file that prints "Hello, World!":

<tool>
{
  "name": "write_file",
  "arguments": {
    "file_path": "hello.py",
    "content": "print('Hello, World!')"
  }
}
</tool>
```

For modifying existing files, you can use generate_diff and apply_patch:
```
I'll update the existing file by generating a diff and applying it:

<tool>
{
  "name": "read_file",
  "arguments": {
    "file_path": "hello.py"
  }
}
</tool>

<tool>
{
  "name": "generate_diff",
  "arguments": {
    "original_content": "print('Hello, World!')",
    "new_content": "print('Hello, Updated World!')",
    "file_path": "hello.py"
  }
}
</tool>

<tool>
{
  "name": "apply_patch",
  "arguments": {
    "file_path": "hello.py",
    "patch_content": "--- original/hello.py\\n+++ new/hello.py\\n@@ -1 +1 @@\\n-print('Hello, World!')\\n+print('Hello, Updated World!')"
  }
}
</tool>
```

After using the tools, verify the results and proceed with the next steps.
""",

    "code_execution": """You are an expert in executing and testing code.
Your job is to:
1. Determine how to run the provided code
2. Execute the code using the run_file tool
3. Interpret execution results
4. Fix any issues that arise

You have access to the following tools that you MUST use to accomplish the task:
- read_file: Read the content of a file in the project
- write_file: Write content to a file in the project
- run_file: Run a file in the project's container
- generate_diff: Generate a diff between original and new content
- apply_patch: Apply a patch to a file
- pip_install: Install Python packages using pip in the project's container

IMPORTANT: You MUST use the run_file tool to execute the code. DO NOT just describe how to run it.

To use a tool, format your response like this:
```
I'll run the Python file:

<tool>
{
  "name": "run_file",
  "arguments": {
    "file_path": "hello.py"
  }
}
</tool>
```

If you need to fix issues in the code, you can use generate_diff and apply_patch:
```
I'll fix the code by generating a diff and applying it:

<tool>
{
  "name": "read_file",
  "arguments": {
    "file_path": "hello.py"
  }
}
</tool>

<tool>
{
  "name": "generate_diff",
  "arguments": {
    "original_content": "print('Hello, World!'",  # Note the missing closing parenthesis
    "new_content": "print('Hello, World!')",  # Fixed version
    "file_path": "hello.py"
  }
}
</tool>

<tool>
{
  "name": "apply_patch",
  "arguments": {
    "file_path": "hello.py",
    "patch_content": "--- original/hello.py\\n+++ new/hello.py\\n@@ -1 +1 @@\\n-print('Hello, World!'\\n+print('Hello, World!')"
  }
}
</tool>
```

After running the file, analyze the output and fix any issues if needed.
Be precise and focus on practical execution steps.
""",

    "testing": """You are an expert in software testing.
Your job is to:
1. Design appropriate test cases for the code
2. Implement the test cases using the write_file tool
3. Run the tests using the run_file tool
4. Verify that the code meets requirements

You have access to the following tools that you MUST use to accomplish the task:
- read_file: Read the content of a file in the project
- write_file: Write content to a file in the project
- run_file: Run a file in the project's container
- generate_diff: Generate a diff between original and new content
- apply_patch: Apply a patch to a file
- pip_install: Install Python packages using pip in the project's container

DO NOT just describe the tests - actually create and run them using the tools.

To use a tool, format your response like this:
```
I'll create a test file:

<tool>
{
  "name": "write_file",
  "arguments": {
    "file_path": "test_hello.py",
    "content": "import unittest\\n\\nclass TestHello(unittest.TestCase):\\n    def test_hello(self):\\n        # Test code here\\n        pass\\n\\nif __name__ == '__main__':\\n    unittest.main()"
  }
}
</tool>
```

If you need to modify existing test files, use generate_diff and apply_patch.
Be thorough and methodical in your approach to testing.
""",

    "refinement": """You are an expert in code refinement and optimization.
Based on the previous steps and feedback, your job is to:
1. Identify areas for improvement in the code
2. Implement specific optimizations or refactorings
3. Address any issues or bugs discovered
4. Enhance the code's readability, performance, or maintainability

You have access to the following tools that you MUST use to accomplish the task:
- read_file: Read the content of a file in the project
- write_file: Write content to a file in the project
- run_file: Run a file in the project's container
- generate_diff: Generate a diff between original and new content
- apply_patch: Apply a patch to a file
- pip_install: Install Python packages using pip in the project's container

For small changes to existing files, use generate_diff and apply_patch:
```
I'll refactor this code by generating a diff and applying it:

<tool>
{
  "name": "read_file",
  "arguments": {
    "file_path": "example.py"
  }
}
</tool>

<tool>
{
  "name": "generate_diff",
  "arguments": {
    "original_content": "def calculate(x, y):\\n    return x + y",
    "new_content": "def calculate(x, y):\\n    \"\"\"Add two numbers and return the result.\"\"\"\\n    return x + y",
    "file_path": "example.py"
  }
}
</tool>

<tool>
{
  "name": "apply_patch",
  "arguments": {
    "file_path": "example.py",
    "patch_content": "--- original/example.py\\n+++ new/example.py\\n@@ -1 +1,2 @@\\n def calculate(x, y):\\n+    \"\"\"Add two numbers and return the result.\"\"\"\\n     return x + y"
  }
}
</tool>
```

DO NOT just suggest improvements - actually implement them using the appropriate tools.
Provide specific, actionable improvements.
""",

    "conclusion": """You are an expert in summarizing development work.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "summary": "Overall summary of what was accomplished",
    "key_changes": [
        {
            "description": "Description of a key change or improvement",
            "impact": "Impact of this change"
        },
        // Additional key changes...
    ],
    "files_modified": ["List", "of", "files", "that", "were", "modified"],
    "remaining_issues": ["List", "of", "any", "remaining", "issues"],
    "future_work": ["List", "of", "suggested", "future", "work"],
    "conclusion": "Final concluding thoughts"
}

IMPORTANT: In this conclusion step, DO NOT execute any tools. Your job is ONLY to summarize what was accomplished in the previous steps.

You do not need to use any tools for this step. Just provide a clear, concise summary of the work done.

Be concise but comprehensive in your summary.
"""
}


class SimpleReasoning:
    """
    A simplified version of the AI reasoning system that uses direct API calls instead of LangChain.
    """

    def __init__(self, project: Project, api_key: str):
        """
        Initialize the Simple Reasoning system.

        Args:
            project: The Django project model instance
            api_key: OpenAI API key
        """
        self.project = project
        self.api_key = api_key

        # Initialize file operations
        self.file_ops = FileOperations(project, project.user)

        # Initialize tools
        self.tools = self._create_tools()

    def _create_tools(self) -> List[Dict[str, Any]]:
        """
        Create tools for the OpenAI API.

        Returns:
            List of tool definitions
        """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the content of a file in the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file relative to the project root"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file in the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file relative to the project root"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files and directories in a directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory_path": {
                                "type": "string",
                                "description": "Path to the directory relative to the project root"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_file",
                    "description": "Run a file in the project's container.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to run relative to the project root"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "Delete a file or directory in the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file or directory relative to the project root"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_diff",
                    "description": "Generate a diff between original and new content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "original_content": {
                                "type": "string",
                                "description": "Original content"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "New content"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Optional file path for context"
                            }
                        },
                        "required": ["original_content", "new_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_patch",
                    "description": "Apply a patch to a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to patch"
                            },
                            "patch_content": {
                                "type": "string",
                                "description": "The patch content to apply"
                            }
                        },
                        "required": ["file_path", "patch_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pip_install",
                    "description": "Install Python packages using pip in the project's container.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "packages": {
                                "type": "string",
                                "description": "Space-separated list of packages to install (e.g., 'numpy pandas matplotlib')"
                            }
                        },
                        "required": ["packages"]
                    }
                }
            }
        ]

        return tools

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool

        Returns:
            Result of the tool execution
        """
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")

        try:
            # Execute the appropriate tool
            if tool_name == "read_file":
                file_path = arguments.get("file_path", "")
                if not file_path:
                    return {"status": "error", "message": "No file path provided"}

                logger.info(f"Reading file: {file_path}")
                result = self.file_ops.read_file(file_path)

            elif tool_name == "write_file":
                file_path = arguments.get("file_path", "")
                content = arguments.get("content", "")

                if not file_path:
                    return {"status": "error", "message": "No file path provided"}

                # Check if file exists
                read_result = self.file_ops.read_file(file_path)
                if read_result["status"] == "success":
                    # Update existing file
                    logger.info(f"Updating file: {file_path}")
                    result = self.file_ops.update_file(file_path, content)
                else:
                    # Create new file
                    logger.info(f"Creating file: {file_path}")
                    result = self.file_ops.create_file(file_path, content)

            elif tool_name == "list_files":
                directory_path = arguments.get("directory_path", "")
                logger.info(f"Listing files in directory: {directory_path}")
                result = self.file_ops.list_files(directory_path)

            elif tool_name == "run_file":
                file_path = arguments.get("file_path", "")
                if not file_path:
                    return {"status": "error", "message": "No file path provided"}

                logger.info(f"Running file: {file_path}")
                result = self.file_ops.run_file(file_path)

            elif tool_name == "delete_file":
                file_path = arguments.get("file_path", "")
                if not file_path:
                    return {"status": "error", "message": "No file path provided"}

                logger.info(f"Deleting file: {file_path}")
                result = self.file_ops.delete_file(file_path)

            elif tool_name == "generate_diff":
                original_content = arguments.get("original_content", "")
                new_content = arguments.get("new_content", "")
                file_path = arguments.get("file_path")

                if not original_content or not new_content:
                    return {"status": "error", "message": "Both original_content and new_content must be provided"}

                logger.info(f"Generating diff" + (f" for file: {file_path}" if file_path else ""))
                result = self.file_ops.generate_diff(original_content, new_content, file_path)

            elif tool_name == "apply_patch":
                file_path = arguments.get("file_path", "")
                patch_content = arguments.get("patch_content", "")

                if not file_path:
                    return {"status": "error", "message": "No file path provided"}
                if not patch_content:
                    return {"status": "error", "message": "No patch content provided"}

                logger.info(f"Applying patch to file: {file_path}")
                result = self.file_ops.apply_patch(file_path, patch_content)

            elif tool_name == "pip_install":
                packages = arguments.get("packages", "")

                if not packages:
                    return {"status": "error", "message": "No packages provided"}

                logger.info(f"Installing pip packages: {packages}")
                result = self.file_ops.pip_install(packages)

            else:
                logger.warning(f"Unknown tool: {tool_name}")
                result = {"status": "error", "message": f"Unknown tool: {tool_name}"}

            # Send a WebSocket notification about the tool execution
            self._send_tool_notification(tool_name, result)

            return result

        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}: {str(e)}")
            error_result = {"status": "error", "message": f"Error executing tool {tool_name}: {str(e)}"}

            # Send a WebSocket notification about the error
            self._send_tool_notification(tool_name, error_result)

            return error_result

    def _send_tool_notification(self, tool_name: str, result: Dict[str, Any]) -> None:
        """
        Send a WebSocket notification about a tool execution.

        Args:
            tool_name: The name of the tool that was executed
            result: The result of the tool execution
        """
        try:
            # Import here to avoid circular imports
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            # Get the channel layer
            channel_layer = get_channel_layer()

            # Get the project ID
            project_id = self.project.id

            # Send the notification to the group
            async_to_sync(channel_layer.group_send)(
                f"tools_{project_id}",
                {
                    "type": "tool_executed",
                    "tool_name": tool_name,
                    "result": result
                }
            )

            logger.info(f"Sent WebSocket notification for tool: {tool_name}")
        except Exception as e:
            logger.exception(f"Error sending WebSocket notification: {str(e)}")

    def create_session(self, title: str, description: str = "") -> ReasoningSession:
        """
        Create a new reasoning session.

        Args:
            title: Title for the reasoning session
            description: Optional description

        Returns:
            Created ReasoningSession instance
        """
        return ReasoningSession.objects.create(
            project=self.project,
            user=self.project.user,
            title=title,
            description=description
        )

    def execute_step(self, session: ReasoningSession, step_type: str,
                    prompt: str, step_number: Optional[int] = None) -> ReasoningStep:
        """
        Execute a reasoning step using direct OpenAI API calls.

        Args:
            session: ReasoningSession instance
            step_type: Type of reasoning step
            prompt: Prompt for the step
            step_number: Optional step number (auto-incremented if not provided)

        Returns:
            Created ReasoningStep instance with results
        """
        # Determine step number if not provided
        if step_number is None:
            last_step = session.steps.order_by('-step_number').first()
            step_number = 1 if last_step is None else last_step.step_number + 1

        # Create the step record
        step = ReasoningStep.objects.create(
            session=session,
            step_number=step_number,
            step_type=step_type,
            prompt=prompt,
            model_used="gpt-4" if step_type in ["planning", "analysis", "conclusion"] else "gpt-4"
        )

        try:
            # Get the system prompt for this step type
            system_prompt = SYSTEM_PROMPTS.get(step_type, SYSTEM_PROMPTS["planning"])

            # Prepare the messages for the API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            # Make the API request to OpenAI with tools
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # For planning and conclusion steps, use a completely different approach
            # with no tools at all to prevent the model from trying to use tools
            if step_type in ["planning", "conclusion"]:
                # Set up a payload with no tools
                payload = {
                    "model": "gpt-4o",
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 4000
                }

                # Do not include tools or tool_choice in the payload at all
                use_tools = False
                force_tool = False
            else:
                # For all other steps, use tools
                use_tools = True

                # For code generation and execution steps, force tool use
                force_tool = step_type in ["code_generation", "code_execution"]

                # Set up the payload with tools
                payload = {
                    "model": "gpt-4o",
                    "messages": messages,
                    "tools": self.tools,
                    "temperature": 0.2,
                    "max_tokens": 4000
                }

                # Set tool_choice based on step type
                if force_tool:
                    # Force the model to use tools
                    payload["tool_choice"] = "auto"
                else:
                    # Let the model decide whether to use tools
                    payload["tool_choice"] = "auto"

            if step_type in ["planning", "conclusion"]:
                logger.info(f"Sending request to OpenAI with no tools (step type: {step_type})")
            else:
                logger.info(f"Sending request to OpenAI with {len(self.tools)} tools")

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )

            # Check if the request was successful
            if response.status_code != 200:
                error_message = response.json().get('error', {}).get('message', 'Unknown error')
                raise Exception(f"OpenAI API error: {error_message}")

            # Extract the assistant's response
            response_data = response.json()
            assistant_message = response_data['choices'][0]['message']

            # Initialize variables
            content = assistant_message.get('content', '') or ''  # Ensure content is never None
            tool_calls = assistant_message.get('tool_calls', [])
            tool_results = []

            # Process any tool calls
            if tool_calls:
                logger.info(f"Received {len(tool_calls)} tool calls from OpenAI")

                # Create a new message list for follow-up requests
                follow_up_messages = messages.copy()

                for tool_call in tool_calls:
                    function = tool_call.get('function', {})
                    tool_name = function.get('name')
                    arguments_str = function.get('arguments')
                    tool_call_id = tool_call.get('id', 'unknown')

                    try:
                        arguments = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        arguments = {}

                    logger.info(f"Executing tool call: {tool_name} with arguments: {arguments}")

                    # Execute the tool
                    result = self._execute_tool(tool_name, arguments)

                    # Store the result
                    tool_results.append({
                        'name': tool_name,
                        'arguments': arguments,
                        'result': result
                    })

                    # Add tool result to the content
                    tool_result_text = f"\n\n# Tool Result: {result.get('status', 'unknown').upper()}\n"
                    tool_result_text += f"# Tool: {tool_name}\n\n"
                    tool_result_text += f"{result.get('message', 'No message provided')}\n"

                    # Add file path if available
                    if 'file_path' in result:
                        tool_result_text += f"\nFile: {result['file_path']}"

                    # Add stdout if available
                    if 'stdout' in result:
                        tool_result_text += f"\n\nOutput:\n{result['stdout']}"

                    # Add stderr if available
                    if 'stderr' in result and result['stderr']:
                        tool_result_text += f"\n\nErrors:\n{result['stderr']}"

                    content += tool_result_text

                    # Add the tool call and result to the follow-up messages
                    try:
                        # Create a proper tool call message
                        tool_call_message = {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": arguments_str
                                    }
                                }
                            ]
                        }
                        follow_up_messages.append(tool_call_message)

                        # Create a proper tool result message
                        result_content = json.dumps(result)
                        if len(result_content) > 1000:
                            # Truncate long results to avoid token limits
                            result_content = result_content[:1000] + "... (truncated)"

                        tool_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_content
                        }
                        follow_up_messages.append(tool_result_message)

                        logger.info(f"Added tool call and result to follow-up messages: {tool_name}")
                    except Exception as e:
                        logger.exception(f"Error adding tool call to follow-up messages: {str(e)}")

                # Process follow-up requests recursively to handle multiple tool calls
                max_follow_up_rounds = 5  # Limit the number of follow-up rounds to prevent infinite loops
                current_round = 0

                while current_round < max_follow_up_rounds:
                    current_round += 1
                    logger.info(f"Starting follow-up round {current_round}")

                    # Make a follow-up request to process the tool results
                    # For planning and conclusion steps, use a completely different approach
                    if step_type in ["planning", "conclusion"]:
                        # Set up a payload with no tools
                        follow_up_payload = {
                            "model": "gpt-4o",
                            "messages": follow_up_messages,
                            "temperature": 0.2,
                            "max_tokens": 4000
                        }
                    else:
                        # For all other steps, include tools
                        follow_up_payload = {
                            "model": "gpt-4o",
                            "messages": follow_up_messages,
                            "tools": self.tools,
                            "temperature": 0.2,
                            "max_tokens": 4000
                        }

                        # Set tool_choice based on step type and round
                        if force_tool and current_round <= 2:
                            # Force the model to use tools in early rounds
                            follow_up_payload["tool_choice"] = "auto"
                        else:
                            # Let the model decide whether to use tools
                            follow_up_payload["tool_choice"] = "auto"

                    follow_up_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=follow_up_payload
                    )

                    if follow_up_response.status_code == 200:
                        follow_up_data = follow_up_response.json()
                        follow_up_message = follow_up_data['choices'][0]['message']
                        follow_up_content = follow_up_message.get('content', '') or ''
                        follow_up_tool_calls = follow_up_message.get('tool_calls', [])

                        # Add the follow-up content to the original content
                        if follow_up_content:
                            content += f"\n\n# Follow-up Analysis (Round {current_round}):\n{follow_up_content}"

                        # If there are no more tool calls, we're done
                        if not follow_up_tool_calls:
                            logger.info(f"No more tool calls in round {current_round}, finishing")
                            break

                        # Process the new tool calls
                        logger.info(f"Processing {len(follow_up_tool_calls)} new tool calls in round {current_round}")

                        # Add the assistant message with tool calls
                        follow_up_messages.append({
                            "role": "assistant",
                            "content": follow_up_content,
                            "tool_calls": follow_up_tool_calls
                        })

                        # Process each tool call
                        for tool_call in follow_up_tool_calls:
                            function = tool_call.get('function', {})
                            tool_name = function.get('name')
                            arguments_str = function.get('arguments')
                            tool_call_id = tool_call.get('id', 'unknown')

                            try:
                                arguments = json.loads(arguments_str)
                            except json.JSONDecodeError:
                                arguments = {}

                            logger.info(f"Executing follow-up tool call: {tool_name} with arguments: {arguments}")

                            # Execute the tool
                            result = self._execute_tool(tool_name, arguments)

                            # Store the result
                            tool_results.append({
                                'name': tool_name,
                                'arguments': arguments,
                                'result': result
                            })

                            # Add tool result to the content
                            tool_result_text = f"\n\n# Tool Result (Round {current_round}): {result.get('status', 'unknown').upper()}\n"
                            tool_result_text += f"# Tool: {tool_name}\n\n"
                            tool_result_text += f"{result.get('message', 'No message provided')}\n"

                            # Add file path if available
                            if 'file_path' in result:
                                tool_result_text += f"\nFile: {result['file_path']}"

                            # Add stdout if available
                            if 'stdout' in result:
                                tool_result_text += f"\n\nOutput:\n{result['stdout']}"

                            # Add stderr if available
                            if 'stderr' in result and result['stderr']:
                                tool_result_text += f"\n\nErrors:\n{result['stderr']}"

                            content += tool_result_text

                            # Add the tool result to the follow-up messages
                            follow_up_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(result)
                            })
                    else:
                        # If the follow-up request failed, log the error and break
                        error_message = follow_up_response.json().get('error', {}).get('message', 'Unknown error')
                        logger.error(f"Follow-up request failed: {error_message}")
                        content += f"\n\nError in follow-up request: {error_message}"
                        break

                # Add a final summary if we reached the maximum number of rounds
                if current_round >= max_follow_up_rounds:
                    logger.warning(f"Reached maximum number of follow-up rounds ({max_follow_up_rounds})")
                    content += f"\n\nNote: Reached maximum number of follow-up rounds ({max_follow_up_rounds}). Some actions may not have been completed."

            # Update the step with the response and tool calls
            step.response = content
            step.tool_calls = tool_results
            step.is_complete = True
            step.save()

            return step

        except Exception as e:
            logger.exception(f"Error executing reasoning step: {str(e)}")
            step.error = str(e)
            step.save()
            raise

    def execute_reasoning_chain(self, task_description: str,
                               context: Optional[Dict[str, Any]] = None) -> ReasoningSession:
        """
        Execute a full reasoning chain for a task.

        Args:
            task_description: Description of the task to perform
            context: Optional context information (e.g., current file)

        Returns:
            Completed ReasoningSession instance
        """
        # Create a new session
        session = self.create_session(
            title=task_description[:100] + "..." if len(task_description) > 100 else task_description,
            description=task_description
        )

        try:
            # Step 1: Planning
            planning_prompt = f"""Task: {task_description}

Create a detailed plan to accomplish this task.

IMPORTANT: In this planning step, DO NOT actually execute any tools or implement any code. Your job is ONLY to create a plan that will be executed in later steps.

For each step, specify:
1. The goal of the step
2. What files need to be examined or modified
3. What tools might be needed (read_file, write_file, run_file, etc.)

The following tools will be available in later steps, but you should NOT use them now:
- read_file: Read the content of a file in the project
- write_file: Write content to a file in the project
- list_files: List files and directories in a directory
- run_file: Run a file in the project's container
- delete_file: Delete a file or directory in the project
"""
            if context and "current_file" in context:
                planning_prompt += f"\n\nThe user is currently working on: {context['current_file']}"

            planning_step = self.execute_step(session, "planning", planning_prompt)
            plan = planning_step.response

            # Step 2: Code Generation
            code_gen_prompt = f"""Task: {task_description}

Plan: {plan}

Now, implement the code needed for this task. You MUST use the write_file tool to create any necessary files.
DO NOT just describe the code - actually create the files using the write_file tool.

For each file you need to create:
1. Determine the appropriate file path and content
2. Use the write_file tool with the file_path and content parameters
3. Verify the file was created successfully by checking the tool result

Example of using the write_file tool:
```
I'll create a Python file that implements the task:

[Tool Call: write_file]
{{
  "file_path": "task_implementation.py",
  "content": "# Your code here\\nprint('Task implemented successfully')"
}}
```

Remember to use proper error handling, comments, and follow best practices for the language you're using.
"""
            code_gen_step = self.execute_step(session, "code_generation", code_gen_prompt)

            # Step 3: Execution (always run this step)
            execution_prompt = f"""Task: {task_description}

Plan: {plan}

Code implementation: {code_gen_step.response}

Now, execute the code you've created. You MUST use the run_file tool to run the appropriate files.
DO NOT just describe how to run the code - actually run it using the run_file tool.

For each file you need to run:
1. Determine the file path to run
2. Use the run_file tool with the file_path parameter
3. Analyze the output to verify it works correctly

Example of using the run_file tool:
```
I'll run the Python file:

[Tool Call: run_file]
{{
  "file_path": "task_implementation.py"
}}
```

If there are any errors or issues:
1. Fix the code using the write_file tool
2. Run it again to verify your fixes worked
"""
            execution_step = self.execute_step(session, "code_execution", execution_prompt)

            # Step 4: Conclusion
            conclusion_prompt = f"""Task: {task_description}

Plan: {plan}

Implementation: {code_gen_step.response}

Execution results: {execution_step.response}

IMPORTANT: In this conclusion step, DO NOT execute any tools. Your job is ONLY to summarize what was accomplished in the previous steps.

Provide a summary of what was accomplished:
1. What files were created or modified
2. What the code does
3. The results of running the code
4. Any issues encountered and how they were resolved

Be concise but comprehensive in your summary.
"""
            # Execute the conclusion step
            self.execute_step(session, "conclusion", conclusion_prompt)

            # Mark session as complete
            session.is_complete = True
            session.save()

            return session

        except Exception as e:
            logger.exception(f"Error in reasoning chain: {str(e)}")
            # Don't mark as complete if there was an error
            return session
