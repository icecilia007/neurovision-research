from nicegui import ui
from components.shared.plotly_config import create_histogram


class SubscaleSection:
    def __init__(self, subscale_stats: dict, respondent_scores: list = None):
        self.subscale_stats = subscale_stats
        self.respondent_scores = respondent_scores

    def render(self, container=None):
        target = container or ui.column()
        with target:
            ui.label("Escores por subescala CHYPS-V").style(
                "font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;"
            )

            with ui.row().style("width: 100%; gap: 1rem; flex-wrap: wrap;"):
                for name, stats in self.subscale_stats.items():
                    label_en = stats.get("label_en", "")
                    items = stats.get("items", [])
                    with ui.card().style(
                        "flex: 1; min-width: 280px; max-width: 450px; padding: 1rem; "
                        "background: #f9fafb; border-radius: 8px;"
                    ):
                        with ui.row().style("align-items: baseline; gap: 0.5rem;"):
                            ui.label(name).style("font-weight: 700; color: #111827; font-size: 1rem;")
                            if label_en:
                                ui.label(f"({label_en})").style("color: #9ca3af; font-size: 0.8rem;")

                        ui.label(f"Itens: {', '.join(items)}").style(
                            "color: #6b7280; font-size: 0.8rem; margin: 0.25rem 0;"
                        )

                        with ui.row().style("gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem;"):
                            for label, key in [
                                ("Média", "mean"), ("DP", "sd"), ("Mediana", "median"),
                                ("Moda", "mode"), ("IIQ", "iqr"),
                            ]:
                                val = stats.get(key, 0)
                                with ui.badge(f"{label}: {val:.1f}").style(
                                    "background-color: #e0e7ff; color: #3730a3; "
                                    "padding: 0.2rem 0.5rem; font-size: 0.75rem;"
                                ):
                                    pass

            if self.respondent_scores and len(self.respondent_scores) > 1:
                self._render_subscale_histograms()

    def _render_subscale_histograms(self):
        with ui.row().style("width: 100%; gap: 1rem; flex-wrap: wrap; margin-top: 1rem;"):
            for name in self.subscale_stats:
                values = [
                    r["subscale_scores"].get(name, 0)
                    for r in self.respondent_scores
                ]
                if not values:
                    continue
                fig = create_histogram(
                    values=values,
                    title=f"{name}",
                    x_label="Escore",
                    nbins=max(5, len(set(values))),
                    height=280,
                )
                with ui.card().style(
                    "flex: 1; min-width: 280px; max-width: 400px; padding: 0.5rem;"
                ):
                    ui.plotly(fig).style("width: 100%;")
