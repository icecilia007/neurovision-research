from nicegui import ui


class FilterSidebar:
    def __init__(self, filter_options: dict, on_apply=None, on_clear=None, validity_questions: list = None):
        self.filter_options = filter_options
        self.on_apply = on_apply
        self.on_clear = on_clear
        self.validity_questions = validity_questions or []

        # Demographic filter state
        self.diagnosis_checkboxes = {}
        self.medication_checkboxes = {}
        self.year_range = None
        self.min_year = None
        self.max_year = None

        # Validity filter state
        self.validity_toggle = None
        self.validity_question_select = None
        # caption -> {opt_id: checkbox}
        self._all_options: dict = {}
        # caption -> ui.column container (pre-rendered, toggled visible/hidden)
        self._all_option_containers: dict = {}
        self._validity_questions_by_caption = {q["caption"]: q for q in self.validity_questions}

        # Track initial year range so we only apply filter when user changed it
        self._initial_year_min: int | None = None
        self._initial_year_max: int | None = None

    def render(self, container=None):
        target = container or ui.card().style('width: 100%; max-width: 100%;')
        with target:
            with ui.card().style(
                "padding: 1.25rem; border-radius: 12px; width: 100%; "
                "background: #f8fafc; border: 1px solid #e2e8f0; gap: 0;"
            ):
                # ── Header ──────────────────────────────────────────────
                with ui.row().style("align-items: center; justify-content: space-between; width: 100%;"):
                    with ui.row().style("align-items: center; gap: 0.4rem;"):
                        ui.icon("tune", size="1.1rem", color="primary")
                        ui.label("Filtros").style(
                            "font-weight: 700; font-size: 1rem; color: #111827;"
                        )

                ui.separator().style("margin: 0.75rem 0;")

                # ── Demographic Filters ──────────────────────────────────
                has_demographic = bool(self.filter_options)
                if has_demographic:
                    self._render_demographic_filters()
                    ui.separator().style("margin: 0.75rem 0;")
                else:
                    ui.label("Nenhum filtro demográfico disponível.").style(
                        "color: #9ca3af; font-size: 0.8rem; font-style: italic;"
                    )
                    ui.separator().style("margin: 0.75rem 0;")

                # ── Validity Filter ──────────────────────────────────────
                self._render_validity_filter()

                ui.separator().style("margin: 0.75rem 0;")

                # ── Action Buttons ───────────────────────────────────────
                with ui.row().style("gap: 0.5rem; width: 100%;"):
                    ui.button(
                        "Aplicar filtros",
                        on_click=self._apply,
                        icon="check",
                    ).props("dense color=primary").style("flex: 1; font-size: 0.8rem;")

                    ui.button(
                        "",
                        on_click=self._clear,
                        icon="restart_alt",
                    ).props("dense flat color=grey").style("flex: 0;").tooltip("Limpar filtros")

    # ── Demographic section ────────────────────────────────────────────

    def _render_demographic_filters(self):
        def _section_label(text):
            ui.label(text).style(
                "font-size: 0.68rem; font-weight: 600; color: #9ca3af; "
                "text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.15rem;"
            )

        if "diagnosis" in self.filter_options:
            with ui.column().style("gap: 0.1rem; width: 100%;"):
                _section_label("Diagnóstico prévio")
                with ui.scroll_area().style("max-height: 120px; width: 100%;"):
                    with ui.column().style("gap: 0.05rem;"):
                        for option in self.filter_options["diagnosis"]:
                            cb = ui.checkbox(option).props("dense").style("font-size: 0.82rem;")
                            self.diagnosis_checkboxes[option] = cb

        if "medication" in self.filter_options:
            with ui.column().style("gap: 0.1rem; width: 100%; margin-top: 0.6rem;"):
                _section_label("Medicamento psiquiátrico")
                with ui.column().style("gap: 0.05rem;"):
                    for option in self.filter_options["medication"]:
                        cb = ui.checkbox(option).props("dense").style("font-size: 0.82rem;")
                        self.medication_checkboxes[option] = cb

        if "birth_year" in self.filter_options:
            years = self.filter_options["birth_year"]
            valid_years = [y for y in years if 1900 <= y <= 2015]
            min_year = min(valid_years) if valid_years else 1950
            max_year = max(valid_years) if valid_years else 2010

            self._initial_year_min = min_year
            self._initial_year_max = max_year

            with ui.column().style("gap: 0.1rem; width: 100%; margin-top: 0.6rem;"):
                _section_label("Ano de nascimento")
                self.year_range = ui.range(
                    min=min_year, max=max_year, step=1,
                    value={"min": min_year, "max": max_year},
                ).props("label-always color=primary").style("width: 100%;")
                with ui.row().style("justify-content: space-between; width: 100%;"):
                    self.min_year = ui.label(f"{min_year}").style("font-size: 0.7rem; color: #9ca3af;")
                    self.max_year = ui.label(f"{max_year}").style("font-size: 0.7rem; color: #9ca3af;")

                def update_year_labels(e):
                    self.min_year.set_text(str(e.value["min"]))
                    self.max_year.set_text(str(e.value["max"]))

                self.year_range.on_value_change(update_year_labels)

    # ── Validity filter section ────────────────────────────────────────

    def _render_validity_filter(self):
        with ui.card().style(
            "border: 1.5px solid #86efac; border-radius: 10px; "
            "padding: 0; width: 100%; overflow: hidden; gap: 0; box-shadow: none;"
        ):
            # Header — always visible
            with ui.row().style(
                "align-items: center; gap: 0.5rem; padding: 0.65rem 0.85rem; "
                "background: linear-gradient(135deg, #f0fdf4, #dcfce7); "
                "width: 100%; flex-wrap: nowrap; box-sizing: border-box;"
            ):
                ui.icon("verified_user", size="1.1rem").style("color: #16a34a; flex-shrink: 0;")
                with ui.column().style("gap: 0; flex: 1; min-width: 0;"):
                    ui.label("Controle de Qualidade").style(
                        "font-weight: 700; font-size: 0.85rem; color: #15803d;"
                    )
                    ui.label("Filtra por questão de atenção").style(
                        "font-size: 0.7rem; color: #166534;"
                    )
                self.validity_toggle = ui.switch(value=False).props("color=green dense")

            # Expandable content — visibility bound reactively to the toggle switch
            with ui.column().style(
                "gap: 0.5rem; width: 100%; padding: 0.7rem 0.85rem; "
                "background: white; border-top: 1px solid #bbf7d0; "
                "box-sizing: border-box;"
            ).bind_visibility_from(self.validity_toggle, "value"):

                if not self.validity_questions:
                    ui.label("Nenhuma questão disponível.").style(
                        "color: #9ca3af; font-size: 0.78rem; font-style: italic;"
                    )
                    return

                ui.label("Questão").style(
                    "font-size: 0.68rem; font-weight: 600; color: #9ca3af; "
                    "text-transform: uppercase; letter-spacing: 0.07em;"
                )

                question_options = {
                    q["caption"]: f"{q['caption']} — {q['text'][:40]}{'…' if len(q['text']) > 40 else ''}"
                    for q in self.validity_questions
                }

                self.validity_question_select = ui.select(
                    options=question_options,
                    value=None,
                ).props("dense outlined clearable").style("width: 100%; max-width: 100%; overflow: hidden;")
                self.validity_question_select.on_value_change(self._on_validity_question_change)

                # Pre-render option sets for every question at init time.
                # All start hidden; _on_validity_question_change shows the right one.
                # This avoids dynamic DOM insertion inside an event handler, which
                # can cause NiceGUI to place elements in the wrong slot.
                for q in self.validity_questions:
                    caption = q["caption"]
                    q_container = ui.column().classes("validity-opts").style("gap: 0.25rem; width: 100%;")
                    q_container.set_visibility(False)
                    with q_container:
                        ui.separator().style("margin: 0.15rem 0 0.3rem;")
                        ui.label("Respostas aceitas").style(
                            "font-size: 0.68rem; font-weight: 600; color: #9ca3af; "
                            "text-transform: uppercase; letter-spacing: 0.07em;"
                        )
                        self._all_options[caption] = {}
                        for opt in q.get("options", []):
                            raw = opt["text"].strip()
                            label = raw[:48] + "…" if len(raw) > 48 else raw
                            cb = ui.checkbox(label).props("dense color=green").style(
                                "font-size: 0.8rem; width: 100%; white-space: normal;"
                            )
                            self._all_options[caption][opt["id"]] = cb
                    self._all_option_containers[caption] = q_container

    def _on_validity_question_change(self, e):
        for caption, container in self._all_option_containers.items():
            container.set_visibility(caption == e.value)

    # ── Apply / Clear ──────────────────────────────────────────────────

    def _apply(self):
        if not self.on_apply:
            return
        filters = {}

        selected_diagnoses = [opt for opt, cb in self.diagnosis_checkboxes.items() if cb.value]
        if selected_diagnoses:
            filters["diagnosis"] = selected_diagnoses

        selected_medications = [opt for opt, cb in self.medication_checkboxes.items() if cb.value]
        if selected_medications:
            filters["medication"] = selected_medications

        if self.year_range:
            year_value = self.year_range.value
            user_changed_range = (
                year_value.get("min") != self._initial_year_min
                or year_value.get("max") != self._initial_year_max
            )
            if year_value and user_changed_range:
                filters["birth_year"] = {"min": year_value["min"], "max": year_value["max"]}

        if (
            self.validity_toggle
            and self.validity_toggle.value
            and self.validity_question_select
            and self.validity_question_select.value
        ):
            caption = self.validity_question_select.value
            option_cbs = self._all_options.get(caption, {})
            accepted_ids = [oid for oid, cb in option_cbs.items() if cb.value]
            if accepted_ids:
                filters["validity"] = {
                    "caption": caption,
                    "accepted_option_ids": accepted_ids,
                }

        self.on_apply(filters)

    def _clear(self):
        for cb in self.diagnosis_checkboxes.values():
            cb.set_value(False)
        for cb in self.medication_checkboxes.values():
            cb.set_value(False)

        if self.year_range and self._initial_year_min is not None:
            self.year_range.set_value({
                "min": self._initial_year_min,
                "max": self._initial_year_max,
            })
            if self.min_year:
                self.min_year.set_text(str(self._initial_year_min))
            if self.max_year:
                self.max_year.set_text(str(self._initial_year_max))

        if self.validity_toggle:
            self.validity_toggle.set_value(False)
        if self.validity_question_select:
            self.validity_question_select.set_value(None)
        for caption_opts in self._all_options.values():
            for cb in caption_opts.values():
                cb.set_value(False)
        for container in self._all_option_containers.values():
            container.set_visibility(False)

        if self.on_clear:
            self.on_clear()
