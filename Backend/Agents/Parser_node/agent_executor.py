from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState
)
from a2a.utils import new_text_artifact
from agent.agent import ParserAgent

class ParserNodeAgentExecutor(AgentExecutor):

    def __init__(self):
        self.agent=ParserAgent()

    async def execute(self, context:RequestContext, event_queue:EventQueue):

        user_query= context.get_user_input()

        package_name=await self.agent.extractPythonModule(user_query)


        # if(package_name):

        #     response=await self.agent.call_mcp_tools(package_name,user_query)

        #     final_answer_node_Prompt=f"""User Query is {user_query} and its retrived SDK Definations are {response}"""

        #     if(response):
                
        #         FINAL_ANSWER_NODE_BASE_URL="http://localhost:8006"

        #         result=await self.agent.delegateTasks(FINAL_ANSWER_NODE_BASE_URL,final_answer_node_Prompt)

                

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                context_id=context.context_id,
                task_id=context.task_id,
                artifact=new_text_artifact(
                    "Parser_agent_answer",
                     str(package_name)
                )

            )
        )

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                context_id=context.context_id,
                task_id=context.task_id,
                status=TaskStatus(state=TaskState.completed),
                final=True
            )
        )

    async def cancel(self, context, event_queue):
        raise Exception('Error Processing Request')
        