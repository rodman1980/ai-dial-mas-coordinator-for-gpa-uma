"""
MAS Coordinator Agent - Routes requests between GPA and UMS agents.

Execution Flow:
1. Receive user request via handle_request()
2. Open "Coordination" stage and call LLM to determine routing (GPA vs UMS)
3. Parse LLM response into CoordinationRequest (agent_name + instructions)
4. Route to appropriate agent gateway (GPAGateway or UMSAgentGateway)
5. Agent processes request and streams response to nested stage
6. Call LLM again to synthesize final user-friendly response
7. Stream final response to choice

External I/O: LLM calls via AsyncDial, agent calls via gateways
Side Effects: Opens/closes stages, streams content to choice
"""

import json
from copy import deepcopy
from typing import Any

from aidial_client import AsyncDial
from aidial_sdk.chat_completion import Role, Choice, Request, Message, Stage
from pydantic import StrictStr

from task.coordination.gpa import GPAGateway
from task.coordination.ums_agent import UMSAgentGateway
from task.logging_config import get_logger
from task.models import CoordinationRequest, AgentName
from task.prompts import COORDINATION_REQUEST_SYSTEM_PROMPT, FINAL_RESPONSE_SYSTEM_PROMPT
from task.stage_util import StageProcessor

logger = get_logger(__name__)


class MASCoordinator:
    """
    Multi-Agent System Coordinator that routes user requests to specialized agents.
    
    Acts as an intelligent router:
    - Analyzes user intent via LLM
    - Delegates to GPA (general tasks) or UMS (user management)
    - Synthesizes final response from agent output
    """

    def __init__(self, endpoint: str, deployment_name: str, ums_agent_endpoint: str):
        """
        Initialize coordinator with required endpoints.
        
        Args:
            endpoint: DIAL Core endpoint for LLM calls
            deployment_name: LLM model deployment name (e.g., 'gpt-4o')
            ums_agent_endpoint: UMS Agent base URL
        """
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.ums_agent_endpoint = ums_agent_endpoint

    async def handle_request(self, choice: Choice, request: Request) -> Message:
        """
        Main entry point - orchestrate the full request handling flow.
        
        Flow:
        1. Create AsyncDial client for LLM calls
        2. Open coordination stage and determine routing
        3. Delegate to appropriate agent
        4. Synthesize final response
        
        Args:
            choice: DIAL choice for streaming response
            request: User request with message history
            
        Returns:
            Final assistant message
        """
        # Step 1: Initialize DIAL client for LLM calls
        client = AsyncDial(base_url=self.endpoint, api_version='2025-01-01-preview')

        # Step 2: Routing decision - determine which agent handles this request
        coordination_stage = StageProcessor.open_stage(choice, "🧭 Coordination")
        coordination_request = await self.__prepare_coordination_request(client, request)
        
        # Log routing decision to stage and close it
        coordination_stage.append_content(
            f"Routing to: **{coordination_request.agent_name}**\n"
            f"Instructions: {coordination_request.additional_instructions or 'None'}"
        )
        StageProcessor.close_stage_safely(coordination_stage)
        logger.info(f"Routing decision: {coordination_request}")

        # Step 3: Open agent stage and delegate to appropriate agent
        agent_stage = StageProcessor.open_stage(choice, f"🤖 {coordination_request.agent_name} Agent")
        agent_message = await self.__handle_coordination_request(
            coordination_request, choice, agent_stage, request
        )
        StageProcessor.close_stage_safely(agent_stage)

        # Step 4: Synthesize final response from agent output
        final_message = await self.__final_response(client, choice, request, agent_message)
        
        return final_message

    async def __prepare_coordination_request(self, client: AsyncDial, request: Request) -> CoordinationRequest:
        """
        Call LLM to determine which agent should handle the request.
        
        Uses structured output (JSON schema) to ensure valid response format.
        
        Args:
            client: AsyncDial client for LLM call
            request: User request for context
            
        Returns:
            CoordinationRequest with agent_name and optional instructions
        """
        messages = self.__prepare_messages(request, COORDINATION_REQUEST_SYSTEM_PROMPT)

        # Use JSON schema response format for structured output
        response = await client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            extra_body={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "schema": CoordinationRequest.model_json_schema()
                    }
                }
            }
        )

        # Parse structured response
        content = response.choices[0].message.content
        data = json.loads(content)
        return CoordinationRequest.model_validate(data)

    def __prepare_messages(self, request: Request, system_prompt: str) -> list[dict[str, Any]]:
        """
        Convert request messages to LLM-ready format with system prompt.
        
        Handles DIAL-specific custom_content by extracting only the text content
        for user messages (custom_content may contain attachments, state, etc.).
        
        Args:
            request: Original request with message history
            system_prompt: System prompt for LLM role
            
        Returns:
            List of message dicts for LLM API
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        for msg in request.messages:
            if msg.role == Role.USER and msg.custom_content:
                # For user messages with custom_content, only include text content
                # (skip attachments, state, stages that are DIAL-specific)
                messages.append({"role": "user", "content": msg.content or ""})
            else:
                # Standard message - use dict serialization (deprecated but DIAL-compatible)
                messages.append(msg.dict(exclude_none=True))

        return messages

    async def __handle_coordination_request(
            self,
            coordination_request: CoordinationRequest,
            choice: Choice,
            stage: Stage,
            request: Request
    ) -> Message:
        """
        Route request to the appropriate agent based on coordination decision.
        
        Args:
            coordination_request: Routing decision from LLM
            choice: DIAL choice for state/attachments
            stage: Stage for agent response streaming
            request: Original user request
            
        Returns:
            Agent's response message
        """
        if coordination_request.agent_name == AgentName.UMS:
            # Route to Users Management Service Agent
            gateway = UMSAgentGateway(self.ums_agent_endpoint)
            return await gateway.response(
                choice, stage, request, coordination_request.additional_instructions
            )
        else:
            # Route to General-Purpose Agent (default)
            gateway = GPAGateway(self.endpoint)
            return await gateway.response(
                choice, stage, request, coordination_request.additional_instructions
            )

    async def __final_response(
            self,
            client: AsyncDial,
            choice: Choice,
            request: Request,
            agent_message: Message
    ) -> Message:
        """
        Synthesize agent output into a polished user response.
        
        Augments the conversation with agent's response as context,
        then streams LLM's synthesized response to the user.
        
        Args:
            client: AsyncDial client for LLM call
            choice: DIAL choice for streaming
            request: Original request for context
            agent_message: Response from delegated agent
            
        Returns:
            Final synthesized message
        """
        # Prepare messages with synthesis prompt
        messages = self.__prepare_messages(request, FINAL_RESPONSE_SYSTEM_PROMPT)

        # Augment last user message with agent's response as context
        if messages:
            last_msg = messages[-1]
            original_content = last_msg.get('content', '')
            augmented_content = (
                f"## Original User Request\n{original_content}\n\n"
                f"## Agent Response\n{agent_message.content or ''}"
            )
            last_msg['content'] = augmented_content

        # Stream final response
        stream = await client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            stream=True
        )

        content = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                chunk_content = chunk.choices[0].delta.content
                content += chunk_content
                choice.append_content(chunk_content)

        return Message(role=Role.ASSISTANT, content=content)

