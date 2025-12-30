"""
UMS Agent Gateway - Interface to the Users Management Service Agent.

Execution Flow:
1. Check for existing UMS conversation ID in message history state
2. If no conversation exists, create one via POST to /conversations
3. Augment user message with additional instructions if provided
4. Stream response from UMS agent, parsing SSE format (data: {...})
5. Return assistant message and persist conversation ID in choice state

External I/O: HTTP calls to UMS agent endpoint (create conversation, chat)
Error Handling: Relies on httpx exceptions; streaming parse errors will propagate
"""

import json
from typing import Optional

import httpx
from aidial_sdk.chat_completion import Role, Request, Message, Stage, Choice
from pydantic import StrictStr


_UMS_CONVERSATION_ID = "ums_conversation_id"


class UMSAgentGateway:
    """
    Gateway for communicating with the UMS (Users Management Service) Agent.
    Handles conversation lifecycle and streaming responses.
    """

    def __init__(self, ums_agent_endpoint: str):
        """
        Initialize gateway with UMS agent base URL.
        
        Args:
            ums_agent_endpoint: Base URL of UMS agent (e.g., http://localhost:8042)
        """
        self.ums_agent_endpoint = ums_agent_endpoint

    async def response(
            self,
            choice: Choice,
            stage: Stage,
            request: Request,
            additional_instructions: Optional[str]
    ) -> Message:
        """
        Send user request to UMS Agent and stream the response.
        
        Flow:
        1. Retrieve or create UMS conversation (UMS tracks its own conversation state)
        2. Augment last user message with coordinator instructions
        3. Call UMS agent with streaming enabled
        4. Persist conversation ID for future requests
        
        Args:
            choice: DIAL choice to store state
            stage: Stage to append streamed content
            request: Original user request with message history
            additional_instructions: Optional context from coordinator
            
        Returns:
            Assistant message with UMS agent's response
        """
        # Step 1: Get or create conversation - UMS agent maintains its own conversation history
        conversation_id = self.__get_ums_conversation_id(request)
        if conversation_id is None:
            conversation_id = await self.__create_ums_conversation()
            # Persist conversation ID in choice state for future requests
            choice.set_state({_UMS_CONVERSATION_ID: conversation_id})

        # Step 2: Get last user message and augment with instructions
        last_message = request.messages[-1]
        user_content = last_message.content or ""
        if additional_instructions:
            user_content = f"{user_content}\n\nAdditional context: {additional_instructions}"

        # Step 3: Call UMS agent and stream response
        response_content = await self.__call_ums_agent(conversation_id, user_content, stage)

        # Step 4: Return assistant message
        return Message(role=Role.ASSISTANT, content=response_content)

    def __get_ums_conversation_id(self, request: Request) -> Optional[str]:
        """
        Extract UMS conversation ID from previous assistant messages' state.
        
        UMS agent maintains its own conversation tracking, so we store its
        conversation ID in our message state to maintain continuity.
        
        Args:
            request: Request containing message history
            
        Returns:
            Conversation ID if found in history, None otherwise
        """
        for message in request.messages:
            # Check assistant messages for stored UMS conversation state
            if message.role == Role.ASSISTANT and message.custom_content:
                state = message.custom_content.state
                if state and _UMS_CONVERSATION_ID in state:
                    return state[_UMS_CONVERSATION_ID]
        return None

    async def __create_ums_conversation(self) -> str:
        """
        Create a new conversation on UMS agent side.
        
        External I/O: POST to {ums_agent_endpoint}/conversations
        
        Returns:
            New conversation ID from UMS agent
            
        Raises:
            httpx.HTTPError: On network/HTTP failures
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.ums_agent_endpoint}/conversations")
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def __call_ums_agent(
            self,
            conversation_id: str,
            user_message: str,
            stage: Stage
    ) -> str:
        """
        Call UMS agent and stream the response, appending chunks to stage.
        
        Streaming Format (SSE-like):
            data: {'choices': [{'delta': {'content': 'chunk'}}]}
            data: {'conversation_id': '...'}
            data: [DONE]
        
        Args:
            conversation_id: UMS conversation to continue
            user_message: User's message content
            stage: Stage to append content chunks for real-time display
            
        Returns:
            Complete accumulated response content
            
        Raises:
            httpx.HTTPError: On network/HTTP failures
            json.JSONDecodeError: On malformed streaming chunks
        """
        accumulated_content = ""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Stream request to UMS agent chat endpoint
            async with client.stream(
                "POST",
                f"{self.ums_agent_endpoint}/conversations/{conversation_id}/chat",
                json={
                    "message": {"role": "user", "content": user_message},
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                
                # Parse SSE-style streaming response
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # Strip 'data: ' prefix from SSE format
                    if line.startswith("data: "):
                        line = line[6:]  # Remove 'data: ' prefix
                    
                    # Check for stream termination
                    if line == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(line)
                        
                        # Extract content from OpenAI-compatible delta format
                        if "choices" in chunk_data:
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                accumulated_content += content
                                # Append to stage for real-time display in UI
                                stage.append_content(content)
                    except json.JSONDecodeError:
                        # Skip non-JSON lines (e.g., conversation_id metadata)
                        continue
        
        return accumulated_content
