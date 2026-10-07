from pathlib import Path
from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM
from langchain.tools import tool
from sqlalchemy import select

from app.core.config import settings
from app.ai_service import tool_store
from app.core.database import SyncSessionLocal
from app.models.auth import User

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


llm = ChatLiteLLM(model=settings.LLM_MODEL, api_key=settings.LLM_API_KEY or None,
                  api_base=settings.LLM_API_BASE if settings.LLM_TYPE == 'local' else None)


hr_helper_agent = create_agent(model=llm, system_prompt=load_prompt('hr_helper_prompt.md'), tools=[tool_store.get_user_info, tool_store.get_attendance])


expanse_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('expanse_helper_prompt.md')
)

@tool('hr_helper', description='Agent that helps get user information')
def call_hr_helper_agent(query: str):
    result = hr_helper_agent.invoke(
        {'messages': {
            'role': 'user',
            'content': query
        }
        })
    return result['messages'][-1].content

@tool('expanse_helper', description='Agent that helps with expanse-relate tasks')
def call_expanse_helper_agent(query: str):
    result = expanse_helper_agent.invoke({
        'messages': [
            {'role': 'user',
             'content': query}
    ]}
    )
    return result['messages'][-1].content

def init_orchestrator(user_id: int):
    """
    Create orchestrator, with permitted subagents, subagent are selected by User's `has_finance_access`, `has_scm_access`, `has_hr_access` and `has_dev_access`
    Args:
        user_id: User who call orchestrator

    Returns:
        Agent orchestrator
    """
    # Configure sub-agent list
    with SyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        caller = session.execute(stmt).scalar_one_or_none()
    if not caller:
        raise ValueError('Unknow user ID')
    # Append tool list of user
    tool_list = []
    if caller.has_hr_access:
        tool_list.append(call_hr_helper_agent)
    if caller.has_dev_access:
        tool_list.append(call_expanse_helper_agent)
    orchestrator_agent = create_agent(model=llm, system_prompt=load_prompt('orchestrator_prompt.md'), tools=tool_list)
    return orchestrator_agent

# Test run area
if __name__ == '__main__':
    orchestrator = init_orchestrator(user_id=1)
    while True:
        terminal_input = input('test input: \n')
        if terminal_input == 'exit':
            break
        test_response = orchestrator.invoke({'messages': [{'role': 'user', 'content': terminal_input}]})
        print(test_response['messages'][-1])