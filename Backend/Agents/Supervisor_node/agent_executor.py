import json
from a2a.server.agent_execution import AgentExecutor , RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState
) 
from a2a.utils import new_text_artifact
from agent.agent import SupervisorAgent

class SupervisorAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent=SupervisorAgent()
    
    async def execute(self,context:RequestContext,event_queue:EventQueue):

        PARSER_NODE_URL="http://localhost:8005"
        FINAL_ANSWER_NODE_URL="http://localhost:8006"


        user_query=context.get_user_input()

        response=await self.agent.extractPythonModule(user_query)

        if(response):
            result= await self.agent.delegateTasks(PARSER_NODE_URL,response)
            # JSON_result = json.loads(result)
            # upload_result=await self.agent.uploadSDKSchemaToPinecone(JSON_result)
            # print(upload_result)
            # if(result):
            #     final_answer=await self.agent.delegateTasks(FINAL_ANSWER_NODE_URL,user_query)
            #     print(final_answer)
          
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                context_id=context.context_id,
                task_id=context.task_id,
                artifact=new_text_artifact(
                    "final_answer",
                    str(result)
                ),
            )
        )

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                context_id=context.context_id,
                task_id=context.task_id,
                status=TaskStatus(state=TaskState.completed),
                final=True,
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')