from nicegui import ui


class TextResponsesTable:
    def __init__(
        self,
        question_text: str,
        responses: list,
        total: int,
        page: int,
        total_pages: int,
        on_search=None,
        on_page_change=None,
    ):
        self.question_text = question_text
        self.responses = responses
        self.total = total
        self.page = page
        self.total_pages = total_pages
        self.on_search = on_search
        self.on_page_change = on_page_change

    def render(self, container=None):
        target = container or ui.card()
        with target:
            with ui.card().style(
                "width: 100%; padding: 1rem; background: #fafafa; border-radius: 8px;"
            ):
                ui.label(self.question_text).style(
                    "font-weight: 600; color: #111827; font-size: 0.95rem; margin-bottom: 0.5rem;"
                )
                ui.label(f"{self.total} resposta(s)").style(
                    "color: #6b7280; font-size: 0.85rem; margin-bottom: 0.75rem;"
                )

                if self.total == 0:
                    ui.label("Nenhuma resposta encontrada.").style(
                        "color: #9ca3af; font-style: italic; padding: 1rem; text-align: center;"
                    )
                    return

                with ui.row().style("gap: 0.5rem; width: 100%; margin-bottom: 0.75rem; align-items: center;"):
                    search_input = ui.input(
                        placeholder="Buscar nas respostas...",
                    ).style("flex: 1;").props('dense outlined')
                    if self.on_search:
                        search_input.on("keydown.enter", lambda e: self.on_search(search_input.value))

                columns = [
                    {"name": "idx", "label": "#", "field": "idx", "align": "left", "sortable": False},
                    {"name": "text", "label": "Resposta", "field": "text", "align": "left", "sortable": False},
                    {"name": "date", "label": "Data", "field": "date", "align": "left", "sortable": False},
                ]
                rows = [
                    {
                        "idx": i + 1 + (self.page - 1) * 10,
                        "text": r["text"][:200] + ("..." if len(r["text"]) > 200 else ""),
                        "date": r.get("submitted_at", "")[:10],
                    }
                    for i, r in enumerate(self.responses)
                ]
                ui.table(
                    columns=columns,
                    rows=rows,
                    row_key="idx",
                ).style("width: 100%;").props('flat bordered dense')

                if self.total_pages > 1:
                    with ui.row().style(
                        "gap: 0.5rem; margin-top: 0.5rem; align-items: center; justify-content: center;"
                    ):
                        ui.button(
                            "Anterior",
                            on_click=lambda: self.on_page_change(self.page - 1) if self.on_page_change else None,
                        ).props("dense flat").style(
                            "font-size: 0.8rem;"
                        ).bind_enabled_from(self, '_has_prev')

                        ui.label(f"Página {self.page} de {self.total_pages}").style(
                            "font-size: 0.85rem; color: #6b7280;"
                        )

                        ui.button(
                            "Próxima",
                            on_click=lambda: self.on_page_change(self.page + 1) if self.on_page_change else None,
                        ).props("dense flat").style(
                            "font-size: 0.8rem;"
                        ).bind_enabled_from(self, '_has_next')

    @property
    def _has_prev(self):
        return self.page > 1

    @property
    def _has_next(self):
        return self.page < self.total_pages
