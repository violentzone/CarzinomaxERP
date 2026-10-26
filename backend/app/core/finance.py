"""
Finance logic shared by the REST router and the chat tools
An investment expense linked to a dev project is mirrored into `dev_investments` so Dev Tracking totals stay complete (owner decision); update and delete do not sync the mirror.
"""
from app.models.dev_tracking import DEV_INVESTMENT_CATEGORIES, DevInvestment
from app.models.finance import ExpenseType, Finance


def investment_from_expense(expense: Finance) -> DevInvestment | None:
    """
    Build the Dev Tracking row that mirrors an investment expense; the caller adds it to its own session
    Args:
        expense: Expense about to be saved, `expense_date` must already be set (the column default only runs at flush)

    Returns:
        A `DevInvestment` with the expense's project, date, amount, vendor, category and description, None when the expense is not an investment or has no project
    """
    if expense.expense_type != ExpenseType.INVESTMENT or expense.project_id is None:
        return None
    category = expense.category if expense.category in DEV_INVESTMENT_CATEGORIES else 'other'
    investment = DevInvestment(project_id=expense.project_id, date=expense.expense_date, amount=expense.amount, vendor=expense.vendor, category=category, description=expense.description)
    return investment
