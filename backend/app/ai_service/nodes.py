from pathlib import Path
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph_supervisor import create_supervisor
from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM

from app.core.config import settings

PROMPTS_DIR = Path(__file__).parent / 'prompts'

llm = ChatLiteLLM(model=settings.LLM_MODEL, api_key=settings.LLM_KEY or None, api_base=settings.LLM_API_BASE if settings.LLM_TYPE == 'local' else None)

def load_prompt(name: str) -> str:
    """
    Read a prompt file from `app/ai_service/prompts/`.
    Args:
        name: File name including extension, e.g. 'orchestrator_system.md'
    Returns:
        Prompt text with surrounding whitespace stripped
    """
    return (PROMPTS_DIR / name).read_text(encoding='utf-8').strip()


llm = ChatLiteLLM(model=settings.LLM_MODEL, api_key=settings.LLM_KEY or None,
                  api_base=settings.LLM_API_BASE if settings.LLM_TYPE == 'local' else None)

class State(TypedDict):
    message: Annotated[list, add_messages]


def hr_helper(state: State):
    last_message = state['message'][-1]
    # TODO: remove later
    print('last_message: ', last_message)
    llm = llm

