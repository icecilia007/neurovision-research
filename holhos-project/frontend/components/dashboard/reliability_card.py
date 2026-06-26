from nicegui import ui


class ReliabilityCard:
    def __init__(self, alpha: float = None, n_items: int = 20):
        self.alpha = alpha
        self.n_items = n_items

    def render(self, container=None):
        target = container or ui.card()
        with target:
            with ui.card().style(
                "width: 100%; padding: 1.5rem; border-radius: 8px; "
                "background: linear-gradient(135deg, #f8fafc, #eef2ff);"
            ):
                ui.label("Análise de Confiabilidade").style(
                    "font-size: 1.1rem; font-weight: 700; color: #111827; margin-bottom: 0.75rem;"
                )

                if self.alpha is None:
                    ui.label("Dados insuficientes para calcular o Alpha de Cronbach.").style(
                        "color: #9ca3af; font-style: italic;"
                    )
                    return

                color, label = self._interpret(self.alpha)

                with ui.row().style("align-items: center; gap: 1rem;"):
                    ui.label(f"α = {self.alpha:.4f}").style(
                        "font-size: 2rem; font-weight: 800; color: #111827;"
                    )
                    with ui.badge(label).style(
                        f"background-color: {color}; color: white; "
                        "padding: 0.35rem 0.75rem; font-size: 0.85rem; font-weight: 600;"
                    ):
                        pass

                ui.label(
                    f"Alpha de Cronbach para {self.n_items} itens da escala. "
                    "Mede a consistência interna dos itens."
                ).style("color: #6b7280; font-size: 0.85rem; margin-top: 0.5rem;")

                with ui.row().style("gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap;"):
                    for val, desc, clr in [
                        (0.9, "Excelente", "#059669"),
                        (0.8, "Boa", "#10b981"),
                        (0.7, "Aceitável", "#f59e0b"),
                        (0.6, "Questionável", "#f97316"),
                        (0.0, "Inaceitável", "#ef4444"),
                    ]:
                        alpha_color = clr if self.alpha >= val else "#d1d5db"
                        with ui.badge(f"≥{val}: {desc}").style(
                            f"background-color: {alpha_color}; color: white; "
                            "padding: 0.2rem 0.5rem; font-size: 0.7rem;"
                        ):
                            pass

    @staticmethod
    def _interpret(alpha: float):
        if alpha >= 0.9:
            return "#059669", "Excelente"
        if alpha >= 0.8:
            return "#10b981", "Boa"
        if alpha >= 0.7:
            return "#f59e0b", "Aceitável"
        if alpha >= 0.6:
            return "#f97316", "Questionável"
        return "#ef4444", "Inaceitável"
