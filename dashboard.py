"""Plotly + Streamlit presentation layer for a KPI dashboard.

Public API:
    build_kpi_dashboard_figure - KPIResult -> plotly.graph_objects.Figure.
    render_kpi_dashboard - renders that figure in the current Streamlit app.
    main - Streamlit entry point (CSV upload + KPI calculation + dashboard),
        run via `streamlit run dashboard.py`.

Every number on the dashboard is read from the `KPIResult` passed in at
call time — nothing here is sample or placeholder data. Styling (colors,
type, spacing) follows a single fixed, professional palette; the only
things a caller can configure are presentation preferences (currency
symbol, columns per row), never the figures themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from domain.kpi_models import KPIResult
from kpis import calculate_kpis

__all__ = ["build_kpi_dashboard_figure", "render_kpi_dashboard", "main"]

# Corporate palette (light-mode chart chrome). Kept as named constants so
# the figure-building code below reads by role, not by raw hex.
_PAGE_PLANE = "#f9f9f7"
_CARD_SURFACE = "#fcfcfb"
_CARD_BORDER = "rgba(11, 11, 11, 0.10)"
_ACCENT = "#2a78d6"
_INK_PRIMARY = "#0b0b0b"
_INK_SECONDARY = "#52514e"
_INK_MUTED = "#898781"
_FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"

_CARD_GAP = 0.02
_ROW_HEIGHT_PX = 168
_HEADER_HEIGHT_PX = 56
_MAX_COLUMNS = 4


@dataclass(frozen=True)
class _KPITile:
    """A single stat-tile's already-formatted display content."""

    label: str
    value_text: str
    caption: str


def _format_compact_number(value: float, prefix: str = "", suffix: str = "") -> str:
    """Auto-compact magnitude formatting: 1,284 / 12.9K / 4.2M / 1.1B."""
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:,.2f}B{suffix}"
    if magnitude >= 1_000_000:
        return f"{prefix}{value / 1_000_000:,.2f}M{suffix}"
    if magnitude >= 1_000:
        return f"{prefix}{value / 1_000:,.1f}K{suffix}"
    return f"{prefix}{value:,.2f}{suffix}"


def _format_currency(value: float | None, currency_symbol: str, *, compact: bool) -> str:
    if value is None:
        return "N/A"
    if compact:
        return _format_compact_number(value, prefix=currency_symbol)
    return f"{currency_symbol}{value:,.2f}"


def _format_number(value: float | None, *, compact: bool) -> str:
    if value is None:
        return "N/A"
    if compact:
        return _format_compact_number(value)
    return f"{value:,.2f}"


def _format_percent(value: float | None, decimals: int) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def _format_count(value: int) -> str:
    return f"{value:,}"


def _build_tiles(result: KPIResult, currency_symbol: str) -> list[_KPITile]:
    """Turn a `KPIResult` into the seven display tiles, values included.

    Every string here is derived from a `result` field or a formatting
    preference (currency symbol) — none of it is sample data.
    """
    return [
        _KPITile(
            label="Premium",
            value_text=_format_currency(result.total_premium, currency_symbol, compact=True),
            caption=f"{_format_count(result.policy_count)} polic{'y' if result.policy_count == 1 else 'ies'}",
        ),
        _KPITile(
            label="Exposure",
            value_text=_format_number(result.total_exposure, compact=True),
            caption="total exposure units",
        ),
        _KPITile(
            label="Loss Ratio",
            value_text=_format_percent(result.loss_ratio, decimals=1),
            caption=f"{_format_currency(result.total_losses, currency_symbol, compact=True)} incurred losses",
        ),
        _KPITile(
            label="Frequency",
            value_text=_format_percent(result.frequency, decimals=2),
            caption=f"{_format_count(result.claim_count)} claims",
        ),
        _KPITile(
            label="Severity",
            value_text=_format_currency(result.severity, currency_symbol, compact=False),
            caption="average cost per claim",
        ),
        _KPITile(
            label="Average Premium",
            value_text=_format_currency(result.average_premium, currency_symbol, compact=False),
            caption="average premium per policy",
        ),
        _KPITile(
            label="Burning Cost",
            value_text=_format_currency(result.burning_cost, currency_symbol, compact=False),
            caption="loss cost per exposure unit",
        ),
    ]


