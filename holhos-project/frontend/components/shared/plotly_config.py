import plotly.graph_objects as go
import plotly.colors

SET1_COLORS = [
    '#e41a1c', '#377eb8', '#4daf4a', '#984ea3',
    '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999',
]

ACADEMIC_FONT = "Inter, system-ui, -apple-system, sans-serif"


def get_plotly_config() -> dict:
    return {
        "displayModeBar": True,
        "responsive": True,
    }


def _base_layout(title: str, height: int = 350) -> dict:
    return {
        "title": {"text": title, "font": {"size": 14, "family": ACADEMIC_FONT}},
        "font": {"family": ACADEMIC_FONT, "size": 12},
        "margin": {"l": 50, "r": 20, "t": 50, "b": 60},
        "height": height,
        "autosize": True,
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
    }


def create_pie_chart(
    labels: list,
    values: list,
    title: str = "",
    height: int = 350,
) -> go.Figure:
    fig = go.Figure(
        data=[go.Pie(
            labels=labels,
            values=values,
            textinfo="percent",
            textfont={"size": 12, "family": ACADEMIC_FONT},
            marker={"colors": SET1_COLORS[:len(labels)]},
            hole=0.35,
            textposition="inside",
        )]
    )
    fig.update_layout(**_base_layout(title, height))
    fig.update_layout(
        showlegend=True,
        legend={
            "font": {"size": 11},
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
            "y": -0.05,
            "yanchor": "top",
        },
    )
    return fig


def create_bar_chart(
    labels: list,
    counts: list,
    percentages: list = None,
    title: str = "",
    height: int = 350,
) -> go.Figure:
    bar_text = [f"{c} ({p}%)" for c, p in zip(counts, percentages or [])] if percentages else None
    fig = go.Figure(
        data=[go.Bar(
            x=labels,
            y=counts,
            text=bar_text,
            textposition="outside",
            marker_color=SET1_COLORS[:len(labels)],
            marker_line_color="#fff",
            marker_line_width=1,
        )]
    )
    layout = _base_layout(title, height)
    layout["xaxis"] = {"tickangle": -30 if any(len(l) > 10 for l in labels) else 0}
    layout["yaxis"] = {"title": "Frequência", "gridcolor": "#f0f0f0"}
    layout["margin"]["t"] = max(layout["margin"].get("t", 50), 40)
    fig.update_layout(**layout)
    max_count = max(counts) if counts else 0
    fig.update_yaxes(range=[0, max_count * 1.2] if max_count > 0 else None)
    return fig


def create_bar_chart_h(
    labels: list,
    counts: list,
    percentages: list = None,
    title: str = "",
    height: int = 350,
) -> go.Figure:
    bar_text = [f"{c} ({p}%)" for c, p in zip(counts, percentages or [])] if percentages else None
    max_count = max(counts) if counts else 0
    fig = go.Figure(
        data=[go.Bar(
            y=labels,
            x=counts,
            orientation='h',
            text=bar_text,
            textposition="outside",
            marker_color=SET1_COLORS[:len(labels)],
            marker_line_color="#fff",
            marker_line_width=1,
        )]
    )
    layout = _base_layout(title, height)
    layout["xaxis"] = {
        "title": "Frequência",
        "gridcolor": "#f0f0f0",
        "range": [0, max_count * 1.3] if max_count > 0 else [0, 1],
    }
    layout["yaxis"] = {"autorange": "reversed", "tickfont": {"size": 10}}
    layout["margin"] = {"l": 10, "r": 80, "t": 10, "b": 40}
    fig.update_layout(**layout)
    return fig


def create_histogram(
    values: list,
    title: str = "",
    x_label: str = "",
    nbins: int = 20,
    height: int = 350,
    use_set1: bool = True,
) -> go.Figure:
    bargap = 0.3 if use_set1 else 0.05

    if use_set1:
        import numpy as np
        counts, bin_edges = np.histogram(values, bins=nbins)
        fig = go.Figure()
        for i in range(len(counts)):
            if counts[i] == 0:
                continue
            fig.add_trace(go.Bar(
                x=[(bin_edges[i] + bin_edges[i + 1]) / 2],
                y=[int(counts[i])],
                width=[bin_edges[i + 1] - bin_edges[i]],
                marker_color=SET1_COLORS[i % len(SET1_COLORS)],
                marker_line_color="white",
                marker_line_width=1,
                text=[str(int(counts[i]))],
                textposition="outside",
                showlegend=False,
            ))
        layout = _base_layout(title, height)
        layout["xaxis"] = {"title": x_label}
        layout["yaxis"] = {"title": "Frequência", "gridcolor": "#f0f0f0"}
        layout["bargap"] = bargap
        fig.update_layout(**layout)
    else:
        fig = go.Figure(
            data=[go.Histogram(
                x=values,
                nbinsx=nbins,
                marker_color=SET1_COLORS[0],
                marker_line_color="white",
                marker_line_width=1,
            )]
        )
        layout = _base_layout(title, height)
        layout["xaxis"] = {"title": x_label}
        layout["yaxis"] = {"title": "Frequência", "gridcolor": "#f0f0f0"}
        layout["bargap"] = bargap
        fig.update_layout(**layout)
    return fig


def create_correlation_heatmap(
    matrix: list,
    labels: list,
    title: str = "",
    height: int = 800,
    width: int = 800,
) -> go.Figure:
    import numpy as np
    z = np.array(matrix)
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=labels,
        y=labels,
        colorscale="PiYG",
        zmin=-1, zmax=1,
        text=np.round(z, 2),
        texttemplate="%{text}",
        textfont={"size": 8, "family": ACADEMIC_FONT},
        hovertemplate="%{y} × %{x}: ρ = %{z:.4f}<extra></extra>",
    ))
    layout = _base_layout(title, height)
    layout["width"] = width
    layout["xaxis"] = {"tickangle": -45, "tickfont": {"size": 9}}
    layout["yaxis"] = {"tickfont": {"size": 9}, "autorange": "reversed"}
    layout["margin"] = {"l": 80, "r": 80, "t": 60, "b": 80}
    fig.update_layout(**layout)
    return fig