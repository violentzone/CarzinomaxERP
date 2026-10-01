from pathlib import Path
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM
from langchain.tools import tool

from app.core.config import settings
from app.ai_service import tool_store

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

# class State(TypedDict):
#     message: Annotated[list, add_messages]
#
#
# def hr_helper(state: State):
#     last_message = state['message'][-1]
#     # TODO: remove later
#     print('last_message: ', last_message)
#     # Load everything
#     model = llm
#     hr_helper_prompt = load_prompt('hr_helper_prompt.md')
#     messages = [
#         {'role': 'system',
#          'content': hr_helper_prompt},
#         {'role': 'user',
#          'content': last_message},
#     ]
#     reply = llm.invoke(messages=messages)
#     return {'messages': ['role': 'assistant', 'content': reply]}

hr_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('hr_helper_prompt.md')
    tool=[tool_store.get_user_info, tool_store.get_attendance]
)

expance_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('expance_helper_prompt.md')
)

@tool('hr_helper', description='Agent that helps get user information')
def call_hr_helper_agent(query: str)
    result = hr_helper_agent.invoke(
        'messages': [
        'role': 'user',
        'contant': query
    ]
    )
    return result['messages'][-1]

@tool('expance_helper', description='Agent that helps with expanse-relate tasks')
def call_expance_helper_agent(query: str)
    reult = expance_helper_agent.invoke(
        'messages': [
        'role': 'user',
        'contant': query
    ]
    )

orchestrator = create_agent(
    model=llm,
    system_prompt=load_prompt('orchestrator_prompt.md')
    tool=[call_hr_helper_agent, expance_helper_agent]
    )

# Test run area
if __name__ == '__main__':
