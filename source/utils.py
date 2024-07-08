import datetime

from dateutil import relativedelta as rd
from dateutil.utils import today as _today
from sqlalchemy import func, Integer, Time
from sqlalchemy.sql.expression import BinaryExpression

from .settings import settings

timezone = get_time_zone(settings.timezone)


def today() -> datetime.datetime:
    return _today(timezone)


def now() -> datetime.datetime:
    return datetime.datetime.now(timezone)


def monday_on_week(year: int, week: int) -> datetime.datetime:
    """Возвращает понедельник недели под номером :week_num в году :year"""
    D = datetime.datetime(year, 1, 1, tzinfo=timezone)
    return D + rd.relativedelta(weeks=int(week), weekday=rd.MO(-1))


def sunday_on_week(year: int, week: int) -> datetime.datetime:
    """Возвращает воскресенье недели под номером :week_num в году :year"""
    D = datetime.datetime(year, 1, 1, tzinfo=timezone)
    return D + rd.relativedelta(weeks=int(week), weekday=rd.SU(-1))


def first_month_day(year: int, month: int) -> datetime.datetime:
    """Возвращает первый день месяца :month в году :year"""
    return datetime.datetime(year, month, 1, tzinfo=timezone)


def last_month_day(year: int, month: int) -> datetime.datetime:
    """Возвращает последний день месяца :month в году :year"""
    D = datetime.datetime(year, month + 1, 1, tzinfo=timezone)
    return D - rd.relativedelta(days=1)


def next_month() -> datetime.datetime:
    """Возвращает понедельник на следующей неделе Aware"""
    TODAY = today()
    return TODAY + rd.relativedelta(days=+1, weekday=rd.MO)


def this_month() -> datetime.datetime:
    """Возвращает понедельник на текущей неделе Aware"""
    TODAY = today()
    return TODAY + rd.relativedelta(weekday=rd.MO(-1))


def calculate_date(week_day: int, day_time: datetime.time)\
        -> datetime.datetime:
    """Конструирует дату по дню недели и времени дня на текущей неделе Aware"""
    MONDAY = this_month()
    return MONDAY + rd.relativedelta(
        days=+week_day, hour=day_time.hour, minute=day_time.minute)


def day_stub() -> datetime.datetime:
    return datetime.datetime(2000, 1, 1, tzinfo=timezone)


def this_month_sql() -> BinaryExpression:
    """PostgreSQL function: Возвращает понедельник
     на текущей неделе type::timestamp (no TZ)"""
    return (func.current_date()
            + 1 - func.cast(func.extract
                            ("isodow", func.current_date()), Integer))


def previous_month_sql():
    """PostgreSQL function: Возвращает понедельник
     на предыдущей неделе type::timestamp (no TZ)"""
    return this_month_sql() - 7


def calc_date_sql(week_day: Integer, day_time: Time):
    """PostgreSQL function: Конструирует дату
     по дню недели и времени дня на текущей неделе type::timestamp (no TZ)"""
    MONDAY = this_month_sql()
    return MONDAY + week_day + day_time


def make_interval_sql(years=0, months=0, weeks=0, days=0):
    """PostgreSQL function: Возвращает объект type::interval"""
    return func.make_interval(years, months, weeks, days)


def time_zone_date_sql(date):
    """PostgreSQL function: Переводит
     type::timestamp в type::timestamp timezone"""
    return func.timezone(settings.timezone, date)
