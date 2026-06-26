from nicegui import ui


class SummaryCards:
    def __init__(
        self,
        n_responses: int,
        global_stats: dict,
        cronbachs_alpha: float = None,
    ):
        self.n_responses = n_responses
        self.global_stats = global_stats
        self.cronbachs_alpha = cronbachs_alpha

    def render(self, container=None):
        target = container or ui.column()
        with target:
            with ui.row().style(
                "width: 100%; gap: 1rem; flex-wrap: wrap; justify-content: center;"
            ):
                self._stat_card(
                    str(self.n_responses),
                    "Respostas",
                    "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    "people",
                )
                self._stat_card(
                    f"{self.global_stats.get('mean', 0):.1f}",
                    f"Média (DP={self.global_stats.get('sd', 0):.1f})",
                    "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                    "analytics",
                )
                self._stat_card(
                    f"{self.global_stats.get('median', 0):.1f}",
                    f"Mediana (IIQ={self.global_stats.get('iqr', 0):.1f})",
                    "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
                    "trending_up",
                )
                if self.cronbachs_alpha is not None:
                    alpha_label = self._alpha_interpretation(self.cronbachs_alpha)
                    self._stat_card(
                        f"{self.cronbachs_alpha:.3f}",
                        f"Alpha de Cronbach ({alpha_label})",
                        "linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)",
                        "verified",
                    )

    @staticmethod
    def _stat_card(value: str, label: str, gradient: str, icon: str):
        with ui.card().style(
            f"""
            padding: 1rem;
            text-align: center;
            background: {gradient};
            flex: 0 0 auto;
            min-width: 200px;
            max-width: 260px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.4rem;
            """
        ):
            ui.icon(icon, size="1.8rem").style("color: white;")
            ui.label(value).style("font-size: 1.5rem; font-weight: 700; color: white;")
            ui.label(label).style("font-size: 0.8rem; color: white; text-align: center;")

    @staticmethod
    def _alpha_interpretation(alpha: float) -> str:
        if alpha >= 0.9:
            return "Excelente"
        if alpha >= 0.8:
            return "Boa"
        if alpha >= 0.7:
            return "Aceitável"
        if alpha >= 0.6:
            return "Questionável"
        return "Inaceitável"
