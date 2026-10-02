from pathlib import Path
from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM
from langchain.tools import tool

from app.core.config import settings
from app.ai_service import tool_store

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
    return result['messages'][-1]

@tool('expanse_helper', description='Agent that helps with expanse-relate tasks')
def call_expanse_helper_agent(query: str):
    result = expanse_helper_agent.invoke({
        'messages': [
            {'role': 'user',
             'content': query}
    ]}
    )
    return result['messages'][-1]

orchestrator = create_agent(model=llm, system_prompt=load_prompt('orchestrator_prompt.md'), tools=[call_hr_helper_agent, call_expanse_helper_agent])


# Test run area
if __name__ == '__main__':
    while True:
        terminal_input = input('test input: \n')
        if terminal_input == 'exit':
            break
        test_response = orchestrator.invoke({'messages': [{'role': 'user', 'content': terminal_input}]})
        print(test_response['messages'][-1])