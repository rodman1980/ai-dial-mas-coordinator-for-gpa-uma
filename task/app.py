"""
MAS Coordinator Application Entry Point.

This module defines the DIAL application for the Multi-Agent System Coordinator.
It exposes a chat completion endpoint that routes requests to GPA or UMS agents.

Run with: uvicorn task.app:app --port 8055 --host 0.0.0.0
Endpoint: POST /openai/deployments/mas-coordinator/chat/completions
"""

import os

import uvicorn
from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from task.agent import MASCoordinator
from task.logging_config import setup_logging, get_logger

# Configuration from environment with sensible defaults for local development
DIAL_ENDPOINT = os.getenv('DIAL_ENDPOINT', "http://localhost:8080")
DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME', 'gpt-4o')
UMS_AGENT_ENDPOINT = os.getenv('UMS_AGENT_ENDPOINT', "http://localhost:8042")
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

setup_logging(log_level=LOG_LEVEL)
logger = get_logger(__name__)


class MASCoordinatorApplication(ChatCompletion):
    """
    DIAL ChatCompletion implementation for MAS Coordinator.
    
    Handles incoming chat completion requests by delegating to MASCoordinator
    which determines routing between GPA and UMS agents.
    """

    async def chat_completion(self, request: Request, response: Response) -> None:
        """
        Process chat completion request through MAS coordinator.
        
        Creates a single response choice and delegates to coordinator
        for agent routing and response synthesis.
        
        Args:
            request: Incoming DIAL request with messages and headers
            response: DIAL response object for streaming output
        """
        # Create single choice - MAS coordinator always produces one response
        with response.create_single_choice() as choice:
            # Initialize coordinator with configuration
            coordinator = MASCoordinator(
                endpoint=DIAL_ENDPOINT,
                deployment_name=DEPLOYMENT_NAME,
                ums_agent_endpoint=UMS_AGENT_ENDPOINT
            )
            # Delegate request handling - coordinator manages routing and synthesis
            await coordinator.handle_request(choice, request)


# Initialize DIAL application
app = DIALApp()

# Register MAS Coordinator as chat completion endpoint
agent_app = MASCoordinatorApplication()
app.add_chat_completion("mas-coordinator", agent_app)

# Run server when executed directly
if __name__ == "__main__":
    logger.info(f"Starting MAS Coordinator on port 8055")
    logger.info(f"DIAL Endpoint: {DIAL_ENDPOINT}")
    logger.info(f"UMS Agent Endpoint: {UMS_AGENT_ENDPOINT}")
    uvicorn.run(app, port=8055, host="0.0.0.0")


