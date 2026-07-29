"""Хранилище и движок «Анти-Холодильник»."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Optional

DATA_FILE = Path(__file__).parent / "anti_fridge_data.json"
DAY_MINUTES = 24 * 60


def min_to_str(total_min: int) -> str:
    total_min = int(total_min) % DAY_MINUTES
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def str_to_min(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 2:
        return 0
    try:
        h, m = int(parts[0]), int(parts[1])
        return max(0, min(DAY_MINUTES - 1, h * 60 + m))
    except ValueError:
        return 0


def sync_triple(
    *,
    parent_hours: float,
    from_min: int,
    to_min: int,
    percent: float,
    hours: float,
    source: str,
) -> tuple[int, int, float, float]:
    """Синхронизирует время, проценты и часы относительно родителя."""
    parent_hours = max(parent_hours, 0.01)
    parent_min = parent_hours * 60

    if source == "percent":
        hours = parent_hours * percent / 100
        duration = int(round(hours * 60))
        to_min = from_min + duration
    elif source == "hours":
        percent = hours / parent_hours * 100
        duration = int(round(hours * 60))
        to_min = from_min + duration
    else:  # time
        duration = max(15, to_min - from_min)
        hours = duration / 60
        percent = hours / parent_hours * 100

    percent = max(0.1, min(100.0, percent))
    hours = max(0.1, min(parent_hours, hours))
    to_min = from_min + int(round(hours * 60))
    return from_min, to_min, round(percent, 1), round(hours, 2)


@dataclass
class Subtask:
    id: int
    name: str
    from_min: int = 540
    to_min: int = 600
    percent: float = 50.0
    hours: float = 1.0

    @classmethod
    def create(cls, uid: int, name: str, from_min: int, parent_hours: float, percent: float = 25.0):
        hours = parent_hours * percent / 100
        to_min = from_min + int(round(hours * 60))
        return cls(uid, name, from_min, to_min, percent, hours)


@dataclass
class Task:
    id: int
    name: str
    from_min: int = 540
    to_min: int = 660
    percent: float = 50.0
    hours: float = 2.0
    is_active: bool = False
    is_completed: bool = False
    accumulated_min: float = 0.0
    start_ts: Optional[float] = None
    overtime_min: float = 0.0
    notified_end: bool = False
    subtasks: list[Subtask] = field(default_factory=list)

    @property
    def planned_min(self) -> float:
        return self.hours * 60

    @classmethod
    def create(cls, uid: int, name: str, from_min: int, parent_hours: float, percent: float = 50.0):
        hours = parent_hours * percent / 100
        to_min = from_min + int(round(hours * 60))
        return cls(uid, name, from_min, to_min, percent, hours)


@dataclass
class Compartment:
    id: int
    name: str
    from_min: int = 540
    to_min: int = 780
    percent: float = 16.7
    hours: float = 4.0
    is_active: bool = False
    is_completed: bool = False
    accumulated_min: float = 0.0
    start_ts: Optional[float] = None
    overtime_min: float = 0.0
    notified_end: bool = False
    tasks: list[Task] = field(default_factory=list)

    @property
    def planned_min(self) -> float:
        return self.hours * 60

    @classmethod
    def create(cls, uid: int, name: str, from_min: int, percent: float = 16.7):
        hours = DAY_MINUTES / 60 * percent / 100
        to_min = from_min + int(round(hours * 60))
        task = Task.create(uid + 1, "Главная задача", from_min, hours, 60)
        task.subtasks = [
            Subtask.create(uid + 2, "Шаг 1", from_min, task.hours, 50),
            Subtask.create(uid + 3, "Шаг 2", from_min + int(task.hours * 30), task.hours, 50),
        ]
        return cls(uid, name, from_min, to_min, percent, hours, tasks=[task])


@dataclass
class DayPlan:
    id: str
    label: str
    compartments: list[Compartment] = field(default_factory=list)
    green_pct: float = 0.0
    yellow_pct: float = 0.0
    red_pct: float = 0.0

    def recompute_stats(self):
        total = self.green_pct + self.yellow_pct + self.red_pct
        if total <= 0:
            self.green_pct, self.yellow_pct, self.red_pct = 60.0, 25.0, 15.0


class AppStore:
    def __init__(self):
        self.days: list[DayPlan] = []
        self.selected_day_id: str = ""
        self.next_id: int = 10
        self.on_change: Optional[Callable[[], None]] = None
        self._load()

    def _new_id(self) -> int:
        self.next_id += 1
        return self.next_id

    def selected_day(self) -> DayPlan:
        for d in self.days:
            if d.id == self.selected_day_id:
                return d
        return self.days[0]

    def _load(self):
        if DATA_FILE.exists():
            raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            self.days = [self._day_from_dict(d) for d in raw.get("days", [])]
            self.selected_day_id = raw.get("selected_day_id", "")
            self.next_id = raw.get("next_id", 10)
        else:
            self._seed_demo()
        if not self.days:
            self._seed_demo()
        if not self.selected_day_id:
            self.selected_day_id = self.days[-1].id

    def _seed_demo(self):
        today = date.today()
        day_id = today.isoformat()
        comp1 = Compartment.create(1, "Работа", 600, percent=16.7)
        comp1.tasks = [
            Task.create(2, "Созвоны", 600, comp1.hours, 25),
            Task.create(3, "Код", 720, comp1.hours, 50),
            Task.create(4, "Почта", 840, comp1.hours, 25),
        ]
        for t in comp1.tasks:
            t.subtasks = [
                Subtask.create(self._new_id(), f"{t.name} — шаг 1", t.from_min, t.hours, 50),
                Subtask.create(self._new_id(), f"{t.name} — шаг 2", t.from_min + int(t.hours * 30), t.hours, 50),
            ]

        comp2 = Compartment.create(5, "Учёба", 960, percent=12.5)
        comp2.tasks = [Task.create(6, "Теория", 960, comp2.hours, 50), Task.create(7, "Практика", 1080, comp2.hours, 50)]

        self.days = [
            DayPlan("2026-07-19", "19 Июля"),
            DayPlan("2026-07-20", "20 Июля"),
            DayPlan(day_id, "Сегодня", [comp1, comp2]),
        ]
        self.days[-1].recompute_stats()
        self.selected_day_id = day_id

    def save(self):
        payload = {
            "days": [self._day_to_dict(d) for d in self.days],
            "selected_day_id": self.selected_day_id,
            "next_id": self.next_id,
        }
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.on_change:
            self.on_change()

    def add_compartment(self, name: str, from_min: int, percent: float, hours: float):
        day = self.selected_day()
        uid = self._new_id()
        comp = Compartment.create(uid, name, from_min, percent)
        comp.from_min, comp.to_min, comp.percent, comp.hours = sync_triple(
            parent_hours=DAY_MINUTES / 60,
            from_min=from_min,
            to_min=from_min + int(hours * 60),
            percent=percent,
            hours=hours,
            source="hours",
        )
        day.compartments.append(comp)
        self.save()

    def add_task(self, comp_id: int, name: str, from_min: int, percent: float, hours: float):
        comp = self._find_comp(comp_id)
        if not comp:
            return
        uid = self._new_id()
        task = Task.create(uid, name, from_min, comp.hours, percent)
        task.from_min, task.to_min, task.percent, task.hours = sync_triple(
            parent_hours=comp.hours,
            from_min=from_min,
            to_min=from_min + int(hours * 60),
            percent=percent,
            hours=hours,
            source="hours",
        )
        comp.tasks.append(task)
        self.save()

    def add_subtask(self, comp_id: int, task_id: int, name: str, from_min: int, percent: float, hours: float):
        task = self._find_task(comp_id, task_id)
        if not task:
            return
        uid = self._new_id()
        sub = Subtask.create(uid, name, from_min, task.hours, percent)
        sub.from_min, sub.to_min, sub.percent, sub.hours = sync_triple(
            parent_hours=task.hours,
            from_min=from_min,
            to_min=from_min + int(hours * 60),
            percent=percent,
            hours=hours,
            source="hours",
        )
        task.subtasks.append(sub)
        self.save()

    def update_entity(self, kind: str, comp_id: int, data: dict, task_id: Optional[int] = None, sub_id: Optional[int] = None):
        if kind == "compartment":
            comp = self._find_comp(comp_id)
            if not comp:
                return
            parent_h = DAY_MINUTES / 60
            comp.name = data["name"]
            comp.from_min, comp.to_min, comp.percent, comp.hours = sync_triple(
                parent_hours=parent_h,
                from_min=data["from_min"],
                to_min=data["to_min"],
                percent=data["percent"],
                hours=data["hours"],
                source=data["source"],
            )
        elif kind == "task":
            comp = self._find_comp(comp_id)
            task = self._find_task(comp_id, task_id)
            if not comp or not task:
                return
            task.name = data["name"]
            task.from_min, task.to_min, task.percent, task.hours = sync_triple(
                parent_hours=comp.hours,
                from_min=data["from_min"],
                to_min=data["to_min"],
                percent=data["percent"],
                hours=data["hours"],
                source=data["source"],
            )
        elif kind == "subtask":
            task = self._find_task(comp_id, task_id)
            if not task:
                return
            sub = next((s for s in task.subtasks if s.id == sub_id), None)
            if not sub:
                return
            sub.name = data["name"]
            sub.from_min, sub.to_min, sub.percent, sub.hours = sync_triple(
                parent_hours=task.hours,
                from_min=data["from_min"],
                to_min=data["to_min"],
                percent=data["percent"],
                hours=data["hours"],
                source=data["source"],
            )
        self.save()

    def delete_entity(self, kind: str, comp_id: int, task_id: Optional[int] = None, sub_id: Optional[int] = None):
        day = self.selected_day()
        if kind == "compartment":
            day.compartments = [c for c in day.compartments if c.id != comp_id]
        elif kind == "task":
            comp = self._find_comp(comp_id)
            if comp:
                comp.tasks = [t for t in comp.tasks if t.id != task_id]
        elif kind == "subtask":
            task = self._find_task(comp_id, task_id)
            if task:
                task.subtasks = [s for s in task.subtasks if s.id != sub_id]
        self.save()

    def ensure_active_chain(self):
        """Авто-старт первого незавершённого отсека и задачи."""
        day = self.selected_day()
        if any(c.is_active for c in day.compartments):
            return
        for comp in day.compartments:
            if comp.is_completed:
                continue
            comp.is_active = True
            comp.start_ts = time.time()
            for task in comp.tasks:
                if not task.is_completed:
                    task.is_active = True
                    task.start_ts = time.time()
                    break
            break
        self.save()

    def tick(self) -> list[str]:
        """Обновляет фактическое время и возвращает сообщения для уведомлений."""
        messages: list[str] = []
        now = time.time()
        day = self.selected_day()

        for comp in day.compartments:
            if comp.is_active and comp.start_ts:
                elapsed = (now - comp.start_ts) / 60
                comp.accumulated_min += elapsed
                comp.start_ts = now

                if comp.accumulated_min > comp.planned_min:
                    comp.overtime_min = comp.accumulated_min - comp.planned_min
                    if not comp.notified_end:
                        comp.notified_end = True
                        messages.append(f'⏰ Отсек «{comp.name}» — время вышло! Нажми «Завершить» или идёт переработка 🔴')

            for task in comp.tasks:
                if task.is_active and task.start_ts:
                    elapsed = (now - task.start_ts) / 60
                    task.accumulated_min += elapsed
                    task.start_ts = now

                    if task.accumulated_min > task.planned_min:
                        task.overtime_min = task.accumulated_min - task.planned_min
                        if not task.notified_end:
                            task.notified_end = True
                            messages.append(f'⏰ Задача «{task.name}» — время вышло! Нажми «Завершить» 🟡')

        self._update_day_stats(day)
        return messages

    def finish_task(self, comp_id: int, task_id: int):
        comp = self._find_comp(comp_id)
        task = self._find_task(comp_id, task_id)
        if not comp or not task or not task.is_active:
            return

        now = time.time()
        if task.start_ts:
            task.accumulated_min += (now - task.start_ts) / 60
        task.is_active = False
        task.is_completed = True
        task.start_ts = None

        incomplete = [t for t in comp.tasks if not t.is_completed]
        if incomplete:
            comp_budget = comp.planned_min
            spent = sum(t.accumulated_min for t in comp.tasks if t.is_completed)
            remaining = max(0.0, comp_budget - spent)
            share = remaining / len(incomplete)
            cursor = comp.from_min + int(spent)

            for t in incomplete:
                t.hours = round(share / 60, 2)
                t.percent = round(t.hours / comp.hours * 100, 1) if comp.hours else 33.3
                t.from_min = cursor
                t.to_min = cursor + int(round(share))
                t.overtime_min = 0
                t.notified_end = False
                cursor = t.to_min

            incomplete[0].is_active = True
            incomplete[0].start_ts = now

        self.save()

    def finish_compartment(self, comp_id: int):
        comp = self._find_comp(comp_id)
        if not comp or not comp.is_active:
            return

        now = time.time()
        if comp.start_ts:
            comp.accumulated_min += (now - comp.start_ts) / 60
        comp.is_active = False
        comp.is_completed = True
        comp.start_ts = None

        for task in comp.tasks:
            if task.is_active:
                if task.start_ts:
                    task.accumulated_min += (now - task.start_ts) / 60
                task.is_active = False
                task.start_ts = None

        day = self.selected_day()
        incomplete = [c for c in day.compartments if not c.is_completed]
        if incomplete:
            day_budget = DAY_MINUTES
            spent = sum(c.accumulated_min for c in day.compartments if c.is_completed)
            remaining = max(0.0, day_budget - spent)
            share = remaining / len(incomplete)
            cursor = int(spent)

            for c in incomplete:
                c.hours = round(share / 60, 2)
                c.percent = round(c.hours / 24 * 100, 1)
                c.from_min = cursor
                c.to_min = cursor + int(round(share))
                c.overtime_min = 0
                c.notified_end = False
                cursor = c.to_min

            nxt = incomplete[0]
            nxt.is_active = True
            nxt.start_ts = now
            for task in nxt.tasks:
                if not task.is_completed:
                    task.is_active = True
                    task.start_ts = now
                    break

        self.save()

    def analytics(self, day: DayPlan) -> dict:
        """Анализ: какие задачи просят больше времени."""
        suggestions = []
        yellow = red = green = 0

        for comp in day.compartments:
            if comp.overtime_min > 0 or comp.accumulated_min > comp.planned_min:
                red += 1
            elif comp.is_completed:
                green += 1

            for task in comp.tasks:
                if task.overtime_min > 0:
                    yellow += 1
                    suggestions.append(
                        {
                            "name": task.name,
                            "compartment": comp.name,
                            "overtime_min": int(task.overtime_min),
                            "hint": f"Увеличь % для «{task.name}» в отсеке «{comp.name}»",
                        }
                    )
                elif task.is_completed and task.accumulated_min <= task.planned_min:
                    green += 1

        total = max(1, green + yellow + red)
        return {
            "green_pct": round(green / total * 100),
            "yellow_pct": round(yellow / total * 100),
            "red_pct": round(red / total * 100),
            "suggestions": sorted(suggestions, key=lambda x: x["overtime_min"], reverse=True)[:5],
        }

    def _update_day_stats(self, day: DayPlan):
        stats = self.analytics(day)
        day.green_pct = stats["green_pct"]
        day.yellow_pct = stats["yellow_pct"]
        day.red_pct = stats["red_pct"]

    def _find_comp(self, comp_id: int) -> Optional[Compartment]:
        for c in self.selected_day().compartments:
            if c.id == comp_id:
                return c
        return None

    def _find_task(self, comp_id: int, task_id: Optional[int]) -> Optional[Task]:
        comp = self._find_comp(comp_id)
        if not comp or task_id is None:
            return None
        return next((t for t in comp.tasks if t.id == task_id), None)

    @staticmethod
    def _day_to_dict(day: DayPlan) -> dict:
        return {
            "id": day.id,
            "label": day.label,
            "green_pct": day.green_pct,
            "yellow_pct": day.yellow_pct,
            "red_pct": day.red_pct,
            "compartments": [AppStore._comp_to_dict(c) for c in day.compartments],
        }

    @staticmethod
    def _comp_to_dict(comp: Compartment) -> dict:
        d = asdict(comp)
        d["tasks"] = [AppStore._task_to_dict(t) for t in comp.tasks]
        return d

    @staticmethod
    def _task_to_dict(task: Task) -> dict:
        d = asdict(task)
        d["subtasks"] = [asdict(s) for s in task.subtasks]
        return d

    @staticmethod
    def _day_from_dict(raw: dict) -> DayPlan:
        day = DayPlan(raw["id"], raw["label"])
        day.green_pct = raw.get("green_pct", 0)
        day.yellow_pct = raw.get("yellow_pct", 0)
        day.red_pct = raw.get("red_pct", 0)
        day.compartments = [AppStore._comp_from_dict(c) for c in raw.get("compartments", [])]
        return day

    @staticmethod
    def _comp_from_dict(raw: dict) -> Compartment:
        comp = Compartment(**{k: v for k, v in raw.items() if k != "tasks"})
        comp.tasks = [AppStore._task_from_dict(t) for t in raw.get("tasks", [])]
        return comp

    @staticmethod
    def _task_from_dict(raw: dict) -> Task:
        task = Task(**{k: v for k, v in raw.items() if k != "subtasks"})
        task.subtasks = [Subtask(**s) for s in raw.get("subtasks", [])]
        return task
