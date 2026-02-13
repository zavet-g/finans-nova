import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sheets_")


def run_in_executor(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, functools.partial(func, *args, **kwargs))

    return wrapper


async def async_add_transaction(transaction):
    from src.services.sheets import add_transaction

    return await run_in_executor(add_transaction)(transaction)


async def async_get_transactions(limit: int = 10, offset: int = 0):
    from src.services.sheets import get_transactions

    return await run_in_executor(get_transactions)(limit, offset)


async def async_get_month_summary(year: int, month: int):
    from src.services.sheets import get_month_summary

    return await run_in_executor(get_month_summary)(year, month)


async def async_get_period_summary(start_date, end_date):
    from src.services.sheets import get_period_summary

    return await run_in_executor(get_period_summary)(start_date, end_date)


async def async_get_enriched_analytics(start_date, end_date, prev_start=None, prev_end=None):
    from src.services.sheets import get_enriched_analytics

    return await run_in_executor(get_enriched_analytics)(start_date, end_date, prev_start, prev_end)


async def async_get_expenses_by_category(year: int = None, month: int = None):
    from src.services.sheets import get_expenses_by_category

    return await run_in_executor(get_expenses_by_category)(year, month)


async def async_get_yearly_monthly_breakdown(year: int):
    from src.services.sheets import get_yearly_monthly_breakdown

    return await run_in_executor(get_yearly_monthly_breakdown)(year)


async def async_create_backup():
    from src.services.sheets import create_backup

    return await run_in_executor(create_backup)()


async def async_export_to_csv():
    from src.services.sheets import export_to_csv

    return await run_in_executor(export_to_csv)()


async def async_init_spreadsheet():
    from src.services.sheets import init_spreadsheet

    return await run_in_executor(init_spreadsheet)()


def shutdown_executor():
    logger.info("Shutting down Google Sheets executor...")
    _executor.shutdown(wait=True)
    logger.info("Google Sheets executor shut down")
