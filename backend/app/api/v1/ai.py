from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from starlette import status

from app.ai_service.agents import llm, orchestrator
from app.core.log_module import user_log


router = APIRouter(prefix='/ai', tags=['AI'])


@router.post('/', status_code=status.HTTP_200_OK)
async def health_check():
    try:
        await llm.ainvoke('ping', max_tokens=1, timeout=10)
        response = Response(content={'live': True, 'message': ''})
    except Exception as e:
        response = Response(content={'live': False, 'message': str(e)})

    return response

@router.post('/chatbox/{user_id}', status_code=status.HTTP_200_OK)
async def chatbox(user_id: int, input_message: str):
    """
    Webpage agent call this endpoint
    Args:
        user_id: User id sends message to chatbox
        input_message: Text user input

    Returns:
        Response of orchestrator agent's last message
    """

    formatted_user_input = {'messages':[{
        'role': 'user', 'content': input_message
    }]}
    try:
        async for chunk, _metadata in orchestrator.astream(formatted_user_input, stream_mode='messages'):
            