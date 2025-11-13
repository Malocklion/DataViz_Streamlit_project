# utils/viz.py
from plotly.graph_objs import Figure

def configure_fig(fig: Figure, height: int | None = None) -> Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, Roboto", size=12),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig
