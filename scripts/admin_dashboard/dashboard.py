"""LeagueQL admin dashboard (Streamlit).

A simple, read-only onboarding-health dashboard driven entirely by the ``METADATA``
items in DynamoDB. It queries **GSI3** ("All-leagues index") once — a single
``SK = "METADATA"`` query returns every onboarded league ordered by ``onboarded_at``,
with ``platform``, ``active_platform`` and ``last_accessed_at`` already projected — so
there is no full-table scan and no per-league ``GetItem``.

It renders:

  * top row  — total leagues onboarded, active leagues (accessed in the last 14 days),
               and an ESPN-vs-SLEEPER horizontal bar chart
  * next row — cumulative leagues-onboarded over time, with 1M / 3M / 6M / YTD / 1Y / All
               range buttons embedded in the chart

Data source is **prod only** (``leagueql-table-prod``). It uses your terminal's AWS
credentials via ``boto3.Session()`` — point them at the prod account first.

Usage
-----
    pipenv run streamlit run scripts/admin_dashboard/dashboard.py
"""

import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from aggregations import (
    build_dataframe,
    count_active,
    cumulative_series,
    platform_counts,
)
from boto3.dynamodb.conditions import Key

TABLE_NAME = "leagueql-table-prod"
GSI3_INDEX_NAME = "GSI3"
ACTIVE_DAYS = 14

# Brand-ish colors so ESPN / SLEEPER read consistently across the page.
PLATFORM_COLORS = {"ESPN": "#D50A0A", "SLEEPER": "#F5A623"}


def fetch_metadata_items(table) -> list[dict]:
    """Query GSI3 for every METADATA item, paginating on LastEvaluatedKey."""
    items: list[dict] = []
    kwargs = {
        "IndexName": GSI3_INDEX_NAME,
        "KeyConditionExpression": Key("SK").eq("METADATA"),
    }
    while True:
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


@st.cache_data(ttl=300, show_spinner="Querying DynamoDB (GSI3)…")
def load_items() -> list[dict]:
    """Load METADATA items from prod, cached for 5 minutes (see Refresh button)."""
    session = boto3.Session()  # terminal AWS creds + default region
    table = session.resource("dynamodb").Table(TABLE_NAME)
    return fetch_metadata_items(table)


def _platform_bar(counts: dict[str, int]) -> go.Figure:
    bar_df = pd.DataFrame(
        {"platform": list(counts.keys()), "count": list(counts.values())}
    )
    fig = px.bar(
        bar_df,
        x="count",
        y="platform",
        orientation="h",
        color="platform",
        color_discrete_map=PLATFORM_COLORS,
        text="count",
    )
    fig.update_layout(
        title="Leagues by platform",
        showlegend=False,
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        height=200,
        xaxis_title=None,
        yaxis_title=None,
    )
    return fig


def _cumulative_line(series: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=series["onboarded_at"],
            y=series["cumulative_count"],
            mode="lines",
            fill="tozeroy",
            line={"color": "#4C78A8", "width": 2},
            hovertemplate="%{x|%Y-%m-%d}<br>%{y} leagues<extra></extra>",
        )
    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=420,
        yaxis_title="Cumulative leagues onboarded",
        xaxis={
            "type": "date",
            "rangeselector": {
                "buttons": [
                    {
                        "count": 1,
                        "label": "1M",
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {
                        "count": 3,
                        "label": "3M",
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {
                        "count": 6,
                        "label": "6M",
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {"count": 1, "label": "YTD", "step": "year", "stepmode": "todate"},
                    {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "All"},
                ]
            },
            "rangeslider": {"visible": True},
        },
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="LeagueQL Admin", page_icon="🏈", layout="wide")
    st.title("LeagueQL Admin Dashboard")

    with st.sidebar:
        st.caption(f"Source: `{TABLE_NAME}` · {GSI3_INDEX_NAME}")
        if st.button("Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    items = load_items()
    df = build_dataframe(items)
    now = pd.Timestamp.now(tz="UTC")

    # --- Top row: two metric cards + platform split ---
    col_total, col_active, col_bar = st.columns([1, 1, 2])
    col_total.metric("Total leagues onboarded", len(df))
    col_active.metric(
        f"Active leagues ({ACTIVE_DAYS}d)", count_active(df, now, days=ACTIVE_DAYS)
    )
    with col_bar:
        st.plotly_chart(_platform_bar(platform_counts(df)), use_container_width=True)

    # --- Second row: cumulative onboarding over time ---
    st.subheader("Cumulative leagues onboarded")
    series = cumulative_series(df)
    if series.empty:
        st.info("No onboarded leagues to plot yet.")
    else:
        st.plotly_chart(_cumulative_line(series), use_container_width=True)


if __name__ == "__main__":
    main()
