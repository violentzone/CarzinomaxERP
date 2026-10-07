import json
import traceback
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
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
        payload: New user message plus prior turns; only the last MAX_HISTORY_MESSAGES are kept
        current_user: Current user sends message to chatbox

    Returns:
        NDJSON stream of the orchestrator agent's reply tokens
    """

    log = user_log(str(current_user.id))
    start_time = datetime.now()
    log.info(f'{start_time.strftime('%Y-%m-%d %H:%M:%S')} sends message to chatbox: {payload.message}')
    history = [m.model_dump() for m in payload.history[-MAX_HISTORY_MESSAGES:]]
    formatted_user_input = {'messages': history + [{'role': 'user', 'content': payload.message}]}
    orchestrator = init_orchestrator(current_user.id)
    async def stream_reply():
        try:
            async for chunk, metadata in orchestrator.astream(formatted_user_input, stream_mode='messages'):
                # Only the orchestrator's own model tokens; skip tool results from the tools node
                if metadata.get('langgraph_node') != 'model' or not chunk.content:
                    continue
                yield json.dumps({'type': 'token', 'content': chunk.content}) + '\n'
            yield json.dumps({'type': 'done'}) + '\n'
            log.info(f'Chatbox reply finished, response duration: {str(datetime.now() - start_time)}')
        except Exception:
            log.error(f'Error: {traceback.format_exc()}')
            yield json.dumps({'type': 'error', 'message': 'Error when try to send to LLM'}) + '\n'

    return StreamingResponse(stream_reply(), media_type='application/x-ndjson')
