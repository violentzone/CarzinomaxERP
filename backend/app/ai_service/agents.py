from pathlib import Path
from langgraph_supervisor import create_supervisor
from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM

from app.core.config import settings

PROMPTS_DIR = Path(__file__).parent / 'prompts'


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

ORCHESTRATOR_SYSTEM_PROMPT = load_prompt('orchestrator_prompt.md')




orchestrator = create_supervisor(model=llm, prompt=ORCHESTRATOR_SYSTEM_PROMPT)


