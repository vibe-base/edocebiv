"""
A simplified version of the AI reasoning module that uses direct API calls instead of LangChain.
This is a fallback for when the LangChain integration has compatibility issues.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional

from django.conf import settings

from .models import Project, ReasoningSession, ReasoningStep
from .file_operations import FileOperations

logger = logging.getLogger(__name__)

# System prompts for different reasoning steps
SYSTEM_PROMPTS = {
    "planning": """You are an expert software developer and AI assistant specialized in planning coding tasks.
Your job is to break down complex coding tasks into clear, actionable steps.
For each step, specify:
1. The goal of the step
2. What files need to be examined or modified
3. What tools might be needed (file operations, code execution, etc.)

Be thorough but concise. Focus on creating a practical, step-by-step plan that another AI can follow.
""",

    "analysis": """You are an expert code analyst specialized in understanding codebases.
Examine the provided code carefully and provide insights on:
1. The overall structure and purpose
2. Key components and their relationships
3. Potential issues or areas for improvement
4. How the code relates to the user's request

Be thorough and precise in your analysis. This will be used to guide further actions.
""",

    "code_generation": """You are an expert software developer specialized in writing high-quality code.
Generate code based on the provided specifications and analysis.
Your code should be:
1. Well-structured and organized
2. Properly commented
3. Following best practices for the language/framework
4. Compatible with the existing codebase

Provide complete implementations that can be directly integrated into the project.
""",

    "code_execution": """You are an expert in executing and testing code.
Your job is to:
1. Determine how to run the provided code
2. Predict potential outcomes or issues
3. Suggest appropriate test cases
4. Interpret execution results

Be precise and focus on practical execution steps.
""",

    "testing": """You are an expert in software testing.
Your job is to:
1. Design appropriate test cases for the code
2. Identify edge cases and potential issues
3. Verify that the code meets requirements
4. Suggest improvements based on test results

Be thorough and methodical in your approach to testing.
""",

    "refinement": """You are an expert in code refinement and optimization.
Based on the previous steps and feedback, your job is to:
1. Identify areas for improvement in the code
2. Suggest specific optimizations or refactorings
3. Address any issues or bugs discovered
4. Enhance the code's readability, performance, or maintainability

Provide specific, actionable improvements.
""",

    "conclusion": """You are an expert in summarizing development work.
Your job is to:
1. Summarize what has been accomplished
2. Highlight key changes or improvements made
3. Note any remaining issues or future work
4. Provide a clear conclusion to the reasoning session

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
        if tool_name == "read_file":
            return self.file_ops.read_file(arguments["file_path"])
        elif tool_name == "write_file":
            # Check if file exists
            read_result = self.file_ops.read_file(arguments["file_path"])
            if read_result["status"] == "success":
                # Update existing file
                return self.file_ops.update_file(arguments["file_path"], arguments["content"])
            else:
                # Create new file
                return self.file_ops.create_file(arguments["file_path"], arguments["content"])
        elif tool_name == "list_files":
            directory_path = arguments.get("directory_path", "")
            return self.file_ops.list_files(directory_path)
        elif tool_name == "run_file":
            return self.file_ops.run_file(arguments["file_path"])
        elif tool_name == "delete_file":
            return self.file_ops.delete_file(arguments["file_path"])
        else:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

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

            payload = {
                "model": "gpt-4",
                "messages": messages,
                "tools": self.tools,
                "tool_choice": "auto",  # Let the model decide when to use tools
                "temperature": 0.2,
                "max_tokens": 4000
            }

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
            content = assistant_message.get('content', '')
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
                    follow_up_messages.append({
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
                    })

                    # Add the tool result to the follow-up messages
                    follow_up_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(result)
                    })

                # Make a follow-up request to process the tool results
                follow_up_payload = {
                    "model": "gpt-4",
                    "messages": follow_up_messages,
                    "temperature": 0.2,
                    "max_tokens": 4000
                }

                follow_up_response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=follow_up_payload
                )

                if follow_up_response.status_code == 200:
                    follow_up_data = follow_up_response.json()
                    follow_up_message = follow_up_data['choices'][0]['message']
                    follow_up_content = follow_up_message.get('content', '')

                    # Add the follow-up content to the original content
                    content += f"\n\n# Follow-up Analysis:\n{follow_up_content}"

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
            planning_prompt = f"Task: {task_description}\n\nCreate a detailed plan to accomplish this task."
            if context and "current_file" in context:
                planning_prompt += f"\n\nThe user is currently working on: {context['current_file']}"

            planning_step = self.execute_step(session, "planning", planning_prompt)
            plan = planning_step.response

            # Step 2: Code Generation
            code_gen_prompt = f"""
            Task: {task_description}

            Plan: {plan}

            Generate the necessary code to implement this task. Use the available tools to read, write, or execute files as needed.
            """
            code_gen_step = self.execute_step(session, "code_generation", code_gen_prompt)

            # Step 3: Testing/Execution (if applicable)
            if "run" in task_description.lower() or "test" in task_description.lower():
                testing_prompt = f"""
                Task: {task_description}

                Plan: {plan}

                Code implementation: {code_gen_step.response}

                Test the implementation and verify it works correctly. Use the run_file tool if needed.
                """
                testing_step = self.execute_step(session, "testing", testing_prompt)

            # Step 4: Conclusion
            conclusion_prompt = f"""
            Task: {task_description}

            Plan: {plan}

            Implementation: {code_gen_step.response}

            Provide a summary of what was accomplished and any next steps or recommendations.
            """
            conclusion_step = self.execute_step(session, "conclusion", conclusion_prompt)

            # Mark session as complete
            session.is_complete = True
            session.save()

            return session

        except Exception as e:
            logger.exception(f"Error in reasoning chain: {str(e)}")
            # Don't mark as complete if there was an error
            return session
