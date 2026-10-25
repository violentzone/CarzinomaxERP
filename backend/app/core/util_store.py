"""
Small helpers shared by more than one module
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'ai_service' / 'prompts'


def load_prompt(name: str) -> str:
    """
    Read a prompt file from `app/ai_service/prompts/`.
    Args:
        name: File name including extension, e.g. 'orchestrator_system.md'
    Returns:
        Prompt text with surrounding whitespace stripped
    """
    return (PROMPTS_DIR / name).read_text(encoding='utf-8').strip()
