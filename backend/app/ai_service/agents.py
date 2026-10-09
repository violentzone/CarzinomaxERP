from datetime import date
from pathlib import Path
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_litellm import ChatLiteLLM
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
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


def with_today(query: str) -> str:
    """
    Prefix a sub-agent query with today's date so relative periods can be resolved.
    Args:
        query: Query handed over by the orchestrator
    Returns:
        Query with a `<context>` block in front
    """
    return f'<context>\ntoday: {date.today().isoformat()}\n</context>\n{query}'


llm = ChatLiteLLM(model=settings.LLM_MODEL, api_key=settings.LLM_API_KEY or None,
                  api_base=settings.LLM_API_BASE if settings.LLM_TYPE == 'local' else None)

# Shared by every orchestrator: a paused delete (waiting for approval) must survive until the next request of the same thread
checkpointer = MemorySaver()


hr_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('hr_helper_prompt.md'),
    tools=[
        tool_store.get_user_info, tool_store.create_user, tool_store.update_user,
        tool_store.get_departments, tool_store.create_department, tool_store.update_department,
        tool_store.get_attendance, tool_store.create_attendance, tool_store.update_attendance,
        tool_store.get_leaves, tool_store.review_leave_request,
        tool_store.get_paychecks, tool_store.create_paycheck, tool_store.update_paycheck,
    ],
)

expanse_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('expanse_helper_prompt.md'),
    tools=[tool_store.get_expenses, tool_store.create_expense, tool_store.update_expense],
)

scm_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('scm_helper_prompt.md'),
    tools=[tool_store.get_products, tool_store.create_product, tool_store.update_product],
)

dev_helper_agent = create_agent(
    model=llm,
    system_prompt=load_prompt('dev_helper_prompt.md'),
    tools=[
        tool_store.get_dev_project, tool_store.create_dev_project, tool_store.update_dev_project,
        tool_store.get_dev_investment, tool_store.create_dev_investment, tool_store.update_dev_investment,
        tool_store.get_project_downloads, tool_store.create_project_download, tool_store.update_project_download,
    ],
)

@tool('hr_helper', description='Agent that reads, creates and updates People & Payroll (HR) data: users and their access, departments, attendance logs, leave review, paychecks')
def call_hr_helper_agent(query: str):
    result = hr_helper_agent.invoke({
        'messages': [
            {'role': 'user',
             'content': with_today(query)}
    ]}
    )
    return result['messages'][-1].content

@tool('expanse_helper', description='Agent that reads, creates and updates Finance expense records')
def call_expanse_helper_agent(query: str):
    result = expanse_helper_agent.invoke({
        'messages': [
            {'role': 'user',
             'content': with_today(query)}
    ]}
    )
    return result['messages'][-1].content

@tool('scm_helper', description='Agent that reads, creates and updates Purchases (SCM) products')
def call_scm_helper_agent(query: str):
    result = scm_helper_agent.invoke({
        'messages': [
            {'role': 'user',
             'content': with_today(query)}
    ]}
    )
    return result['messages'][-1].content

@tool('dev_helper', description='Agent that reads, creates and updates Dev Tracking data: projects, investments, download snapshots')
def call_dev_helper_agent(query: str):
    result = dev_helper_agent.invoke({
        'messages': [
            {'role': 'user',
             'content': with_today(query)}
    ]}
    )
    return result['messages'][-1].content


# Delete tools stay on the orchestrator (not inside sub-agents) so the approval interrupt pauses the graph that owns the checkpointer
HR_DELETE_TOOLS = [tool_store.delete_user, tool_store.delete_department, tool_store.delete_attendance, tool_store.delete_leave_request, tool_store.delete_paycheck]
FINANCE_DELETE_TOOLS = [tool_store.delete_expense]
SCM_DELETE_TOOLS = [tool_store.delete_product]
DEV_DELETE_TOOLS = [tool_store.delete_dev_project, tool_store.delete_dev_investment, tool_store.delete_project_download]


def caller_context(caller: User) -> str:
    """
    Build the `<context>` block appended to the orchestrator system prompt.
    Args:
        caller: User who call orchestrator
    Returns:
        Today's date, the caller's identity and module access as a text block
    """
    return (
        '<context>\n'
        f'today: {date.today().isoformat()}\n'
        f'user_id: {caller.id}\n'
        f'full_name: {caller.full_name}\n'
        f'has_finance_access: {caller.has_finance_access}\n'
        f'has_scm_access: {caller.has_scm_access}\n'
        f'has_hr_access: {caller.has_hr_access}\n'
        f'has_dev_access: {caller.has_dev_access}\n'
        '</context>'
    )


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
    # Append tool list of user; every employee may file their own leave request
    tool_list = [tool_store.create_leave_request]
    delete_tools = []
    if caller.has_hr_access:
        tool_list.append(call_hr_helper_agent)
        delete_tools.extend(HR_DELETE_TOOLS)
    if caller.has_finance_access:
        tool_list.append(call_expanse_helper_agent)
        delete_tools.extend(FINANCE_DELETE_TOOLS)
    if caller.has_scm_access:
        tool_list.append(call_scm_helper_agent)
        delete_tools.extend(SCM_DELETE_TOOLS)
    if caller.has_dev_access:
        tool_list.append(call_dev_helper_agent)
        delete_tools.extend(DEV_DELETE_TOOLS)
    # Every delete pauses the run until the user approves or rejects it
    middleware = []
    if delete_tools:
        middleware.append(HumanInTheLoopMiddleware(interrupt_on={
            t.name: {'allowed_decisions': ['approve', 'reject'], 'description': f'{t.name} permanently removes a record and needs your approval'}
            for t in delete_tools
        }))
    orchestrator_agent = create_agent(
        model=llm,
        system_prompt=load_prompt('orchestrator_prompt.md') + '\n\n' + caller_context(caller),
        tools=tool_list + delete_tools,
        checkpointer=checkpointer,
        middleware=middleware,
    )
    return orchestrator_agent

# Test run area
if __name__ == '__main__':
    orchestrator = init_orchestrator(user_id=1)
    config = {'configurable': {'thread_id': 'cli'}}
    while True:
        terminal_input = input('test input: \n')
        if terminal_input == 'exit':
            break
        test_response = orchestrator.invoke({'messages': [{'role': 'user', 'content': terminal_input}]}, config=config)
        while '__interrupt__' in test_response:
            actions = [a for interrupt in test_response['__interrupt__'] for a in interrupt.value['action_requests']]
            for action in actions:
                print(f"Approval needed: {action['name']} {action['args']}")
            decision = 'approve' if input('approve? (y/n): ').strip().lower() == 'y' else 'reject'
            test_response = orchestrator.invoke(Command(resume={'decisions': [{'type': decision}] * len(actions)}), config=config)
        print(test_response['messages'][-1])
