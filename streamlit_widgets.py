"""Shared Streamlit widget helpers for the presentation layer.

Used by both `validation.py` and `dashboard.py` so column-name settings are
picked from the uploaded CSV's actual columns instead of free-typed text.
"""

from __future__ import annotations

import streamlit as st

NO_FILE_PLACEHOLDER = "Upload a CSV first"


def column_select(label: str, columns: list[str], default: str) -> str:
    """A dropdown of `columns`, pre-selecting `default` when present.

    Before a file is uploaded (`columns` is empty), renders a disabled
    placeholder dropdown and returns `default` unchanged — callers should
    not act on that value until a file with real columns exists.
    """
    if not columns:
        st.selectbox(label, options=[NO_FILE_PLACEHOLDER], disabled=True)
        return default
    index = columns.index(default) if default in columns else 0
    return st.selectbox(label, options=columns, index=index)
