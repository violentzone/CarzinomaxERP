""" Function tools for HR module"""
from typing import Optional, Literal

from app.models import Employee
from sqlalchemy.

def operate_employee(operation: Literal['create', 'update', 'delete'], name: str, department_id: int=None) -> bool:
    """
    Tool for LLM to operate on Employee table in database
    Args:
        operation (str): CRUD operation in string format
        name (str): Employee name
        department_id (int)(optional): Department id of employee, required if create employee or update to different department

    Returns:
        True if successful, False otherwise
    """
    if operation == 'create':
