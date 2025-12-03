import json
import os
import dataclasses
from datetime import date
from typing import Dict, Any, List
from models import (
    AppState, Profile, Stat, TaskTemplate, TimerSession, 
    AmcaAction, Wallet, Transaction, BookProject, 
    DailyRoutineLog, MaterialGoal, Settings, TaskCompletion
)

DEFAULT_STATE_FILE = "state.json"

def default_state() -> AppState:
    stat_names = [
        "yazılım", "yazarlık", "liderlik", "satış", 
        "içerik üretme", "entelektüellik", "plancılık", "farkındalık"
    ]
    default_stats = {name: Stat(name=name) for name in stat_names}

    return AppState(
        profile=Profile(),
        stats=default_stats,
        tasks={},
        sessions={},
        amca_actions=[],
        wallet=Wallet(),
        book_projects={},
        material_goals={},
        daily_logs={},
        settings=Settings(),
        task_completions=[]
    )

def appstate_to_dict(state: AppState) -> Dict[str, Any]:
    return dataclasses.asdict(state)

def dict_to_appstate(data: Dict[str, Any]) -> AppState:
    profile = Profile(**data.get("profile", {}))
    stats = {k: Stat(**v) for k, v in data.get("stats", {}).items()}
    
    # Tasks: Handle new fields with defaults for backward compatibility
    tasks = {}
    for k, v in data.get("tasks", {}).items():
        # Ensure new fields exist if loading old data
        if "created_date" not in v:
            v["created_date"] = date.today().isoformat()
        if "custom_every_n_days" not in v:
            v["custom_every_n_days"] = None
        if "custom_weekdays" not in v:
            v["custom_weekdays"] = None
        tasks[k] = TaskTemplate(**v)

    sessions = {k: TimerSession(**v) for k, v in data.get("sessions", {}).items()}
    amca_actions = [AmcaAction(**item) for item in data.get("amca_actions", [])]
    
    wallet_data = data.get("wallet", {})
    transactions = [Transaction(**t) for t in wallet_data.get("transactions", [])]
    wallet = Wallet(balance=wallet_data.get("balance", 0.0), transactions=transactions)

    book_projects = {k: BookProject(**v) for k, v in data.get("book_projects", {}).items()}
    material_goals = {k: MaterialGoal(**v) for k, v in data.get("material_goals", {}).items()}
    daily_logs = {k: DailyRoutineLog(**v) for k, v in data.get("daily_logs", {}).items()}
    settings = Settings(**data.get("settings", {}))
    
    # New: Task Completions
    completions_data = data.get("task_completions", [])
    task_completions = [TaskCompletion(**c) for c in completions_data]

    return AppState(
        profile=profile,
        stats=stats,
        tasks=tasks,
        sessions=sessions,
        amca_actions=amca_actions,
        wallet=wallet,
        book_projects=book_projects,
        material_goals=material_goals,
        daily_logs=daily_logs,
        settings=settings,
        task_completions=task_completions
    )

def save_state(state: AppState, path: str = DEFAULT_STATE_FILE) -> None:
    data_dict = appstate_to_dict(state)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, indent=2, ensure_ascii=False)
    print(f"State saved to {path}")

def load_state(path: str = DEFAULT_STATE_FILE) -> AppState:
    if not os.path.exists(path):
        return default_state()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return dict_to_appstate(data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"Error loading state: {e}. Returning default.")
        return default_state()