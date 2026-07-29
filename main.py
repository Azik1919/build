"""Анти-Холодильник — Динамический график дня (Android / Telegram Style)."""

from __future__ import annotations

import threading
import time

import flet as ft

from store import AppStore, min_to_str, sync_triple

PX_PER_HOUR = 48  # Высота одного часа в сетке календаря

COLORS = {
    "bg": "#0e1621",          # Telegram Dark BG
    "surface": "#17212b",     # Telegram Card BG
    "surface_light": "#232e3c",
    "accent": "#5288c1",      # Telegram Blue Accent
    "accent_green": "#4fae5e",# Telegram Success Green
    "accent_red": "#e53935",  # Telegram Red
    "accent_yellow": "#f5a623",
    "text": "#ffffff",
    "muted": "#7f8c8d",
    "border": "#2b394a",
}


def main(page: ft.Page):
    page.title = "Анти-Холодильник"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = COLORS["bg"]

    store = AppStore()
    body = ft.Container(expand=True)
    is_processing = False  # Защита от частых кликов

    def refresh():
        idx = page.navigation_bar.selected_index if page.navigation_bar else 0
        if idx == 0:
            body.content = build_timeline_tab()
        elif idx == 1:
            body.content = build_constructor_tab()
        else:
            body.content = build_settings_tab()
        page.update()

    # ------------------------------------------------------------------ HELPERS
    def show_snack(text: str):
        snack = ft.SnackBar(
            content=ft.Text(text, color="#ffffff"),
            bgcolor=COLORS["surface_light"],
            duration=3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # Универсальные функции для работы с диалогами (работают во всех версиях Flet)
    def open_dialog(dlg: ft.AlertDialog):
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def close_dialog(dlg: ft.AlertDialog):
        dlg.open = False
        page.update()

    def hour_picker(label: str, initial_min: int, on_pick):
        h, m = initial_min // 60, initial_min % 60
        hour_dd = ft.Dropdown(
            label="Час",
            width=90,
            value=str(h),
            options=[ft.dropdown.Option(str(i)) for i in range(24)],
        )
        min_dd = ft.Dropdown(
            label="Мин",
            width=90,
            value=str(m),
            options=[ft.dropdown.Option(str(i)) for i in range(0, 60, 5)],
        )

        dlg = ft.AlertDialog(
            title=ft.Text(f"⏰ {label}", color=COLORS["text"]),
            content=ft.Row([hour_dd, min_dd], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=COLORS["surface"],
        )

        def apply(_):
            close_dialog(dlg)
            picked = int(hour_dd.value) * 60 + int(min_dd.value)
            on_pick(picked)

        dlg.actions = [
            ft.TextButton("Отмена", on_click=lambda _: close_dialog(dlg)),
            ft.ElevatedButton("OK", on_click=apply, bgcolor=COLORS["accent"], color="#fff"),
        ]

        open_dialog(dlg)

    def sync_editor(
        title: str,
        name: str,
        parent_hours: float,
        from_min: int,
        to_min: int,
        percent: float,
        hours: float,
        on_save,
    ):
        state = {"from_min": from_min, "to_min": to_min, "percent": percent, "hours": hours, "source": "hours"}
        name_field = ft.TextField(label="Название", value=name, autofocus=True, border_color=COLORS["border"])
        percent_field = ft.TextField(label="% дня/родителю", value=str(percent), keyboard_type=ft.KeyboardType.NUMBER, border_color=COLORS["border"])
        hours_field = ft.TextField(label="Часы", value=str(hours), keyboard_type=ft.KeyboardType.NUMBER, border_color=COLORS["border"])
        time_label = ft.Text(f"{min_to_str(from_min)} — {min_to_str(to_min)}", color=COLORS["accent"], weight=ft.FontWeight.BOLD)
        calc_label = ft.Text("", size=12, color=COLORS["muted"])

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["surface"],
            title=ft.Text(title, color=COLORS["text"]),
        )

        def apply_sync(source: str):
            try:
                p = float(percent_field.value.replace(",", "."))
                h = float(hours_field.value.replace(",", "."))
            except ValueError:
                return
            fm, tm, np, nh = sync_triple(
                parent_hours=parent_hours,
                from_min=state["from_min"],
                to_min=state["to_min"],
                percent=p,
                hours=h,
                source=source,
            )
            state.update(from_min=fm, to_min=tm, percent=np, hours=nh, source=source)
            percent_field.value = str(np)
            hours_field.value = str(nh)
            time_label.value = f"{min_to_str(fm)} — {min_to_str(tm)}"
            calc_label.value = f"= {nh} ч ({np}% от {parent_hours:.1f} ч)"
            page.update()

        percent_field.on_change = lambda _: apply_sync("percent")
        hours_field.on_change = lambda _: apply_sync("hours")

        def pick_from(_):
            hour_picker("Начало", state["from_min"], lambda v: (state.update(from_min=v), apply_sync("time")))

        def pick_to(_):
            hour_picker("Конец", state["to_min"], lambda v: (state.update(to_min=v), apply_sync("time")))

        def save(_):
            if not name_field.value.strip():
                return
            close_dialog(dlg)
            on_save(name_field.value.strip(), state)

        dlg.content = ft.Container(
            width=340,
            content=ft.Column(
                [
                    ft.Text("Задайте время или длительность:", size=11, color=COLORS["muted"]),
                    name_field,
                    ft.Row(
                        [
                            ft.OutlinedButton(f"От {min_to_str(state['from_min'])}", on_click=pick_from),
                            ft.OutlinedButton(f"До {min_to_str(state['to_min'])}", on_click=pick_to),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    time_label,
                    percent_field,
                    hours_field,
                    calc_label,
                ],
                tight=True,
                spacing=10,
            ),
        )
        dlg.actions = [
            ft.TextButton("Отмена", on_click=lambda _: close_dialog(dlg)),
            ft.ElevatedButton("Сохранить", on_click=save, bgcolor=COLORS["accent"], color="#fff"),
        ]

        apply_sync("hours")
        open_dialog(dlg)

    # ------------------------------------------------------------------ TAB 1: CALENDAR TIMELINE
    def build_timeline_tab():
        day = store.selected_day()
        stats = store.analytics(day)

        # Шапка выбора дней
        day_buttons = []
        for d in store.days:
            active = d.id == store.selected_day_id

            def pick(_=None, day_id=d.id):
                store.selected_day_id = day_id
                store.save()
                refresh()

            day_buttons.append(
                ft.Container(
                    content=ft.Text(d.label, color=COLORS["text"] if active else COLORS["muted"], weight=ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL),
                    padding=ft.Padding(16, 8, 16, 8),
                    bgcolor=COLORS["accent"] if active else COLORS["surface"],
                    border_radius=20,
                    on_click=pick,
                )
            )

        # Календарная сетка по часам (24 часа)
        calendar_hours = []
        for h in range(24):
            calendar_hours.append(
                ft.Container(
                    height=PX_PER_HOUR,
                    content=ft.Row(
                        [
                            ft.Text(f"{h:02d}:00", size=11, color=COLORS["muted"], width=45),
                            ft.Container(expand=True, height=1, bgcolor=COLORS["border"]),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                )
            )

        # Плитки событий поверх часов
        event_tiles = []
        for comp in day.compartments:
            top_offset = (comp.from_min / 60) * PX_PER_HOUR
            height = max(36, comp.hours * PX_PER_HOUR)

            tile_color = COLORS["accent_green"] if comp.is_active else COLORS["surface_light"]
            if comp.overtime_min > 0:
                tile_color = COLORS["accent_yellow"]

            event_tiles.append(
                ft.Container(
                    top=top_offset,
                    left=55,
                    height=height,
                    width=250,
                    bgcolor=tile_color,
                    border_radius=10,
                    padding=8,
                    content=ft.Column(
                        [
                            ft.Text(f"📦 {comp.name}", weight=ft.FontWeight.BOLD, size=12, color="#fff", overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{min_to_str(comp.from_min)} — {min_to_str(comp.to_min)} ({comp.hours:.1f}ч)", size=10, color="#ffffffcc"),
                        ],
                        spacing=2,
                    ),
                )
            )

        calendar_stack = ft.Stack(
            controls=[
                ft.Column(calendar_hours, spacing=0),
                *event_tiles,
            ],
            height=24 * PX_PER_HOUR,
        )

        # Панель активного элемента
        live_panel = ft.Container()
        if day.label.startswith("Сегодня") or day.id == store.days[-1].id:
            store.ensure_active_chain()
            live_controls = [ft.Text("⚡ Текущий прогресс", size=14, weight=ft.FontWeight.BOLD, color=COLORS["accent"])]
            
            for comp in day.compartments:
                if comp.is_active:
                    live_controls.append(ft.Text(f"📦 {comp.name}", weight=ft.FontWeight.BOLD, color=COLORS["text"]))
                    for task in comp.tasks:
                        if task.is_active:
                            live_controls.append(
                                ft.Text(
                                    f"  🔹 {task.name}: {int(task.accumulated_min)} / {int(task.planned_min)} мин",
                                    size=12,
                                    color=COLORS["muted"],
                                )
                            )

                            def finish_t(_, cid=comp.id, tid=task.id):
                                nonlocal is_processing
                                if is_processing: return
                                is_processing = True
                                store.finish_task(cid, tid)
                                is_processing = False
                                refresh()

                            live_controls.append(
                                ft.ElevatedButton("⏹ Завершить задачу", bgcolor=COLORS["accent_yellow"], color="#000", on_click=finish_t)
                            )

                    def finish_c(_, cid=comp.id):
                        nonlocal is_processing
                        if is_processing: return
                        is_processing = True
                        store.finish_compartment(cid)
                        is_processing = False
                        refresh()
                        show_snack(f'Отсек «{comp.name}» завершён!')

                    live_controls.append(
                        ft.ElevatedButton("⏹ Завершить отсек", bgcolor=COLORS["accent_red"], color="#fff", on_click=finish_c)
                    )

            live_panel = ft.Container(
                padding=12,
                bgcolor=COLORS["surface"],
                border_radius=14,
                margin=ft.Margin(0, 0, 0, 10),
                content=ft.Column(live_controls, spacing=8),
            )

        # Блок статистики внизу
        suggestions = stats["suggestions"]
        analysis_card = ft.Container(
            padding=14,
            bgcolor=COLORS["surface"],
            border_radius=14,
            margin=ft.Margin(0, 10, 0, 0),
            content=ft.Column(
                [
                    ft.Text(f"📊 Статистика дня — {day.label}", weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Row(
                        [
                            ft.Text(f"🟢 В плане: {stats['green_pct']}%", color=COLORS["accent_green"], size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"🟡 Задержка: {stats['yellow_pct']}%", color=COLORS["accent_yellow"], size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"🔴 Переработка: {stats['red_pct']}%", color=COLORS["accent_red"], size=12, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(color=COLORS["border"]),
                    ft.Text("Рекомендации по времени:", size=11, color=COLORS["muted"]),
                    *(
                        [ft.Text(f"• {s['hint']} (+{s['overtime_min']} мин)", size=11, color=COLORS["accent_yellow"]) for s in suggestions]
                        if suggestions
                        else [ft.Text("Всё идёт точно по графику 🟢", size=11, color=COLORS["accent_green"])]
                    ),
                ],
                spacing=8,
            ),
        )

        return ft.Container(
            padding=12,
            content=ft.Column(
                [
                    ft.Text("📅 Календарь дня", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Container(content=ft.Row(day_buttons, scroll=ft.ScrollMode.AUTO), padding=ft.Padding(0, 0, 0, 10)),
                    live_panel,
                    ft.Text("Сетка по часам:", size=12, color=COLORS["muted"]),
                    ft.Container(
                        content=ft.ListView([calendar_stack], height=380),
                        border_radius=12,
                        bgcolor=COLORS["surface"],
                        padding=10,
                    ),
                    analysis_card,
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    # ------------------------------------------------------------------ TAB 2: CONSTRUCTOR
    def build_constructor_tab():
        day = store.selected_day()
        cards = []

        def edit_comp(comp):
            sync_editor(
                "✏️ Изменить отсек",
                comp.name,
                parent_hours=24,
                from_min=comp.from_min,
                to_min=comp.to_min,
                percent=comp.percent,
                hours=comp.hours,
                on_save=lambda name, st: (store.update_entity("compartment", comp.id, {"name": name, **st}), refresh()),
            )

        def edit_task(comp, task):
            sync_editor(
                "✏️ Изменить задачу",
                task.name,
                parent_hours=comp.hours,
                from_min=task.from_min,
                to_min=task.to_min,
                percent=task.percent,
                hours=task.hours,
                on_save=lambda name, st: (store.update_entity("task", comp.id, {"name": name, **st}, task_id=task.id), refresh()),
            )

        def add_comp(_):
            sync_editor(
                "➕ Новый отсек",
                "Новый отсек",
                parent_hours=24,
                from_min=540,
                to_min=660,
                percent=16.7,
                hours=2.0,
                on_save=lambda name, st: (store.add_compartment(name, st["from_min"], st["percent"], st["hours"]), refresh()),
            )

        for comp in day.compartments:
            task_rows = []
            for task in comp.tasks:
                task_rows.append(
                    ft.Container(
                        padding=8,
                        bgcolor=COLORS["surface_light"],
                        border_radius=8,
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(f"🔹 {task.name}", weight=ft.FontWeight.W_500, color=COLORS["text"]),
                                        ft.Text(f"{min_to_str(task.from_min)}–{min_to_str(task.to_min)} | {task.hours}ч", size=10, color=COLORS["muted"]),
                                    ],
                                    expand=True,
                                    spacing=2,
                                ),
                                ft.IconButton(ft.Icons.EDIT, icon_color=COLORS["accent"], icon_size=18, on_click=lambda _, c=comp, t=task: edit_task(c, t)),
                                ft.IconButton(ft.Icons.DELETE, icon_color=COLORS["accent_red"], icon_size=18, on_click=lambda _, c=comp, t=task: (store.delete_entity("task", c.id, t.id), refresh())),
                            ]
                        ),
                    )
                )

            cards.append(
                ft.Container(
                    padding=12,
                    bgcolor=COLORS["surface"],
                    border_radius=12,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(f"📦 {comp.name}", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text"], expand=True),
                                    ft.IconButton(ft.Icons.EDIT, icon_color=COLORS["accent"], on_click=lambda _, c=comp: edit_comp(c)),
                                    ft.IconButton(ft.Icons.DELETE, icon_color=COLORS["accent_red"], on_click=lambda _, c=comp: (store.delete_entity("compartment", c.id), refresh())),
                                ]
                            ),
                            ft.Text(f"{min_to_str(comp.from_min)}–{min_to_str(comp.to_min)} | {comp.hours}ч ({comp.percent}% дня)", size=11, color=COLORS["muted"]),
                            ft.TextButton(
                                "➕ Задача",
                                icon=ft.Icons.ADD,
                                icon_color=COLORS["accent"],
                                on_click=lambda _, c=comp: sync_editor(
                                    "➕ Задача",
                                    "Новая задача",
                                    parent_hours=c.hours,
                                    from_min=c.from_min,
                                    to_min=c.from_min + 60,
                                    percent=50,
                                    hours=c.hours * 0.5,
                                    on_save=lambda name, st: (store.add_task(c.id, name, st["from_min"], st["percent"], st["hours"]), refresh()),
                                ),
                            ),
                            *task_rows,
                        ],
                        spacing=6,
                    ),
                )
            )

        return ft.Container(
            padding=12,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("✍️ Конструктор", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"], expand=True),
                            ft.ElevatedButton("➕ Отсек", icon=ft.Icons.ADD, bgcolor=COLORS["accent"], color="#fff", on_click=add_comp),
                        ]
                    ),
                    ft.Text("Нажмите на элемент для редактирования времени", size=12, color=COLORS["muted"]),
                    ft.Divider(color=COLORS["border"]),
                    ft.Column(cards if cards else [ft.Text("Список пуст. Добавьте отсек.", color=COLORS["muted"])], spacing=10),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    # ------------------------------------------------------------------ TAB 3: SETTINGS
    def build_settings_tab():
        return ft.Container(
            padding=12,
            content=ft.Column(
                [
                    ft.Text("⚙️ Настройки", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Divider(color=COLORS["border"]),
                    ft.ListTile(leading=ft.Icon(ft.Icons.PERSON, color=COLORS["accent"]), title=ft.Text("Профиль Telegram", color=COLORS["text"])),
                    ft.ListTile(leading=ft.Icon(ft.Icons.NOTIFICATIONS, color=COLORS["accent"]), title=ft.Text("Уведомления", color=COLORS["text"])),
                    ft.Divider(color=COLORS["border"]),
                    ft.ElevatedButton(
                        "🧹 Сбросить данные",
                        icon=ft.Icons.DELETE_FOREVER,
                        bgcolor=COLORS["surface_light"],
                        color=COLORS["accent_red"],
                        on_click=lambda _: reset_day(),
                    ),
                ],
                expand=True,
            ),
        )

    def reset_day():
        from pathlib import Path

        p = Path(__file__).parent / "anti_fridge_data.json"
        if p.exists():
            p.unlink()
        store.days.clear()
        store._seed_demo()
        store.save()
        refresh()

    # ------------------------------------------------------------------ NAVIGATION
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor=COLORS["surface"],
        indicator_color=COLORS["accent"],
        on_change=lambda _: refresh(),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH, label="Календарь"),
            ft.NavigationBarDestination(icon=ft.Icons.EDIT, label="Конструктор"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Настройки"),
        ],
    )

    def tick_loop():
        while True:
            time.sleep(3)
            try:
                msgs = store.tick()
                if msgs:
                    for msg in msgs:
                        show_snack(msg)
                    refresh()
            except Exception:
                break

    page.add(body)
    refresh()
    threading.Thread(target=tick_loop, daemon=True).start()


if __name__ == "__main__":
    ft.app(target=main)
