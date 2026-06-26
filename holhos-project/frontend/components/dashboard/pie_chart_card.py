from nicegui import ui
from components.shared.plotly_config import create_pie_chart


class PieChartCard:
    def __init__(self, question_text: str, labels: list, counts: list, percentages: list):
        self.question_text = question_text
        self.labels = labels
        self.counts = counts
        self.percentages = percentages

    def render(self, container=None):
        target = container or ui.card().style("width: 100%;")
        with target:
            with ui.card().style(
                "width: 100%; padding: 1rem; background: #fafafa; border-radius: 8px;"
            ):
                ui.label(self.question_text).style(
                    "font-weight: 600; color: #111827; font-size: 0.95rem; margin-bottom: 0.5rem;"
                )
                fig = create_pie_chart(
                    labels=self.labels,
                    values=self.counts,
                    title="",
                )
                fig.update_layout(height=300, margin={"l": 20, "r": 20, "t": 20, "b": 20})
                ui.plotly(fig).style("width: 100%;")
