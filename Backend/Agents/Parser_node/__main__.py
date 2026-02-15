from a2a.types import AgentSkill, AgentCapabilities, AgentCard
from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from agent_executor import ParserNodeAgentExecutor
import uvicorn


if __name__ == "__main__":


    parser_skill = AgentSkill(
        id="sdk_schema_parser",
        name="SDK Schema Parser Node",
        description=(
            "Parses and extracts structured SDK schema for a validated "
            "Python package using the SDKGroundingEngine."
        ),
        tags=[
            "parser",
            "sdk",
            "schema",
            "grounding",
            "dependency-analysis"
        ]
    )

    agent_card = AgentCard(
        name="Parser_Agent",
        description=(
            "Parser node responsible for extracting structured SDK schema "
            "from Python packages. Does not generate code or perform reasoning."
        ),
        url="http://localhost:8005",  
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["json"],
        capabilities=AgentCapabilities(
            streaming=True
        ),
        skills=[parser_skill]
    )

   
    request_handler = DefaultRequestHandler(
        agent_executor=ParserNodeAgentExecutor(),
        task_store=InMemoryTaskStore()
    )


    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )

    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=8005
    )
