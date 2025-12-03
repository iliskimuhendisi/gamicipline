import sys
import os
import uuid
from datetime import datetime
from typing import List

import logic
import storage
from models import AppState, TaskTemplate


def print_status_bar(state: AppState):
    """Prints a consistent status bar after actions."""
    p = state.profile
    w = state.wallet
    print(f"\n[ STATUS ] Level {p.level} ({p.level_name}) | XP: {p.xp} | Streak: {p.streak_days} 🔥 | Frz: {p.streak_freezes} ❄️ | Balance: {w.balance:.2f} TL")
    print("-" * 80)

def print_summary(state: AppState):
    print("\n=== FULL SUMMARY ===")
    print(f"User: {state.profile.level_name} (Lvl {state.profile.level})")
    print(f"Total XP: {state.profile.xp}")
    print(f"Wallet: {state.wallet.balance:.2f}")
    
    print("\n--- Stats ---")
    for name, stat in state.stats.items():
        if stat.total_seconds > 0:
            hrs = stat.total_seconds / 3600.0
            print(f"  {name.title()}: Lvl {stat.level()} ({hrs:.2f} hrs)")

    print("\n--- Recent Logs ---")
    sorted_dates = sorted(state.daily_logs.keys(), reverse=True)[:3]
    for d in sorted_dates:
        log = state.daily_logs[d]
        print(f"  {d}: Amca={log.amca_count}, Zikr={log.zikr_count}, Income={log.income_amount}")
    
    print("====================\n")

def list_tasks(state: AppState) -> List[TaskTemplate]:
    if not state.tasks:
        print("No tasks defined.")
        return []
    
    print("\n--- Available Tasks ---")
    tasks_list = list(state.tasks.values())
    for idx, t in enumerate(tasks_list):
        print(f"{idx + 1}) {t.title} [XP: {t.xp_reward}] (ID: {t.id[:4]}...)")
    return tasks_list

def handle_add_task(state: AppState):
    print("\n--- Create New Task ---")
    title = input("Title: ").strip()
    desc = input("Description: ").strip()
    cat = input("Category (e.g., yazılım): ").strip()
    try:
        xp = int(input("XP Reward: ").strip())
        points = int(input("Points Reward: ").strip())
        target = int(input("Target Minutes (0 for none): ").strip())
        target = target if target > 0 else None
    except ValueError:
        print("Invalid number input. Aborting task creation.")
        return

    stat_name = input("Stat Name (optional, press Enter to skip): ").strip()
    stat_name = stat_name if stat_name else None

    t = logic.add_task_definition(
        state, title, desc, cat, "daily", target, xp, points, stat_name
    )
    print(f"Task '{t.title}' created successfully.")

def handle_start_timer(state: AppState):
    tasks = list_tasks(state)
    if not tasks:
        return
    
    try:
        choice = int(input("Select task # to start: ")) - 1
        if 0 <= choice < len(tasks):
            task = tasks[choice]
            session = logic.start_timer_for_task(state, task.id)
            print(f"\nStarted timer for '{task.title}' at {session.start_time}")
            print(f"Session ID: {session.id}")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def handle_stop_timer(state: AppState):
    # Find active sessions (those with end_time is None)
    active_sessions = [s for s in state.sessions.values() if s.end_time is None]
    
    if not active_sessions:
        print("\nNo active timers running.")
        return

    print("\n--- Active Sessions ---")
    for idx, s in enumerate(active_sessions):
        task_title = state.tasks[s.task_id].title if s.task_id in state.tasks else "Unknown Task"
        start_dt = datetime.fromisoformat(s.start_time)
        print(f"{idx + 1}) {task_title} (Started: {start_dt.strftime('%H:%M:%S')})")

    try:
        choice = int(input("Select session # to stop: ")) - 1
        if 0 <= choice < len(active_sessions):
            session = active_sessions[choice]
            updated_session = logic.stop_timer_for_session(state, session.id)
            
            # Duration formatting
            mins = updated_session.duration_seconds // 60
            print(f"\nTimer stopped! Duration: {mins} minutes.")
            
            # Check if associated task exists for feedback
            task = state.tasks.get(updated_session.task_id)
            if task:
                print(f"Gained {task.xp_reward} XP and {task.point_reward} Points.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def handle_amca_action(state: AppState):
    print("\n--- Amca Action (Quick Win) ---")
    try:
        xp = int(input("XP Value (default 10): ") or "10")
        note = input("Note (optional): ").strip()
        note = note if note else None
        
        logic.add_amca_action(state, xp_reward=xp, note=note)
        print(f"Amca action recorded! +{xp} XP.")
    except ValueError:
        print("Invalid input.")

def handle_update_streak(state: AppState):
    """Manually trigger streak check for 'today' for demo purposes."""
    today = datetime.now().date()
    old_streak = state.profile.streak_days
    logic.update_streak_for_date(state, today)
    new_streak = state.profile.streak_days
    
    if new_streak > old_streak:
        print(f"Streak increased! Now at {new_streak} days.")
    elif new_streak == 0 and old_streak > 0:
        print("Streak reset to 0 (Requirements not met).")
    else:
        print(f"Streak updated. Current: {new_streak} days.")

def main():
    print("Initializing Life Gamification App (v2)...")
    state = storage.load_state()
    
    # Ensure level name is correct on load
    state.profile.level_name = logic.get_level_name(state.profile.level)

    while True:
        print_status_bar(state)
        print("\n1) Show Summary")
        print("2) Create New Task")
        print("3) Start Timer")
        print("4) Stop Timer")
        print("5) Quick Amca Action")
        print("6) Update Streak (Check Today)")
        print("7) Save and Exit")
        
        choice = input("Select: ").strip()
        
        if choice == "1":
            print_summary(state)
        elif choice == "2":
            handle_add_task(state)
        elif choice == "3":
            handle_start_timer(state)
        elif choice == "4":
            handle_stop_timer(state)
        elif choice == "5":
            handle_amca_action(state)
        elif choice == "6":
            handle_update_streak(state)
        elif choice == "7":
            storage.save_state(state)
            print("State saved. Goodbye!")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()