"""
AI Reasoning module using LangChain with OpenAI o1 and o4 models.
This module provides a framework for sequential reasoning and code generation.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple

from django.conf import settings
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_openai import ChatOpenAI

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

For each step, specify:
1. A clear title that summarizes the step
2. A detailed description of what needs to be done
3. What files need to be examined or modified
4. What tools might be needed (file operations, code execution, etc.)

Be thorough but concise. Focus on creating a practical, step-by-step plan that can be easily followed.
""",

    "analysis": """You are an expert code analyst specialized in understanding codebases.
Examine the provided code carefully and provide insights.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "overview": "Brief overview of the code",
    "structure": "Description of the overall structure and purpose",
    "components": [
        {
            "name": "Component name",
            "purpose": "Purpose of this component",
            "relationships": "How it relates to other components"
        },
        // Additional components...
    ],
    "issues": [
        {
            "description": "Description of the issue",
            "severity": "high/medium/low",
            "recommendation": "Suggested fix"
        },
        // Additional issues...
    ],
    "relevance": "How the code relates to the user's request"
}

Be thorough and precise in your analysis. This will be used to guide further actions.
""",

    "code_generation": """You are an expert software developer specialized in writing high-quality code.
Generate code based on the provided specifications and analysis.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "overview": "Brief overview of what you're implementing",
    "files": [
        {
            "path": "path/to/file.ext",
            "content": "Complete content of the file",
            "description": "Description of what this file does"
        },
        // Additional files...
    ],
    "explanation": "Explanation of how the code works and any important implementation details",
    "next_steps": "Suggested next steps after implementation"
}

Your code should be:
1. Well-structured and organized
2. Properly commented
3. Following best practices for the language/framework
4. Compatible with the existing codebase

Provide complete implementations that can be directly integrated into the project.
""",

    "code_execution": """You are an expert in executing and testing code.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "execution_plan": "Description of how to run the code",
    "expected_outcomes": "What you expect to happen when the code runs",
    "potential_issues": ["List", "of", "potential", "issues"],
    "test_cases": [
        {
            "description": "Description of the test case",
            "input": "Test input",
            "expected_output": "Expected output"
        },
        // Additional test cases...
    ],
    "results": "Interpretation of execution results",
    "recommendations": "Recommendations based on the results"
}

Be precise and focus on practical execution steps.
""",

    "testing": """You are an expert in software testing.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "test_strategy": "Overall testing strategy",
    "test_cases": [
        {
            "name": "Test case name",
            "description": "Description of what this test verifies",
            "input": "Test input",
            "expected_output": "Expected output",
            "edge_case": true/false
        },
        // Additional test cases...
    ],
    "coverage": "Description of test coverage",
    "issues_found": [
        {
            "description": "Description of the issue",
            "severity": "high/medium/low",
            "recommendation": "Suggested fix"
        },
        // Additional issues...
    ],
    "recommendations": "Overall recommendations based on testing"
}

Be thorough and methodical in your approach to testing.
""",

    "refinement": """You are an expert in code refinement and optimization.
Based on the previous steps and feedback, your job is to improve the code.

IMPORTANT: You MUST format your response as a JSON object with the following structure:
{
    "overview": "Overview of refinement approach",
    "improvements": [
        {
            "file": "path/to/file.ext",
            "description": "Description of the improvement",
            "before": "Code snippet before change",
            "after": "Code snippet after change",
            "rationale": "Why this change improves the code"
        },
        // Additional improvements...
    ],
    "overall_impact": "Description of how these changes improve the codebase",
    "future_recommendations": "Suggestions for future improvements"
}

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

Be concise but comprehensive in your summary.
"""
}


