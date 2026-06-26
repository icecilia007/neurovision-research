from nicegui import ui
from components.shared.plotly_config import create_bar_chart


class BarChartCard:
    def __init__(self, question_text: str, labels: list, counts: list, percentages: list, stats: dict = None):
        self.question_text = question_text
        self.labels = labels
        self.counts = counts
        self.percentages = percentages
        self.stats = stats

    def render(self, container=None):
        target = container or ui.card().style("width: 100%;")
        with target:
            with ui.card().style(
                "width: 100%; padding: 1rem; background: #fafafa; border-radius: 8px;"
            ):
                ui.label(self.question_text).style(
                    "font-weight: 600; color: #111827; font-size: 0.95rem; margin-bottom: 0.5rem;"
                )
                fig = create_bar_chart(
                    labels=self.labels,
                    counts=self.counts,
                    percentages=self.percentages,
                    title="",
                )
                fig.update_layout(height=320, margin={"l": 40, "r": 20, "t": 20, "b": 80})
                ui.plotly(fig).style("width: 100%;")

                if self.stats:
                    with ui.row().style("gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem; justify-content: center;"):
                        for label, key in [
                            ("Média", "mean"), ("DP", "sd"), ("Mediana", "median"),
                            ("Moda", "mode"), ("IIQ", "iqr"),
                        ]:
                            val = self.stats.get(key, 0)
                            with ui.badge(f"{label}: {val:.2f}").style(
                                "background-color: #40479f; color: #f7f0f7; "
                                "padding: 0.25rem 0.6rem; font-size: 0.75rem; font-weight: 500;"
                            ):
                                pass
