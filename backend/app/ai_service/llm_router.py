import traceback
from pydantic import BaseModel
import litellm

from app.core.log_module import user_log, system_log
from app.core.config import settings


class LlmException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class LlmRouter:
    def __init__(self, user_id: str, function_called: str):
        """
        Llm Router using Litellm.
        Connection is verified once at app startup via `LlmRouter.model_check()`.
        Args:
            user_id (): User the requests are logged under
            function_called (): Name of the calling feature, for logging
        """
        self.model = settings.LLM_MODEL
        self.api_base = settings.LLM_API_BASE or None
        self.user_id = user_id
        self.function_called = function_called
        self.user_log = user_log(user_id)
        self.system_log = system_log
        self.llm = settings.LLM_MODEL
        self.llm_key = settings.LLM_KEY

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

        # One-token ping to verify the model is reachable and credentials are accepted.
        # (litellm.ahealth_check is proxy-oriented and pulls in extra dependencies.)
        model_conf = {
            "model": settings.LLM_MODEL,
            "api_key": settings.LLM_KEY,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "timeout": 30}
        if settings.LLM_TYPE == 'local':
            model_conf.update({'api_base': settings.LLM_API_BASE})
        await litellm.acompletion(**model_conf)

    async def chat(self, system_prompt: str, message: list[dict]) -> str:
        """
        Chat endpoint of LLM
        Args:
            system_prompt: System prompt inject to chat
            message: Message user send

        Returns:
            Content (str) of LLM response
        """
        self.user_log.info('Chat input:\n' + str(message))
        request = {
            "model": self.llm,
            "api_key": self.llm_key,
            "messages": [{"role": "system", "content": system_prompt}, *message],
        }
        if settings.LLM_TYPE == 'local':
            request["api_base"] = settings.LLM_API_BASE

        try:
            response = await litellm.acompletion(**request)
            content = response.choices[0].message.content or ''
            self.user_log.info('Chat output:\n' + content)
            return content
        except Exception as e:
            self.user_log.error(traceback.format_exc())
            raise LlmException(str(e))

    async def stream_chat(self, system_prompt: str, message: list[dict]):
        """
        Streaming chat endpoint of LLM
        Args:
            system_prompt: System prompt inject to chat
            message: Message user send

        Yields:
            Content chunks (str) as they arrive from the LLM
        """
        self.user_log.info('Stream chat input:\n' + str(message))
        request = {
            "model": self.llm,
            "api_key": self.llm_key,
            "messages": [{"role": "system", "content": system_prompt}, *message],
            "stream": True,
        }
        if settings.LLM_TYPE == 'local':
            request["api_base"] = settings.LLM_API_BASE

        try:
            response = await litellm.acompletion(**request)
            full_response = []
            async for chunk in response:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    full_response.append(delta)
                    yield delta
            self.user_log.info('Stream chat output:\n' + ''.join(full_response))
        except Exception as e:
            self.user_log.error(traceback.format_exc())
            raise LlmException(str(e))

    async def parsed_chat(self, system_prompt: str, message: list[dict], response_format: type[BaseModel]) -> dict:
        """
        Chat with specific response format
        Args:
            system_prompt:System prompt inject to chat
            message: Message user send
            response_format: The format BaseModel class

        Returns:
            Dict contains LLM response, validated against response_format
        """
        self.user_log.info('Parsed chat input:\n' + str(message))
        request = {
            "model": self.llm,
            "api_key": self.llm_key,
            "messages": [{"role": "system", "content": system_prompt}, *message],
            "response_format": response_format,
        }
        if settings.LLM_TYPE == 'local':
            request["api_base"] = settings.LLM_API_BASE

        try:
            response = await litellm.acompletion(**request)
            content = response.choices[0].message.content or ''
            self.user_log.info('Parsed chat output:\n' + content)
            parsed = response_format.model_validate_json(content)
            return parsed.model_dump()
        except Exception as e:
            self.user_log.error(traceback.format_exc())
            raise LlmException(str(e))