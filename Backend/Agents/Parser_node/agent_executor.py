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

        package_name= context.get_user_input()

        response=await self.agent.call_mcp_tools(package_name)
        
        if(response):
            result=await self.agent.uploadSDKSchemaToPinecone(response)

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                context_id=context.context_id,
                task_id=context.task_id,
                artifact=new_text_artifact(
                    "Parser_agent_answer",
                     str(result)
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
        