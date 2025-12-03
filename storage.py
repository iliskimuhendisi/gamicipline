import json
import os
import dataclasses
from typing import Dict, Any, List
from models import (
    AppState, Profile, Stat, TaskTemplate, TimerSession, 
    AmcaAction, Wallet, Transaction, BookProject, 
    DailyRoutineLog, MaterialGoal, Settings
)

DEFAULT_STATE_FILE = "state.json"

def default_state() -> AppState:
    """Creates a fresh AppState with default values and pre-configured stats."""
    
    # Pre-defined stats
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
        settings=Settings()
    )

def appstate_to_dict(state: AppState) -> Dict[str, Any]:
    """Converts the AppState dataclass hierarchy into a plain dictionary."""
    return dataclasses.asdict(state)

def dict_to_appstate(data: Dict[str, Any]) -> AppState:
    """
    Reconstructs the AppState object from a dictionary.
    We must manually reconstruct nested dataclasses to ensure they are objects, not dicts.
    """
    
    # 1. Profile
    profile_data = data.get("profile", {})
    profile = Profile(**profile_data)

    # 2. Stats (Dict[str, Stat])
    stats_data = data.get("stats", {})
    stats = {k: Stat(**v) for k, v in stats_data.items()}

    # 3. Tasks (Dict[str, TaskTemplate])
    tasks_data = data.get("tasks", {})
    tasks = {k: TaskTemplate(**v) for k, v in tasks_data.items()}

    # 4. Sessions (Dict[str, TimerSession])
    sessions_data = data.get("sessions", {})
    sessions = {k: TimerSession(**v) for k, v in sessions_data.items()}

    # 5. Amca Actions (List[AmcaAction])
    amca_data = data.get("amca_actions", [])
    amca_actions = [AmcaAction(**item) for item in amca_data]

    # 6. Wallet (Nested Transactions)
    wallet_data = data.get("wallet", {})
    transactions_data = wallet_data.get("transactions", [])
    transactions = [Transaction(**t) for t in transactions_data]
    # Reconstruct wallet with the list of Transaction objects
    wallet = Wallet(
        balance=wallet_data.get("balance", 0.0),
        transactions=transactions
    )

    # 7. Book Projects (Dict[str, BookProject])
    books_data = data.get("book_projects", {})
    book_projects = {k: BookProject(**v) for k, v in books_data.items()}

    # 8. Material Goals (Dict[str, MaterialGoal])
    goals_data = data.get("material_goals", {})
    material_goals = {k: MaterialGoal(**v) for k, v in goals_data.items()}

    # 9. Daily Logs (Dict[str, DailyRoutineLog])
    logs_data = data.get("daily_logs", {})
    daily_logs = {k: DailyRoutineLog(**v) for k, v in logs_data.items()}

    # 10. Settings
    settings_data = data.get("settings", {})
    settings = Settings(**settings_data)

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
        settings=settings
    )

def save_state(state: AppState, path: str = DEFAULT_STATE_FILE) -> None:
    """Saves the AppState to a JSON file."""
    data_dict = appstate_to_dict(state)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, indent=2, ensure_ascii=False)
    print(f"State saved to {path}")

def load_state(path: str = DEFAULT_STATE_FILE) -> AppState:
    """Loads AppState from JSON. Returns default state if file doesn't exist."""
    if not os.path.exists(path):
        print(f"No existing state found at {path}. Creating new state.")
        return default_state()
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return dict_to_appstate(data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"Error loading state: {e}. Returning default state (backup advised).")
        return default_state()