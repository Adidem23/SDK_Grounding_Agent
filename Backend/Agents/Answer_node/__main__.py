from a2a.types import AgentSkill, AgentCapabilities, AgentCard
from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from agent_executor import FinalAnswerNodeAgent
import uvicorn
import os


if __name__ == "__main__":

    generator_skill = AgentSkill(
        id="final_answer_generation",
        name="Final Answer Generation Node",
        description=(
            "Generates the final response or code output for the user "
            "based on validated SDK schema and user query."
        ),
        tags=[
            "generator",
            "code-generation",
            "llm",
            "final-response",
            "output-layer"
        ]
    )


    agent_card = AgentCard(
        name="Final_Answer_Agent",
        description=(
            "Final answer agent responsible for generating user-facing "
            "code or responses using grounded SDK schema. "
            "Does not perform delegation or schema extraction."
        ),
        url="http://localhost:8006",  
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(
            streaming=True
        ),
        skills=[generator_skill]
    )


    request_handler = DefaultRequestHandler(
        agent_executor=FinalAnswerNodeAgent(),
        task_store=InMemoryTaskStore()
    )

 
    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )

    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=8006
    )
