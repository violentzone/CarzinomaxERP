import json
import traceback
from uuid import uuid4
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.types import Command
from starlette import status
from datetime import datetime

from app.ai_service.agents import llm, init_orchestrator
from app.core.log_module import user_log
from app.models.auth import User
from app.schemas.chatbot import ChatboxRequest
from app.api.common import get_current_user


chatbot_router = APIRouter(prefix='/chatbot', tags=['Chatbot'])

MAX_HISTORY_MESSAGES = 10  # 5 turns: 5 user + 5 assistant messages


@chatbot_router.post('/', status_code=status.HTTP_200_OK)
async def health_check(user_id: int):
    log = user_log(user_id)
    start_time = datetime.now()
    log.info(f'{start_time.strftime('%Y-%m-%d %H:%M:%S')} checks chatbot health')
    try:
        await llm.ainvoke('ping', max_tokens=1, timeout=10)
        response = JSONResponse(content={'live': True, 'message': ''})
        response_time = datetime.now()
        duration = response_time - start_time
        log.info(f'Chatbot is alive, response duration: {str(duration)}')
    except Exception as e:
        response = JSONResponse(content={'live': False, 'message': 'LLM agent is not responding, make sure all settings in system env is correct'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        log.error(f'Error: {traceback.format_exc()}')
    return response

@chatbot_router.post('/chatbox', status_code=status.HTTP_200_OK)
async def chatbox(payload: ChatboxRequest, current_user: User = Depends(get_current_user)):
    """
    Webpage agent call this endpoint
    Args:
        payload: New user message (or a decision on a pending approval) plus prior turns; only the last MAX_HISTORY_MESSAGES are kept
        current_user: Current user sends message to chatbox

    Returns:
        NDJSON stream of the orchestrator agent's reply tokens; an `interrupt` event means a delete is waiting for `decision`
    """

    log = user_log(str(current_user.id))
    start_time = datetime.now()
    if not payload.message and payload.decision is None:
        return JSONResponse({'status': 'fail', 'error': 'Either message or decision is required'}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

    # Thread is prefixed with the caller's id so nobody can resume another user's paused run
    thread_id = payload.thread_id or str(uuid4())
    config = {'configurable': {'thread_id': f'{current_user.id}:{thread_id}'}}
    orchestrator = init_orchestrator(current_user.id)
    state = await orchestrator.aget_state(config)
    pending_actions = sum(len(i.value['action_requests']) for i in state.interrupts)

    if payload.decision is not None:
        if not pending_actions:
            return JSONResponse({'status': 'fail', 'error': 'No approval is pending on this conversation'}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        log.info(f'{start_time.strftime('%Y-%m-%d %H:%M:%S')} answers pending approval with: {payload.decision}')
        graph_input = Command(resume={'decisions': [{'type': payload.decision}] * pending_actions})
    else:
        if pending_actions:
            return JSONResponse({'status': 'fail', 'error': 'An approval is pending; approve or reject it first'}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        log.info(f'{start_time.strftime('%Y-%m-%d %H:%M:%S')} sends message to chatbox: {payload.message}')
        if state.values.get('messages'):
            # The checkpoint already holds this conversation; only the new turn is needed
            graph_input = {'messages': [{'role': 'user', 'content': payload.message}]}
        else:
            # Fresh thread (or backend restarted): rebuild from the client's history
            history = [m.model_dump() for m in payload.history[-MAX_HISTORY_MESSAGES:]]
            graph_input = {'messages': history + [{'role': 'user', 'content': payload.message}]}

    async def stream_reply():
        try:
            async for mode, chunk in orchestrator.astream(graph_input, config=config, stream_mode=['messages', 'updates']):
                if mode == 'updates':
                    if '__interrupt__' in chunk:
                        actions = [
                            {'name': a['name'], 'args': a['args'], 'description': a.get('description', '')}
                            for interrupt in chunk['__interrupt__'] for a in interrupt.value['action_requests']
                        ]
                        log.info(f'Chatbox paused for approval: {[a["name"] for a in actions]}')
                        yield json.dumps({'type': 'interrupt', 'actions': actions}) + '\n'
                    continue
                message, metadata = chunk
                # Only the orchestrator's own model tokens; skip tool results and the sub-agents' nested model calls
                if metadata.get('langgraph_node') != 'model' or '|' in metadata.get('langgraph_checkpoint_ns', '') or not message.content:
                    continue
                yield json.dumps({'type': 'token', 'content': message.content}) + '\n'
            yield json.dumps({'type': 'done'}) + '\n'
            log.info(f'Chatbox reply finished, response duration: {str(datetime.now() - start_time)}')
        except Exception:
            log.error(f'Error: {traceback.format_exc()}')
            yield json.dumps({'type': 'error', 'message': 'Error when try to send to LLM'}) + '\n'

    return StreamingResponse(stream_reply(), media_type='application/x-ndjson')
