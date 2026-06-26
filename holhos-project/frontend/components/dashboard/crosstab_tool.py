import plotly.graph_objects as go
import plotly.colors
from nicegui import ui


class CrosstabTool:
    def __init__(self, variables: list, on_generate=None):
        self.variables = variables
        self.on_generate = on_generate
        self.row_select = None
        self.col_select = None

    def render(self, container=None):
        target = container or ui.card()
        with target:
            with ui.card().style(
                "width: 100%; padding: 1.5rem; border-radius: 8px;"
            ):
                ui.label("Tabulação Cruzada (Crosstabs)").style(
                    "font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 1rem;"
                )

                if not self.variables:
                    ui.label("Nenhuma variável disponível para tabulação cruzada.").style(
                        "color: #9ca3af; font-style: italic;"
                    )
                    return

                captions = [v["caption"] for v in self.variables]
                texts = [f"{v['caption']} — {v['text'][:40]}" for v in self.variables]

                with ui.row().style("gap: 1rem; align-items: flex-end; flex-wrap: wrap;"):
                    with ui.column().style("gap: 0.25rem;"):
                        ui.label("Variável Linha").style("font-size: 0.85rem; color: #6b7280;")
                        self.row_select = ui.select(
                            options=dict(zip(captions, texts)),
                            value=captions[0] if captions else None,
                        ).props("dense outlined").style("min-width: 250px;")

                    with ui.column().style("gap: 0.25rem;"):
                        ui.label("Variável Coluna").style("font-size: 0.85rem; color: #6b7280;")
                        self.col_select = ui.select(
                            options=dict(zip(captions, texts)),
                            value=captions[1] if len(captions) > 1 else (captions[0] if captions else None),
                        ).props("dense outlined").style("min-width: 250px;")

                    ui.button(
                        "Gerar Tabela",
                        on_click=self._generate,
                        icon="table_chart",
                    ).props("color=primary").style("margin-bottom: 0;")

                self.result_container = ui.column().style("width: 100%; margin-top: 1rem;")

    def _generate(self):
        if self.on_generate and self.row_select and self.col_select:
            self.on_generate(self.row_select.value, self.col_select.value)

    def render_result(self, result: dict):
        self.result_container.clear()
        with self.result_container:
            if not result or not result.get("table"):
                ui.label("Dados insuficientes para tabulação cruzada.").style(
                    "color: #9ca3af; font-style: italic;"
                )
                return

            row_labels = result.get("row_labels", [])
            col_labels = result.get("col_labels", [])
            table_data = result.get("table", [])
            row_var = result.get("row_variable", "Linha")
            col_var = result.get("col_variable", "Coluna")

            # Build text matrix with counts and percentages
            text_matrix = []
            for i, rl in enumerate(row_labels):
                row_texts = [f"<b>{rl}</b>"]
                row_total = sum(table_data[i]) if i < len(table_data) else 1
                for j, cl in enumerate(col_labels):
                    count = table_data[i][j] if i < len(table_data) and j < len(table_data[i]) else 0
                    pct = (count / row_total * 100) if row_total else 0
                    row_texts.append(f"{count} ({pct:.0f}%)")
                text_matrix.append(row_texts)

            header_values = [f"<b>{row_var}</b>"] + col_labels

            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=header_values,
                    fill_color="#4b5563",
                    font=dict(color="white", size=12),
                    align="center",
                    height=36,
                ),
                cells=dict(
                    values=[[r[0] for r in text_matrix]] +
                           [[r[j + 1] for r in text_matrix] for j in range(len(col_labels))],
                    fill_color=self._build_cell_colors(table_data),
                    font=dict(size=11),
                    align="center",
                    height=32,
                ),
            )])
            fig.update_layout(
                margin=dict(l=0, r=0, t=40, b=0),
                height=max(200, len(row_labels) * 40 + 80),
                title=dict(
                    text=f"<b>{row_var}</b> × <b>{col_var}</b>",
                    font=dict(size=14),
                ),
            )
            ui.plotly(fig).style("width: 100%;")

            chi2 = result.get("chi_square")
            p_val = result.get("p_value")
            if chi2 is not None:
                with ui.row().style("gap: 1.5rem; margin-top: 0.5rem;"):
                    ui.label(f"Qui-quadrado (χ²): {chi2:.4f}").style(
                        "font-size: 0.9rem; color: #374151; font-weight: 600;"
                    )
                    ui.label(f"Valor-p: {p_val:.4f}").style(
                        f"font-size: 0.9rem; font-weight: 600; "
                        f"color: {'#059669' if p_val < 0.05 else '#6b7280'};"
                    )
                    dof = result.get("degrees_of_freedom")
                    if dof is not None:
                        ui.label(f"gl: {dof}").style("font-size: 0.9rem; color: #6b7280;")

    @staticmethod
    def _build_cell_colors(table_data: list) -> list:
        if not table_data:
            return []

        flat = [v for row in table_data for v in row]
        max_val = max(flat) if flat else 1
        min_val = min(flat) if flat else 0

        if max_val == min_val:
            max_val = min_val + 1

        normalized = [(v - min_val) / (max_val - min_val) for v in flat]
        sampled_colors = plotly.colors.sample_colorscale("Blues", normalized)

        color_idx = 0
        colors = []
        for row in table_data:
            row_colors = ["#f3f4f6"]
            for _ in row:
                row_colors.append(sampled_colors[color_idx])
                color_idx += 1
            colors.append(row_colors)
        return colors
