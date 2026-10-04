"""
Chatbot module, health check for the agent LLM backend.
"""
from time import perf_counter
from traceback import format_exc

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse as Response
from langchain_core.messages import AIMessage, HumanMessage
from starlette import status

from app.ai_service.agents import llm
from app.api.common import get_current_user
from app.core.config import settings
from app.core.log_module import user_log
from app.models import User

chatbot_router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@chatbot_router.get('/health_check')
async def health_check(current_user: User = Depends(get_current_user)):
    """
    Ping the configured LLM with a one-token request and verify the reply.
    Args:
        current_user: Signed in user

    Returns:
        `{"status": "success", "data": {...}}` with model, latency and token usage when the LLM
        answers, or `{"status": "fail", "error": "..."}` with 503 when it does not.
    """
    log = user_log(current_user.id)
    log.info(f'Chatbot health check against {settings.LLM_MODEL}')
    started = perf_counter()
    try:
        reply = await llm.ainvoke([HumanMessage(content='ping')], max_tokens=1)
    except Exception as e:
        log.error(f'Chatbot health check failed: {e}\n{format_exc()}')
        return Response({"status": "fail", "error": f"LLM unreachable: {e}"},
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type='application/json')
    latency_ms = round((perf_counter() - started) * 1000)

    checks = {}
    if not isinstance(reply, AIMessage):
        checks['unexpected_reply_type'] = type(reply).__name__
    usage = reply.usage_metadata or {}
    output_tokens = usage.get('output_tokens')
    if output_tokens is None:
        checks['missing_usage_metadata'] = 'provider returned no token usage'
    elif output_tokens > 1:
        checks['max_tokens_ignored'] = f'requested 1 output token, provider returned {output_tokens}'
    if output_tokens == 0 and not (reply.content or '').strip():
        checks['empty_reply'] = 'provider returned no tokens and no content'

    data = {
        'model': settings.LLM_MODEL,
        'llm_type': settings.LLM_TYPE,
        'latency_ms': latency_ms,
        'max_tokens': 1,
        'output_tokens': output_tokens,
        'input_tokens': usage.get('input_tokens'),
        'reply': reply.content if isinstance(reply.content, str) else str(reply.content),
    }
    if checks:
        log.warning(f'Chatbot health check degraded: {checks}')
        return Response({"status": "fail", "error": "LLM answered but failed checks", "data": data, "checks": checks},
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, media_type='application/json')
    log.info(f'Chatbot health check ok in {latency_ms} ms')
    return Response({"status": "success", "data": data}, status_code=status.HTTP_200_OK, media_type='application/json')
