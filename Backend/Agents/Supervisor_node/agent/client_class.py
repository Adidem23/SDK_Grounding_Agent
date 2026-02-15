import httpx
import json
from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
    create_text_message_object
)
from a2a.types import TransportProtocol
from a2a.utils.message import get_message_text
from langchain_core.messages import ToolMessage


class Agent_Client_Class:

    async def create_connection(self, url: str, user_input: str):

        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=url
            )

            agent_card = await resolver.get_agent_card()

            config = ClientConfig(
                httpx_client=httpx_client,
                supported_transports=[TransportProtocol.jsonrpc,TransportProtocol.http_json],
                streaming=agent_card.capabilities.streaming,
            )

            client = ClientFactory(config).create(agent_card)

            request = create_text_message_object(content=user_input)

            result=None
            
            async for response in client.send_message(request):
                task, _ = response

                if task.artifacts:
                    result = get_message_text(task.artifacts[-1])

                for artifact in task.artifacts or []:
                    for part in artifact.parts:
                        root = part.root
                        if isinstance(root, ToolMessage):
                            payload = json.loads(root.content)
                            for item in payload:
                                if item.get("type") == "text":
                                    result=item["text"]
                                    

            return result