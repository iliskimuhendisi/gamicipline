import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List

from models import (
    AppState, Profile, TaskTemplate, TimerSession, 
    AmcaAction, DailyRoutineLog, Transaction, TaskCompletion
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
        # Same day of week
        return target_date >= created_dt and target_date.weekday() == created_dt.weekday()
    
    elif task.recurrence == "monthly":
        # Same day of month (simplified, ignores 31st vs 30th issues for now)
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
                
                # If session is still running, add active time
                if s.end_time is None:
                    start_dt = datetime.fromisoformat(s.start_time)
                    active_sec = (datetime.now() - start_dt).total_seconds()
                    total_seconds += active_sec
                    
    return int(total_seconds // 60)

def is_task_completed_for_date(state: AppState, task: TaskTemplate, target_date: date) -> bool:
    # 1. Check if explicit completion record exists
    date_str = target_date.isoformat()
    for c in state.task_completions:
        if c.task_id == task.id and c.date == date_str:
            return True
            
    # 2. Check time target
    if task.target_minutes is None:
        return False
        
    minutes_done = get_task_minutes_for_date(state, task.id, target_date)
    
    if minutes_done >= task.target_minutes:
        # Auto-complete
        comp = TaskCompletion(
            id=str(uuid.uuid4()),
            task_id=task.id,
            date=date_str
        )
        state.task_completions.append(comp)
        return True
        
    return False

def get_tasks_for_date(state: AppState, target_date: date) -> List[TaskTemplate]:
    """Returns all tasks scheduled for today."""
    return [
        t for t in state.tasks.values() 
        if is_task_scheduled_for_date(t, target_date)
    ]

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
    
    # Update Stats
    task = state.tasks.get(session.task_id)
    if task and task.stat_name and task.stat_name in state.stats:
        state.stats[task.stat_name].add_seconds(session.duration_seconds)
    
    ensure_daily_log(state, start_dt.date())
    
    # Check Completion
    was_completed = False
    if task:
        # Check if this session triggered completion
        was_completed = is_task_completed_for_date(state, task, start_dt.date())
        
        # Grant rewards (Per session reward)
        # Note: You might want to only grant big rewards on completion, 
        # but sticking to original logic of reward per session for now.
        state.profile.xp += task.xp_reward
        state.profile.points += task.point_reward
        
    recalc_level_from_xp(state.profile)
    return session

# --- Misc Helpers ---
def ensure_daily_log(state: AppState, log_date: date) -> DailyRoutineLog:
    d_str = log_date.isoformat()
    if d_str not in state.daily_logs:
        state.daily_logs[d_str] = DailyRoutineLog(date=d_str)
    return state.daily_logs[d_str]

def add_amca_action(state: AppState, xp_reward: int, note: Optional[str] = None) -> AmcaAction:
    ts = datetime.now()
    action = AmcaAction(str(uuid.uuid4()), ts.isoformat(), xp_reward, note)
    state.amca_actions.append(action)
    state.profile.xp += xp_reward
    recalc_level_from_xp(state.profile)
    ensure_daily_log(state, ts.date()).amca_count += 1
    return action

def update_streak_for_date(state: AppState, log_date: date) -> None:
    # (Same as before, abbreviated for brevity in this answer context if unchanged)
    # Keeping logic for completeness
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