def build_kpi_dashboard_figure(
    result: KPIResult,
    currency_symbol: str = "$",
    columns: int = _MAX_COLUMNS,
) -> go.Figure:
    """Build a responsive Plotly figure of stat tiles for `result`.

    Args:
        result: The KPIs to display. Every value shown comes from this
            object; nothing is hardcoded.
        currency_symbol: Symbol prefixed to currency-formatted tiles.
        columns: Maximum tiles per row before wrapping to a new row.

    Returns:
        A `plotly.graph_objects.Figure` with `autosize=True`, sized to
        the number of rows the tiles need — pass it to
        `st.plotly_chart(fig, use_container_width=True)` (or any
        Plotly renderer) for a layout that adapts to its container.
    """
    if columns < 1:
        raise ValueError(f"columns must be at least 1, got {columns}.")

    tiles = _build_tiles(result, currency_symbol)
    n_columns = min(columns, len(tiles))
    n_rows = ceil(len(tiles) / n_columns)

    cell_width = 1.0 / n_columns
    cell_height = 1.0 / n_rows

    fig = go.Figure()
    for index, tile in enumerate(tiles):
        row, col = divmod(index, n_columns)
        x0 = col * cell_width + _CARD_GAP / 2
        x1 = (col + 1) * cell_width - _CARD_GAP / 2
        # Row 0 is the top row: convert to bottom-up "paper" y-coordinates.
        y1 = 1.0 - row * cell_height - _CARD_GAP / 2
        y0 = 1.0 - (row + 1) * cell_height + _CARD_GAP / 2
        x_mid = (x0 + x1) / 2
        card_height_px = cell_height * (_ROW_HEIGHT_PX * n_rows)

        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            line=dict(color=_CARD_BORDER, width=1),
            fillcolor=_CARD_SURFACE,
            layer="below",
        )
        fig.add_shape(
            type="line",
            xref="paper",
            yref="paper",
            x0=x0,
            x1=x1,
            y0=y1,
            y1=y1,
            line=dict(color=_ACCENT, width=3),
        )
        fig.add_annotation(
            x=x_mid,
            y=y1 - 0.10 * (1 / n_rows),
            xref="paper",
            yref="paper",
            text=tile.label.upper(),
            showarrow=False,
            font=dict(family=_FONT_FAMILY, size=13, color=_INK_SECONDARY),
            yanchor="top",
        )
        fig.add_annotation(
            x=x_mid,
            y=(y0 + y1) / 2 + 0.02 * (1 / n_rows),
            xref="paper",
            yref="paper",
            text=f"<b>{tile.value_text}</b>",
            showarrow=False,
            font=dict(family=_FONT_FAMILY, size=min(30, int(340 / max(len(tile.value_text), 4))), color=_INK_PRIMARY),
        )
        fig.add_annotation(
            x=x_mid,
            y=y0 + 0.12 * (1 / n_rows),
            xref="paper",
            yref="paper",
            text=tile.caption,
            showarrow=False,
            font=dict(family=_FONT_FAMILY, size=11, color=_INK_MUTED),
            yanchor="bottom",
        )

    fig.update_xaxes(visible=False, range=[0, 1], fixedrange=True)
    fig.update_yaxes(visible=False, range=[0, 1], fixedrange=True)
    fig.update_layout(
        autosize=True,
        height=_HEADER_HEIGHT_PX + _ROW_HEIGHT_PX * n_rows,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=_PAGE_PLANE,
        plot_bgcolor=_PAGE_PLANE,
        font=dict(family=_FONT_FAMILY, color=_INK_PRIMARY),
        showlegend=False,
    )
    return fig


def render_kpi_dashboard(
    result: KPIResult,
    currency_symbol: str = "$",
    columns: int = _MAX_COLUMNS,
) -> None:
    """Render `result` as a KPI dashboard in the current Streamlit app."""
    fig = build_kpi_dashboard_figure(result, currency_symbol=currency_symbol, columns=columns)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def main() -> None:
    """Streamlit entry point: upload a CSV, compute KPIs, show the dashboard."""
    st.set_page_config(page_title="Pricing KPI Dashboard", layout="wide")
    st.title("Pricing KPI dashboard")
    st.caption("Upload a CSV to compute premium, exposure, loss ratio, frequency, severity, average premium, and burning cost.")

    with st.sidebar:
        st.header("Settings")
        premium_column = st.text_input("Premium column", value="premium")
        exposure_column = st.text_input("Exposure column", value="exposure")
        loss_column = st.text_input("Loss column", value="loss")
        use_claim_count_column = st.checkbox("Use a claim-count column", value=False)
        claim_count_column = st.text_input("Claim-count column", value="claim_count") if use_claim_count_column else None
        currency_symbol = st.text_input("Currency symbol", value="$")

    uploaded_file = st.file_uploader("CSV file", type=["csv"])
    if uploaded_file is None:
        st.info("Waiting for a CSV file.")
        return

    try:
        df = pd.read_csv(uploaded_file)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        st.error(f"Could not read the uploaded file as CSV: {exc}")
        return

    if df.empty:
        st.warning("The uploaded file has no rows.")
        return

    try:
        result = calculate_kpis(
            df,
            premium_column=premium_column,
            exposure_column=exposure_column,
            loss_column=loss_column,
            claim_count_column=claim_count_column,
        )
    except KeyError as exc:
        st.error(str(exc))
        return

    render_kpi_dashboard(result, currency_symbol=currency_symbol)


if __name__ == "__main__":
    main()
