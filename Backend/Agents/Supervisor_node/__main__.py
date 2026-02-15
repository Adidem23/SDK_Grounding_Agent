from a2a.types import AgentSkill, AgentCapabilities, AgentCard
from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from agent_executor import SupervisorAgentExecutor
import uvicorn

if __name__ == "__main__":

    agent_skill = AgentSkill(
        id="supervisor_decision",
        name="Supervisor Decision Node",
        description=(
            "Entry-point supervisor agent that evaluates user queries, "
            "decides whether orchestration is required, and delegates tasks "
            "to the central coordinator or specialized agents."
        ),
        tags=[
            "supervisor",
            "orchestrator",
            "decision-maker",
            "delegation",
            "control-plane"
        ]
    )


    agent_card = AgentCard(
        name="Supervisor_Agent",
        description=(
            "Supervisor agent responsible for task delegation and final judgment. "
            "Does not execute domain tasks or manage state."
        ),
        url="http://localhost:8004",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(
            streaming=True
        ),
        skills=[agent_skill]
    )

    request_handler = DefaultRequestHandler(
        agent_executor=SupervisorAgentExecutor(),
        task_store=InMemoryTaskStore()
    )

    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )

    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=8004
    )