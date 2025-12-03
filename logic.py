import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List

from models import (
    AppState, Profile, TaskTemplate, TimerSession, 
    AmcaAction, DailyRoutineLog, Transaction, TaskCompletion, BookProject
)

# --- Leveling Logic ---
LEVEL_NAMES = [
    "Çırak", "Uyanan", "Disiplin Çömezi", "Yolcu", "Savaşçı", 
    "Muhafız", "Usta", "Büyük Usta", "Efsane", "Bilge"
]

def get_level_name(level: int) -> str:
    if level < 1: return LEVEL_NAMES[0]
    index = min(level - 1, len(LEVEL_NAMES) - 1)
    return LEVEL_NAMES[index]

def recalc_level_from_xp(profile: Profile) -> None:
    profile.level = 1 + (profile.xp // 500)
    profile.level_name = get_level_name(profile.level)

# --- Task Definition ---
def add_task_definition(
    state: AppState, title: str, description: str, category: str, 
    recurrence: str, target_minutes: Optional[int], xp_reward: int, 
    point_reward: int, stat_name: Optional[str], 
    is_amca_task: bool = False,
    custom_every_n_days: Optional[int] = None,
    custom_weekdays: Optional[List[int]] = None
) -> TaskTemplate:
    
    new_id = str(uuid.uuid4())
    task = TaskTemplate(
        id=new_id,
        title=title,
        description=description,
        category=category,
        recurrence=recurrence,
        target_minutes=target_minutes,
        xp_reward=xp_reward,
        point_reward=point_reward,
        stat_name=stat_name,
        is_amca_task=is_amca_task,
        created_date=date.today().isoformat(),
        custom_every_n_days=custom_every_n_days,
        custom_weekdays=custom_weekdays
    )
    state.tasks[new_id] = task
    return task

# --- Recurrence & Schedule Logic ---

def is_task_scheduled_for_date(task: TaskTemplate, target_date: date) -> bool:
    created_dt = date.fromisoformat(task.created_date)
    
    if task.recurrence == "once":
        return created_dt == target_date
    elif task.recurrence == "daily":
        return target_date >= created_dt
    elif task.recurrence == "weekly":
        return target_date >= created_dt and target_date.weekday() == created_dt.weekday()
    elif task.recurrence == "monthly":
        return target_date >= created_dt and target_date.day == created_dt.day
    elif task.recurrence == "custom":
        if task.custom_every_n_days:
            diff = (target_date - created_dt).days
            return target_date >= created_dt and (diff % task.custom_every_n_days == 0)
        elif task.custom_weekdays:
            return target_date >= created_dt and (target_date.weekday() in task.custom_weekdays)
    return False

def get_task_minutes_for_date(state: AppState, task_id: str, target_date: date) -> int:
    total_seconds = 0
    for s in state.sessions.values():
        if s.task_id == task_id:
            s_date = datetime.fromisoformat(s.start_time).date()
            if s_date == target_date:
                total_seconds += s.duration_seconds
                if s.end_time is None:
                    start_dt = datetime.fromisoformat(s.start_time)
                    active_sec = (datetime.now() - start_dt).total_seconds()
                    total_seconds += active_sec
    return int(total_seconds // 60)

def is_task_completed_for_date(state: AppState, task: TaskTemplate, target_date: date) -> bool:
    date_str = target_date.isoformat()
    for c in state.task_completions:
        if c.task_id == task.id and c.date == date_str:
            return True
            
    if task.target_minutes is None:
        return False
        
    minutes_done = get_task_minutes_for_date(state, task.id, target_date)
    if minutes_done >= task.target_minutes:
        comp = TaskCompletion(str(uuid.uuid4()), task.id, date_str)
        state.task_completions.append(comp)
        return True
    return False

def get_tasks_for_date(state: AppState, target_date: date) -> List[TaskTemplate]:
    return [t for t in state.tasks.values() if is_task_scheduled_for_date(t, target_date)]

# --- Timer / Session Logic ---

def get_active_session(state: AppState, task_id: str) -> Optional[TimerSession]:
    for session in state.sessions.values():
        if session.task_id == task_id and session.end_time is None:
            return session
    return None

def get_all_active_sessions(state: AppState) -> List[TimerSession]:
    return [s for s in state.sessions.values() if s.end_time is None]

def start_timer_for_task(state: AppState, task_id: str) -> TimerSession:
    existing = get_active_session(state, task_id)
    if existing: return existing
    
    session_id = str(uuid.uuid4())
    session = TimerSession(
        id=session_id,
        task_id=task_id,
        start_time=datetime.now().isoformat(),
        duration_seconds=0
    )
    state.sessions[session_id] = session
    return session

def stop_timer_for_session(state: AppState, session_id: str) -> TimerSession:
    session = state.sessions.get(session_id)
    if not session or session.end_time: return session
    
    end_dt = datetime.now()
    start_dt = datetime.fromisoformat(session.start_time)
    duration = (end_dt - start_dt).total_seconds()
    
    session.duration_seconds = int(duration)
    session.end_time = end_dt.isoformat()
    
    task = state.tasks.get(session.task_id)
    if task and task.stat_name and task.stat_name in state.stats:
        state.stats[task.stat_name].add_seconds(session.duration_seconds)
    
    ensure_daily_log(state, start_dt.date())
    
    if task:
        is_task_completed_for_date(state, task, start_dt.date())
        state.profile.xp += task.xp_reward
        state.profile.points += task.point_reward
        
    recalc_level_from_xp(state.profile)
    return session

# --- Routines & Misc Helpers ---

def ensure_daily_log(state: AppState, log_date: date) -> DailyRoutineLog:
    d_str = log_date.isoformat()
    if d_str not in state.daily_logs:
        state.daily_logs[d_str] = DailyRoutineLog(date=d_str)
    return state.daily_logs[d_str]

def create_book_project(state: AppState, title: str, total_pages: int, daily_target: int) -> BookProject:
    new_id = str(uuid.uuid4())
    book = BookProject(
        id=new_id,
        title=title,
        total_pages=total_pages,
        daily_target_pages=daily_target,
        pages_written=0,
        is_completed=False
    )
    state.book_projects[new_id] = book
    return book

def update_book_progress(state: AppState, book_id: str, pages_written_today: int, log_date: date) -> None:
    book = state.book_projects.get(book_id)
    if not book: return
    
    book.pages_written += pages_written_today
    if book.pages_written >= book.total_pages:
        book.is_completed = True
        
    log = ensure_daily_log(state, log_date)
    log.pages_written += pages_written_today

def set_daily_zikr(state: AppState, log_date: date, count: int) -> None:
    log = ensure_daily_log(state, log_date)
    log.zikr_count = count

def update_zikr_target(state: AppState, new_target: int) -> None:
    state.settings.zikr_daily_target = new_target

def set_daily_income(state: AppState, log_date: date, total_amount: float) -> None:
    """Sets the daily income to a specific total value, adjusting wallet balance by the difference."""
    log = ensure_daily_log(state, log_date)
    
    current_log_income = log.income_amount
    delta = total_amount - current_log_income
    
    if delta == 0:
        return

    # Update Log
    log.income_amount = total_amount
    
    # Update Wallet
    state.wallet.balance += delta
    
    # Add Transaction (Audit trail for the adjustment)
    t_id = str(uuid.uuid4())
    txn = Transaction(
        id=t_id,
        timestamp=datetime.now().isoformat(),
        amount=delta,
        category="Income Adjustment",
        description=f"Manual routine update for {log_date}"
    )
    state.wallet.transactions.append(txn)

def add_amca_action(state: AppState, xp_reward: int, note: Optional[str] = None) -> AmcaAction:
    ts = datetime.now()
    action = AmcaAction(str(uuid.uuid4()), ts.isoformat(), xp_reward, note)
    state.amca_actions.append(action)
    state.profile.xp += xp_reward
    recalc_level_from_xp(state.profile)
    ensure_daily_log(state, ts.date()).amca_count += 1
    return action

def apply_wake_times(state: AppState, log_date: date, wake_target_time: str, wake_actual_time: str) -> None:
    log = ensure_daily_log(state, log_date)
    log.wake_target_time = wake_target_time
    log.wake_actual_time = wake_actual_time
    
    def parse_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    
    try:
        target_min = parse_minutes(wake_target_time)
        actual_min = parse_minutes(wake_actual_time)
        
        if actual_min > target_min:
            delay = actual_min - target_min
            penalty = delay * state.settings.wake_penalty_per_minute
            log.wake_penalty = penalty
        else:
            log.wake_penalty = 0.0
    except ValueError:
        pass # Handle invalid time formats gracefully

def update_streak_for_date(state: AppState, log_date: date) -> None:
    d_str = log_date.isoformat()
    log = state.daily_logs.get(d_str)
    amca_ok = log and log.amca_count >= state.settings.min_amca_per_day
    
    timer_ok = False
    for s in state.sessions.values():
        if s.end_time and datetime.fromisoformat(s.end_time).date() == log_date:
            timer_ok = True
            break
            
    if amca_ok or timer_ok:
        state.profile.streak_days += 1
        state.profile.xp += 10
        recalc_level_from_xp(state.profile)
    else:
        if state.profile.streak_freezes > 0:
            state.profile.streak_freezes -= 1
        else:
            state.profile.streak_days = 0