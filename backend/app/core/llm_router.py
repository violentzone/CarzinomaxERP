import litellm
import asyncio

from app.core.log_module import user_log, system_log
from app.core.config import settings


class LlmRouter:
    def __init__(self, user_id: str, function_called: str):
        """
        Llm Router using Litellm
        Args:
            user_id ():
            function_called ():
        """
        # Test connection of user LLM settings in .env
        if not settings.LLM_MODEL:
            raise ValueError('LLM not set')

        # Models can be ""
        asyncio.run(litellm.ahealth_check())

        self.user_id = user_id
        self.function_called = function_called
        self.user_log = user_log(user_id)
        self.system_log = system_log
        self.llm = settings.LLM_MODEL
        self.llm_token = settings.LLM_TOKEN

