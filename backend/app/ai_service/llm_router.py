import traceback

import litellm
import asyncio

from app.core.log_module import user_log, system_log
from app.core.config import settings


class LlmException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class LlmRouter:
    def __init__(self, user_id: str, function_called: str):
        """
        Llm Router using Litellm
        Args:
            user_id ():
            function_called ():
        """
        self.llm_log = user_log(user_id)
        try:
            asyncio.run(self.model_check())
        except Exception as e:
            self.llm_log.error(traceback.format_exc())
            raise LlmException(str(e))

        self.user_id = user_id
        self.function_called = function_called
        self.user_log = user_log(user_id)
        self.system_log = system_log
        self.llm = settings.LLM_MODEL
        self.llm_token = settings.LLM_TOKEN

    @staticmethod
    async def model_check() -> None:
        """
        Check model connection set in .env
        Returns:
            None, raises error if connection fails
        """
        # None API calling checks
        if not settings.LLM_MODEL or not settings.LLM_TYPE:
            raise ValueError('LLM not set, both LLM_MODEL and LLM_TYPE should be set')
        elif settings.LLM_TYPE == 'local':
            if not settings.LLM_API_BASE:
                raise ValueError('LLM_API_BASE set')


        # LiteLLM `ahealth_check`
        model_conf = {
            "model": settings.LLM_MODEL,
            "api_key": settings.LLM_API_KEY,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "timeout": 30}
        if settings.LLM_TYPE == 'local':
            model_conf.update({'api_base': settings.LLM_API_BASE})
        llm_check_result = await litellm.ahealth_check(model_conf)
        if 'error' in llm_check_result:
            raise RuntimeError(llm_check_result)