import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Stat:
    name: str
    total_seconds: int = 0

    def add_seconds(self, seconds: int) -> None:
        self.total_seconds += seconds

    def level(self) -> int:
        # 1 level per 10 hours. 10 hours = 36000 seconds.
        # Assuming level starts at 1.
        return 1 + (self.total_seconds // 36000)

    def progress_to_next_level(self) -> float:
        # Returns a float between 0.0 and 1.0
        seconds_in_current_level = self.total_seconds % 36000
        return seconds_in_current_level / 36000.0


@dataclass
class Profile:
    xp: int = 0
    level: int = 1
    level_name: str = "Novice"
    points: int = 0
    streak_days: int = 0
    streak_freezes: int = 0
    badges: List[str] = field(default_factory=list)


@dataclass
class TaskTemplate:
    id: str
    title: str
    description: str
    category: str  # e.g. "yazılım", "general"
    recurrence: str  # "once", "daily", "weekly", "monthly", "custom"
    xp_reward: int
    point_reward: int
    target_minutes: Optional[int] = None
    stat_name: Optional[str] = None
    is_amca_task: bool = False


@dataclass
class TimerSession:
    id: str
    task_id: str
    start_time: str  # ISO datetime string
    duration_seconds: int = 0
    end_time: Optional[str] = None  # ISO datetime string


@dataclass
class AmcaAction:
    id: str
    timestamp: str  # ISO datetime string
    xp_reward: int
    note: Optional[str] = None


@dataclass
class Transaction:
    id: str
    timestamp: str
    amount: float
    category: str
    description: Optional[str] = None


@dataclass
class Wallet:
    balance: float = 0.0
    transactions: List[Transaction] = field(default_factory=list)


@dataclass
class BookProject:
    id: str
    title: str
    total_pages: int
    daily_target_pages: int
    pages_written: int = 0
    is_completed: bool = False


@dataclass
class DailyRoutineLog:
    date: str  # "YYYY-MM-DD"
    pages_written: int = 0
    zikr_count: int = 0
    income_amount: float = 0.0
    amca_count: int = 0
    wake_target_time: Optional[str] = None  # "HH:MM"
    wake_actual_time: Optional[str] = None  # "HH:MM"
    wake_penalty: float = 0.0


@dataclass
class MaterialGoal:
    id: str
    name: str
    image_path: str
    target_amount: float
    current_amount: float = 0.0


@dataclass
class Settings:
    monthly_income_target: float = 10000.0
    zikr_daily_target: int = 100
    min_amca_per_day: int = 1
    wake_penalty_per_minute: float = 1.0


@dataclass
class AppState:
    profile: Profile
    stats: Dict[str, Stat]
    tasks: Dict[str, TaskTemplate]
    sessions: Dict[str, TimerSession]
    amca_actions: List[AmcaAction]
    wallet: Wallet
    book_projects: Dict[str, BookProject]
    material_goals: Dict[str, MaterialGoal]
    daily_logs: Dict[str, DailyRoutineLog]
    settings: Settings