import flet as ft

def main(page: ft.Page):
    page.title = "Анти-Холодильник: 3 Столбца + Редактор"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10

    # -------------------------------------------------------------
    # ДАННЫЕ
    # -------------------------------------------------------------
    data_store = [
        {"day_label": "19 Июля", "slots": []},
        {"day_label": "20 Июля", "slots": []},
        {
            "day_label": "Сегодня (21 Июля)",
            "slots": [
                {
                    "id": 1,
                    "title": "Учеба и Код",
                    "from_h": "09:00",
                    "to_h": "13:00",
                    "percent": "50",
                    "hours": 4.0,
                    "tasks": [{"title": "Фронтенд Flet", "subtasks": ["Календарь", "Сетка 3-х столбцов"]}]
                },
                {
                    "id": 2,
                    "title": "Спорт и Отдых",
                    "from_h": "15:00",
                    "to_h": "17:00",
                    "percent": "25",
                    "hours": 2.0,
                    "tasks": [{"title": "Бег на улице", "subtasks": ["Разминка"]}]
                }
            ]
        }
    ]

    selected_day_idx = 2

    # -------------------------------------------------------------
    # ОКНО РЕДАКТИРОВАНИЯ / СОЗДАНИЯ (3 ЗНАЧЕНИЯ)
    # -------------------------------------------------------------
    def open_slot_editor(slot_to_edit=None):
        is_edit = slot_to_edit is not None

        title_field = ft.TextField(
            label="Название отсека", 
            value=slot_to_edit["title"] if is_edit else "Новый Отсек"
        )
        time_field = ft.TextField(
            label="1. Время (От - До)", 
            value=f"{slot_to_edit['from_h']} - {slot_to_edit['to_h']}" if is_edit else "10:00 - 12:00"
        )
        percent_field = ft.TextField(
            label="2. % От дня/отсека", 
            value=str(slot_to_edit["percent"]) if is_edit else "20"
        )
        calc_result = ft.Text(
            f"3. Вычисление: = {slot_to_edit['hours'] if is_edit else 2.0} часа", 
            size=14, color="#4fc3f7", weight=ft.FontWeight.BOLD
        )

        def recalculate(e):
            try:
                p = float(percent_field.value)
                calc_result.value = f"3. Вычисление: = {(p / 100) * 24:.1f} часа"
            except ValueError:
                calc_result.value = "3. Вычисление: = Ошибка ввода"
            page.update()

        time_field.on_change = recalculate
        percent_field.on_change = recalculate

        def save_slot(e):
            slots = data_store[selected_day_idx]["slots"]
            times = time_field.value.split("-")
            from_h = times[0].strip() if len(times) > 0 else "10:00"
            to_h = times[1].strip() if len(times) > 1 else "12:00"
            
            try:
                hrs = round((float(percent_field.value) / 100) * 24, 1)
            except ValueError:
                hrs = 2.0

            if is_edit:
                slot_to_edit["title"] = title_field.value
                slot_to_edit["from_h"] = from_h
                slot_to_edit["to_h"] = to_h
                slot_to_edit["percent"] = percent_field.value
                slot_to_edit["hours"] = hrs
            else:
                new_id = max([s["id"] for s in slots], default=0) + 1
                slots.append({
                    "id": new_id,
                    "title": title_field.value,
                    "from_h": from_h,
                    "to_h": to_h,
                    "percent": percent_field.value,
                    "hours": hrs,
                    "tasks": [{"title": "Новая задача", "subtasks": []}]
                })

            dialog.open = False
            render_current_tab()

        dialog = ft.AlertDialog(
            title=ft.Text("✏️ Редактор слота" if is_edit else "➕ Новый слот"),
            content=ft.Column([
                title_field,
                time_field,
                percent_field,
                ft.Divider(),
                calc_result
            ], tight=True),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: setattr(dialog, "open", False) or page.update()),
                ft.ElevatedButton("Сохранить", on_click=save_slot)
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # -------------------------------------------------------------
    # УДАЛЕНИЕ СЛОТА
    # -------------------------------------------------------------
    def delete_slot(slot_id):
        slots = data_store[selected_day_idx]["slots"]
        data_store[selected_day_idx]["slots"] = [s for s in slots if s["id"] != slot_id]
        render_current_tab()

    # -------------------------------------------------------------
    # ВКЛАДКА 1: КАЛЕНДАРЬ + СЕТКА
    # -------------------------------------------------------------
    def build_timeline_view():
        day_buttons = []
        for i, day_info in enumerate(data_store):
            is_sel = (i == selected_day_idx)
            def make_select(idx):
                return lambda e: select_day(idx)
            
            day_buttons.append(
                ft.ElevatedButton(
                    day_info["day_label"],
                    bgcolor="#4fc3f7" if is_sel else "#263238",
                    color="white" if is_sel else "#b0bec5",
                    on_click=make_select(i)
                )
            )

        def select_day(idx):
            nonlocal selected_day_idx
            selected_day_idx = idx
            render_current_tab()

        current_slots = data_store[selected_day_idx]["slots"]
        time_rows = []
        
        header_row = ft.Container(
            padding=5, bgcolor="#102a43",
            content=ft.Row([
                ft.Text("⏰ Время", width=60, size=11, weight=ft.FontWeight.BOLD),
                ft.Text("📦 1. Отсеки", expand=1, size=11, weight=ft.FontWeight.BOLD, color="#4fc3f7"),
                ft.Text("🔹 2. Задачи", expand=1, size=11, weight=ft.FontWeight.BOLD, color="#81c784"),
                ft.Text("└─ 3. Подзадачи", expand=1, size=11, weight=ft.FontWeight.BOLD, color="#ffb74d"),
            ])
        )
        time_rows.append(header_row)

        for hour in range(24):
            time_str = f"{hour:02d}:00"
            matched_slot = None
            for slot in current_slots:
                try:
                    start_h = int(slot["from_h"].split(":")[0])
                    end_h = int(slot["to_h"].split(":")[0])
                    if start_h <= hour < end_h:
                        matched_slot = slot
                        break
                except Exception:
                    pass

            if matched_slot:
                col1 = ft.Container(
                    content=ft.Text(f"{matched_slot['title']} ({matched_slot['percent']}%)", size=11, weight=ft.FontWeight.BOLD),
                    bgcolor="#1e3a5f", padding=5, border_radius=4
                )
                tasks_text = ", ".join([t["title"] for t in matched_slot["tasks"]])
                col2 = ft.Container(
                    content=ft.Text(tasks_text, size=11),
                    bgcolor="#1b4d3e", padding=5, border_radius=4
                )
                sub_list = []
                for t in matched_slot["tasks"]:
                    sub_list.extend(t["subtasks"])
                col3 = ft.Container(
                    content=ft.Text(", ".join(sub_list) if sub_list else "-", size=10, color="#b0bec5"),
                    bgcolor="#3e2723", padding=5, border_radius=4
                )
            else:
                col1 = ft.Container(content=ft.Text("-", size=10, color="#374151"))
                col2 = ft.Container(content=ft.Text("-", size=10, color="#374151"))
                col3 = ft.Container(content=ft.Text("-", size=10, color="#374151"))

            time_rows.append(
                ft.Container(
                    padding=2,
                    border=ft.Border(bottom=ft.BorderSide(1, "#1f2937")),
                    content=ft.Row([
                        ft.Text(time_str, width=60, size=10, color="#9ca3af"),
                        ft.Container(content=col1, expand=1),
                        ft.Container(content=col2, expand=1),
                        ft.Container(content=col3, expand=1),
                    ])
                )
            )

        return ft.Column([
            ft.Text("📅 Выбор дня:", size=14, weight=ft.FontWeight.BOLD),
            ft.Row(day_buttons, scroll=ft.ScrollMode.AUTO),
            ft.Divider(),
            ft.Text("⚡ Сетка временной ленты (00:00 - 23:00):", size=14, weight=ft.FontWeight.BOLD),
            ft.Column(time_rows, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)

    # -------------------------------------------------------------
    # ВКЛАДКА 2: КОНСТРУКТОР (С КНОПКАМИ РЕДАКТИРОВАНИЯ)
    # -------------------------------------------------------------
    def build_constructor_view():
        slots = data_store[selected_day_idx]["slots"]
        slot_cards = []

        for s in slots:
            def make_edit_cb(slot):
                return lambda e: open_slot_editor(slot)

            def make_del_cb(s_id):
                return lambda e: delete_slot(s_id)

            slot_cards.append(
                ft.Container(
                    padding=10,
                    bgcolor="#1e272c",
                    border=ft.Border(
                        top=ft.BorderSide(1, "#4fc3f7"),
                        bottom=ft.BorderSide(1, "#4fc3f7"),
                        left=ft.BorderSide(1, "#4fc3f7"),
                        right=ft.BorderSide(1, "#4fc3f7")
                    ),
                    border_radius=8,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"📦 {s['title']}", weight=ft.FontWeight.BOLD, size=16),
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.EDIT, icon_color="#4fc3f7", tooltip="Изменить", on_click=make_edit_cb(s)),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_color="#ef5350", tooltip="Удалить", on_click=make_del_cb(s["id"]))
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"⏱ Время: {s['from_h']} - {s['to_h']} | {s['percent']}% дня (= {s['hours']} ч.)", size=12, color="#b0bec5"),
                        ft.Divider(color="#ffffff22"),
                        ft.Text("Задачи отсека:", size=11, color="#81c784"),
                        *[ft.Text(f"  • {t['title']} (Подзадачи: {', '.join(t['subtasks']) if t['subtasks'] else 'нет'})", size=12) for t in s["tasks"]]
                    ])
                )
            )

        return ft.Column([
            ft.Row([
                ft.Text("✍️ Конструктор дня", size=18, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("➕ Добавить слот", icon=ft.Icons.ADD, on_click=lambda e: open_slot_editor(None))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Column(
                slot_cards if slot_cards else [ft.Text("Нет слотов на выбранный день. Нажмите 'Добавить слот'.")], 
                scroll=ft.ScrollMode.AUTO, expand=True
            )
        ], expand=True)

    # -------------------------------------------------------------
    # ВКЛАДКА 3: НАСТРОЙКИ
    # -------------------------------------------------------------
    def build_settings_view():
        return ft.Column([
            ft.Text("⚙️ Настройки и Профиль", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.ListTile(leading=ft.Icon(ft.Icons.PERSON), title=ft.Text("Профиль пользователя")),
            ft.ListTile(leading=ft.Icon(ft.Icons.NOTIFICATIONS), title=ft.Text("Сигналы и звуки")),
        ])

    # -------------------------------------------------------------
    # РЕНДЕР И НАВИГАЦИЯ
    # -------------------------------------------------------------
    body = ft.Container(expand=True)

    def render_current_tab():
        idx = nav.selected_index
        if idx == 0:
            body.content = build_timeline_view()
        elif idx == 1:
            body.content = build_constructor_view()
        elif idx == 2:
            body.content = build_settings_view()
        page.update()

    nav = ft.NavigationBar(
        selected_index=1, # Переключаем по умолчанию на Конструктор
        on_change=lambda e: render_current_tab(),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_VIEW_DAY, label="Лента (3 Столбца)"),
            ft.NavigationBarDestination(icon=ft.Icons.EDIT, label="Конструктор"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Настройки"),
        ]
    )

    page.navigation_bar = nav
    page.add(body)
    render_current_tab()

if __name__ == "__main__":
    ft.app(target=main)
EOF
