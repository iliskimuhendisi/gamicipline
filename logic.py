import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List

from models import (
    AppState, Profile, TaskTemplate, TimerSession, 
    AmcaAction, DailyRoutineLog, Transaction
)

# --- Leveling Logic ---

LEVEL_NAMES = [
    "Çırak",                # Level 1
    "Uyanan",               # Level 2
    "Disiplin Çömezi",      # Level 3
    "Yolcu",                # Level 4
    "Savaşçı",              # Level 5
    "Muhafız",              # Level 6
    "Usta",                 # Level 7
    "Büyük Usta",           # Level 8
    "Efsane",               # Level 9
    "Bilge"                 # Level 10+
]

def get_level_name(level: int) -> str:
    """Returns a human-readable level name, clamping to the max defined index."""
    if level < 1:
        return LEVEL_NAMES[0]
    index = min(level - 1, len(LEVEL_NAMES) - 1)
    return LEVEL_NAMES[index]

def recalc_level_from_xp(profile: Profile) -> None:
    """
    Recalculates level based on XP.
    Formula: Level 1 = 0-499 XP. Level 2 = 500-999 XP, etc.
    Level = 1 + (XP // 500)
    """
    profile.level = 1 + (profile.xp // 500)
    profile.level_name = get_level_name(profile.level)

# --- Task Management ---

def add_task_definition(
    state: AppState, 
    title: str, 
    description: str, 
    category: str, 
    recurrence: str, 
    target_minutes: Optional[int], 
    xp_reward: int, 
    point_reward: int, 
    stat_name: Optional[str], 
    is_amca_task: bool = False
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
        is_amca_task=is_amca_task
    )
    state.tasks[new_id] = task
    return task

# --- Timer / Session Logic ---

def get_active_session(state: AppState, task_id: str) -> Optional[TimerSession]:
    """Returns the active TimerSession for a specific task if one exists."""
    for session in state.sessions.values():
        if session.task_id == task_id and session.end_time is None:
            return session
    return None

def get_all_active_sessions(state: AppState) -> List[TimerSession]:
    """Returns a list of all currently running sessions."""
    return [s for s in state.sessions.values() if s.end_time is None]

def start_timer_for_task(
    state: AppState, 
    task_id: str, 
    start_dt: Optional[datetime] = None
) -> TimerSession:
    
    # Check if already running
    existing = get_active_session(state, task_id)
    if existing:
        return existing

    if start_dt is None:
        start_dt = datetime.now()
        
    session_id = str(uuid.uuid4())
    session = TimerSession(
        id=session_id,
        task_id=task_id,
        start_time=start_dt.isoformat(),
        duration_seconds=0,
        end_time=None
    )
    state.sessions[session_id] = session
    return session

def stop_timer_for_session(
    state: AppState, 
    session_id: str, 
    end_dt: Optional[datetime] = None
) -> TimerSession:
    
    session = state.sessions.get(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")
    
    if session.end_time is not None:
        return session  # Already stopped
        
    if end_dt is None:
        end_dt = datetime.now()
        
    start_dt = datetime.fromisoformat(session.start_time)
    
    # Calculate duration
    duration = (end_dt - start_dt).total_seconds()
    session.duration_seconds = int(duration)
    session.end_time = end_dt.isoformat()
    
    # 1. Update Stat (if task has one)
    task = state.tasks.get(session.task_id)
    if task and task.stat_name and task.stat_name in state.stats:
        state.stats[task.stat_name].add_seconds(session.duration_seconds)
        
    # 2. Update Daily Log (ensure it exists)
    log_date = start_dt.date()
    # ensure_daily_log is called implicitly by just accessing/creating logic
    _ = ensure_daily_log(state, log_date)
    
    # 3. Grant Rewards
    if task:
        state.profile.xp += task.xp_reward
        state.profile.points += task.point_reward
        
    # 4. Recalculate Level
    recalc_level_from_xp(state.profile)
    
    return session

# --- Amca Logic ---

def add_amca_action(
    state: AppState, 
    xp_reward: int, 
    note: Optional[str] = None, 
    ts: Optional[datetime] = None
) -> AmcaAction:
    
    if ts is None:
        ts = datetime.now()
        
    action_id = str(uuid.uuid4())
    action = AmcaAction(
        id=action_id,
        timestamp=ts.isoformat(),
        xp_reward=xp_reward,
        note=note
    )
    state.amca_actions.append(action)
    
    # Update Profile
    state.profile.xp += xp_reward
    recalc_level_from_xp(state.profile)
    
    # Update Daily Log
    daily_log = ensure_daily_log(state, ts.date())
    daily_log.amca_count += 1
    
    return action

# --- Daily Routine & Logistics ---

def ensure_daily_log(state: AppState, log_date: date) -> DailyRoutineLog:
    date_str = log_date.isoformat()
    if date_str not in state.daily_logs:
        state.daily_logs[date_str] = DailyRoutineLog(date=date_str)
    return state.daily_logs[date_str]

def update_book_progress(
    state: AppState, 
    book_id: str, 
    pages_written_today: int, 
    log_date: date
) -> None:
    
    book = state.book_projects.get(book_id)
    if not book:
        return
        
    # Update Book
    book.pages_written += pages_written_today
    if book.pages_written >= book.total_pages:
        book.is_completed = True
        
    # Update Daily Log
    log = ensure_daily_log(state, log_date)
    log.pages_written += pages_written_today

def update_zikr_and_income(
    state: AppState, 
    log_date: date, 
    zikr_count: int, 
    income_amount: float
) -> None:
    
    log = ensure_daily_log(state, log_date)
    log.zikr_count += zikr_count
    log.income_amount += income_amount
    
    if income_amount > 0:
        t_id = str(uuid.uuid4())
        txn = Transaction(
            id=t_id,
            timestamp=datetime.now().isoformat(),
            amount=income_amount,
            category="Income",
            description=f"Daily income log for {log_date}"
        )
        state.wallet.transactions.append(txn)
        state.wallet.balance += income_amount

def apply_wake_times(
    state: AppState, 
    log_date: date, 
    wake_target_time: str, 
    wake_actual_time: str
) -> None:
    """
    Times format: "HH:MM" 24-hour.
    """
    log = ensure_daily_log(state, log_date)
    log.wake_target_time = wake_target_time
    log.wake_actual_time = wake_actual_time
    
    # Simple hour/minute parsing
    def parse_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    
    target_min = parse_minutes(wake_target_time)
    actual_min = parse_minutes(wake_actual_time)
    
    if actual_min > target_min:
        delay = actual_min - target_min
        penalty = delay * state.settings.wake_penalty_per_minute
        log.wake_penalty = penalty

def update_streak_for_date(state: AppState, log_date: date) -> None:
    date_str = log_date.isoformat()
    log = state.daily_logs.get(date_str)
    
    # Check Amca Count condition
    amca_satisfied = False
    if log and log.amca_count >= state.settings.min_amca_per_day:
        amca_satisfied = True
        
    # Check Timer Session condition
    timer_satisfied = False
    for sess in state.sessions.values():
        if sess.end_time:
            end_dt = datetime.fromisoformat(sess.end_time)
            if end_dt.date() == log_date:
                timer_satisfied = True
                break
    
    is_successful_day = amca_satisfied or timer_satisfied
    
    if is_successful_day:
        state.profile.streak_days += 1
        # Small streak bonus
        state.profile.xp += 10 
        recalc_level_from_xp(state.profile)
    else:
        if state.profile.streak_freezes > 0:
            state.profile.streak_freezes -= 1
            # Streak preserved
        else:
            state.profile.streak_days = 0