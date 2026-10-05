import json
import traceback
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from starlette import status
from datetime import datetime

from app.ai_service.agents import llm, orchestrator
from app.core.log_module import user_log
from app.models.auth import User
from app.api.common import get_current_user


chatbot_router = APIRouter(prefix='/chatbot', tags=['Chatbot'])


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

@chatbot_router.post('/chatbox/{user_id}', status_code=status.HTTP_200_OK)
async def chatbox(user_id: int, input_message: str, current_user: User = Depends(get_current_user)):
    """
    Webpage agent call this endpoint
    Args:
        user_id: User id sends message to chatbox
        input_message: Text user input
        current_user: Current user sends message to chatbox

    Returns:
        Response of orchestrator agent's last message
    """

    log = user_log(user_id)
    start_time = datetime.now()
    log.info(f'{start_time.strftime('%Y-%m-%d %H:%M:%S')} sends message to chatbox: {input_message}')
    formatted_user_input = {'messages':[{
        'role': 'user', 'content': input_message
    }]}

    async def stream_reply():
        try:
            async for chunk, _metadata in orchestrator.astream(formatted_user_input, stream_mode='messages'):
                yield json.dumps({'type': 'token', 'content': chunk.content}) + '\n'
            yield json.dumps({'type': 'done'}) + '\n'
            log.info(f'Chatbox reply finished, response duration: {str(datetime.now() - start_time)}')
        except Exception:
            log.error(f'Error: {traceback.format_exc()}')
            yield json.dumps({'type': 'error', 'message': 'Error when try to send to LLM'}) + '\n'

    return StreamingResponse(stream_reply(), media_type='application/x-ndjson')