class AIReasoning:
    """
    AI Reasoning class using LangChain with OpenAI o1 and o4 models.
    Implements a sequential reasoning approach for code-related tasks.
    """

    def __init__(self, project: Project, api_key: str):
        """
        Initialize the AI Reasoning system.

        Args:
            project: The Django project model instance
            api_key: OpenAI API key
        """
        self.project = project
        self.api_key = api_key

        # Initialize LLMs with direct API key approach
        # This avoids using the client parameter which can cause compatibility issues

        # Initialize LLMs with minimal parameters
        self.llm_o1 = ChatOpenAI(
            model="o1",
            temperature=0,
            api_key=api_key,
            # Explicitly set parameters that might cause issues to None
            http_client=None,
            max_retries=None,
            timeout=None,
            default_headers=None,
            default_query=None,
            # Don't use any parameters that might not be supported
            # across different versions
        )

        self.llm_o4 = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=api_key,
            # Explicitly set parameters that might cause issues to None
            http_client=None,
            max_retries=None,
            timeout=None,
            default_headers=None,
            default_query=None,
        )

        # Initialize file operations
        self.file_ops = FileOperations(project, project.user)

        # Initialize tools
        self.tools = self._create_tools()

    def _create_tools(self) -> List[BaseTool]:
        """
        Create tools for the agent to use.

        Returns:
            List of LangChain tools
        """
        @tool
        def read_file(file_path: str) -> str:
            """
            Read the content of a file in the project.

            Args:
                file_path: Path to the file relative to the project root

            Returns:
                Content of the file as a string
            """
            result = self.file_ops.read_file(file_path)
            if result["status"] == "error":
                raise ValueError(result["message"])
            return result["content"]

        @tool
        def write_file(file_path: str, content: str) -> str:
            """
            Write content to a file in the project.

            Args:
                file_path: Path to the file relative to the project root
                content: Content to write to the file

            Returns:
                Success message
            """
            # Check if file exists
            read_result = self.file_ops.read_file(file_path)
            if read_result["status"] == "success":
                # Update existing file
                result = self.file_ops.update_file(file_path, content)
            else:
                # Create new file
                result = self.file_ops.create_file(file_path, content)

            if result["status"] == "error":
                raise ValueError(result["message"])
            return result["message"]

        @tool
        def list_files(directory_path: str = "") -> str:
            """
            List files and directories in a directory.

            Args:
                directory_path: Path to the directory relative to the project root

            Returns:
                JSON string with directory contents
            """
            result = self.file_ops.list_files(directory_path)
            if result["status"] == "error":
                raise ValueError(result["message"])
            return json.dumps(result["items"], indent=2)

        @tool
        def run_file(file_path: str) -> str:
            """
            Run a file in the project's container.

            Args:
                file_path: Path to the file to run relative to the project root

            Returns:
                Execution results
            """
            result = self.file_ops.run_file(file_path)
            if result["status"] == "error":
                raise ValueError(result["message"])

            output = f"Command: {result['command']}\n\n"
            if result["stdout"]:
                output += f"STDOUT:\n{result['stdout']}\n\n"
            if result["stderr"]:
                output += f"STDERR:\n{result['stderr']}\n\n"
            output += f"Exit code: {result['return_code']}"

            return output

        @tool
        def delete_file(file_path: str) -> str:
            """
            Delete a file or directory in the project.

            Args:
                file_path: Path to the file or directory relative to the project root

            Returns:
                Success message
            """
            result = self.file_ops.delete_file(file_path)
            if result["status"] == "error":
                raise ValueError(result["message"])
            return result["message"]

        return [
            read_file,
            write_file,
            list_files,
            run_file,
            delete_file
        ]

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

    def create_agent(self, step_type: str) -> AgentExecutor:
        """
        Create an agent for a specific reasoning step type.

        Args:
            step_type: Type of reasoning step

        Returns:
            LangChain AgentExecutor
        """
        # Select the appropriate LLM based on step type
        if step_type in ["planning", "analysis", "conclusion"]:
            llm = self.llm_o1  # Use o1 for planning and analysis
        else:
            llm = self.llm_o4  # Use o4 for code generation and execution

        # Get the system prompt for this step type
        system_prompt = SYSTEM_PROMPTS.get(step_type, SYSTEM_PROMPTS["planning"])

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        # Create the agent
        agent = create_openai_tools_agent(llm, self.tools, prompt)

        # Create the agent executor
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )

    def execute_step(self, session: ReasoningSession, step_type: str,
                    prompt: str, step_number: Optional[int] = None) -> ReasoningStep:
        """
        Execute a reasoning step.

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
            model_used="o1" if step_type in ["planning", "analysis", "conclusion"] else "gpt-4o"
        )

        # Send a WebSocket notification that the step has started
        self._send_step_notification(session, step, "started")

        try:
            # Create the agent for this step
            agent = self.create_agent(step_type)

            # Execute the agent
            response = agent.invoke({"input": prompt})

            # Update the step with the response
            step.response = response.get("output", "")
            step.is_complete = True
            step.save()

            # Send a WebSocket notification that the step has completed
            self._send_step_notification(session, step, "completed")

            return step

        except Exception as e:
            logger.exception(f"Error executing reasoning step: {str(e)}")
            step.error = str(e)
            step.save()

            # Send a WebSocket notification that the step has failed
            self._send_step_notification(session, step, "failed", error=str(e))

            raise

    def _send_step_notification(self, session: ReasoningSession, step: ReasoningStep, status: str, error: str = None):
        """
        Send a WebSocket notification about a reasoning step.

        Args:
            session: The reasoning session
            step: The reasoning step
            status: The status of the step (started, completed, failed)
            error: Optional error message
        """
        try:
            # Import here to avoid circular imports
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            # Get the channel layer
            channel_layer = get_channel_layer()

            # Get the project ID
            project_id = session.project.id

            # Prepare step data
            step_data = {
                'id': step.id,
                'step_number': step.step_number,
                'step_type': step.step_type,
                'status': status,
                'model_used': step.model_used,
            }

            # Add response if completed
            if status == 'completed':
                step_data['response'] = step.response

            # Add error if failed
            if status == 'failed' and error:
                step_data['error'] = error

            # Send the notification to the group
            async_to_sync(channel_layer.group_send)(
                f"tools_{project_id}",
                {
                    "type": "reasoning_step",
                    "session_id": session.id,
                    "step": step_data
                }
            )

            logger.info(f"Sent WebSocket notification for reasoning step: {step.step_type} ({status})")
        except Exception as e:
            logger.exception(f"Error sending WebSocket notification for reasoning step: {str(e)}")

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
            title=task_description[:100] + "..." if len(task_description) > 100 else task_description
        )

        try:
            # Step 1: Planning (always executed)
            planning_prompt = f"Task: {task_description}\n\nCreate a detailed plan to accomplish this task."
            if context and "current_file" in context:
                planning_prompt += f"\n\nThe user is currently working on: {context['current_file']}"

            planning_step = self.execute_step(session, "planning", planning_prompt)
            plan = planning_step.response

            # Check if the task is already completed in the planning step
            # Look for indicators that the task was simple and already completed
            task_completed_indicators = [
                "task has been completed",
                "task is now complete",
                "all files have been deleted",
                "file has been deleted",
                "files have been deleted",
                "successfully deleted",
                "deletion complete",
                "task completed"
            ]

            task_already_completed = any(indicator.lower() in plan.lower() for indicator in task_completed_indicators)

            # Determine which steps to execute based on the task description and planning response
            needs_analysis = (context and "current_file" in context and "current_file_content" in context and
                             any(keyword in task_description.lower() for keyword in ["analyze", "examine", "understand", "review"]))

            needs_code_generation = (not task_already_completed and
                                    any(keyword in task_description.lower() for keyword in ["create", "implement", "write", "add", "generate"]))

            needs_testing = (not task_already_completed and
                            any(keyword in task_description.lower() for keyword in ["run", "execute", "test"]))

            needs_refinement = (not task_already_completed and
                               any(keyword in task_description.lower() for keyword in ["improve", "optimize", "refactor"]))

            # Step 2: Analysis (if needed)
            if needs_analysis:
                analysis_prompt = f"""
                Task: {task_description}

                Plan: {plan}

                Current file: {context['current_file']}

                File content:
                ```
                {context['current_file_content']}
                ```

                Analyze this code in relation to the task.
                """
                analysis_step = self.execute_step(session, "analysis", analysis_prompt)
                analysis = analysis_step.response
            else:
                # Skip analysis if not needed
                analysis = "No analysis needed for this task."

            # Step 3: Code Generation (if needed)
            if needs_code_generation:
                code_gen_prompt = f"""
                Task: {task_description}

                Plan: {plan}

                Analysis: {analysis}

                Generate the necessary code to implement this task. Use the available tools to read, write, or execute files as needed.
                """
                code_gen_step = self.execute_step(session, "code_generation", code_gen_prompt)
                code_implementation = code_gen_step.response
            else:
                # Skip code generation if not needed
                code_implementation = "No code generation needed for this task."

            # Step 4: Testing/Execution (if needed)
            if needs_testing:
                testing_prompt = f"""
                Task: {task_description}

                Plan: {plan}

                Code implementation: {code_implementation}

                Test the implementation and verify it works correctly. Use the run_file tool if needed.
                """
                testing_step = self.execute_step(session, "testing", testing_prompt)

            # Step 5: Refinement (if needed)
            if needs_refinement:
                refinement_prompt = f"""
                Task: {task_description}

                Plan: {plan}

                Code implementation: {code_implementation}

                Refine and optimize the implementation. Make any necessary improvements.
                """
                refinement_step = self.execute_step(session, "refinement", refinement_prompt)

            # Step 6: Conclusion (always executed)
            conclusion_prompt = f"""
            Task: {task_description}

            Plan: {plan}

            {f"Implementation: {code_implementation}" if needs_code_generation else ""}

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
