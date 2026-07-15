""" Function tools for HR module"""
from typing import Literal
from datetime import datetime


from app.models import Employee
from uuid import uuid4

def operate_employee(operation: Literal['create', 'update', 'delete'], name: str, department_id: int=None, email: str|None=None, job_title: str|None=None) -> bool:
    """
    Tool for LLM to operate on Employee table in database
    Args:
        operation (str): CRUD operation in string format
        name (str): Employee name
        department_id (int)(optional): Department id of employee, required if create employee or update to different department
        email (str): Employee email
        job_title (str): Employee job title

    Returns:
        True if successful, False otherwise
    """
    if operation == 'create':
        _id = uuid4()
        hire_date = datetime.now().date()
        employee = Employee(name=name, department_id=department_id, id=_id, email=email, hire_date=hire_date)