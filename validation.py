"""Streamlit presentation layer for dataframe validation.

Public API:
    ValidationResult   - re-exported from the domain layer.
    ValidationService  - re-exported from the application layer.
    validate_dataframe - convenience function: DataFrame -> ValidationResult.
    render_validation_report - renders a ValidationResult in the current
        Streamlit app.
    main - Streamlit entry point (file upload + report), run via
        `streamlit run validation.py`.

This module intentionally contains no validation *logic* of its own: it
only converts a `ValidationResult` into Streamlit widgets and wires up
the file-upload workflow. All rules live in `application/validators.py`
and are orchestrated by `application/validation_service.py`.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from application.validation_service import ValidationService
from domain.models import Severity, ValidationResult
from streamlit_widgets import column_select

__all__ = [
    "ValidationResult",
    "ValidationService",
    "validate_dataframe",
    "render_validation_report",
    "main",
]


def validate_dataframe(
    df: pd.DataFrame,
    premium_column: str = "premium",
    exposure_column: str = "exposure",
    max_exposure: float | None = None,
) -> ValidationResult:
    """Validate `df` and return a `ValidationResult`.

    Thin convenience wrapper around `ValidationService`, exposed at
    module level so callers (including this module's own Streamlit UI)
    do not need to know the application layer exists.
    """
    service = ValidationService(
        premium_column=premium_column,
        exposure_column=exposure_column,
        max_exposure=max_exposure,
    )
    return service.validate(df)


def render_validation_report(result: ValidationResult) -> None:
    """Render a `ValidationResult` as Streamlit widgets in the current app."""
    st.subheader("Validation summary")

    cols = st.columns(4)
    cols[0].metric("Rows", result.row_count)
    cols[1].metric("Columns with missing values", len(result.missing_values))
    cols[2].metric("Duplicate rows", len(result.duplicate_rows))
    cols[3].metric(
        "Negative premium / invalid exposure rows",
        len(set(result.negative_premium_rows) | set(result.invalid_exposure_rows)),
    )

    if result.is_valid:
        st.success("No blocking errors found.")
    else:
        st.error(f"{len(result.error_messages)} blocking error(s) found — review before pricing.")

    if result.has_missing_values:
        st.markdown("**Missing values by column**")
        st.dataframe(
            pd.DataFrame(
                {"column": list(result.missing_values.keys()), "missing_count": list(result.missing_values.values())}
            ),
            hide_index=True,
        )

    if result.has_duplicate_rows:
        st.markdown(f"**Duplicate row indices** ({len(result.duplicate_rows)})")
        st.write(list(result.duplicate_rows))

    if result.has_negative_premium:
        st.markdown(f"**Negative premium row indices** ({len(result.negative_premium_rows)})")
        st.write(list(result.negative_premium_rows))

    if result.has_invalid_exposure:
        st.markdown(f"**Invalid exposure row indices** ({len(result.invalid_exposure_rows)})")
        st.write(list(result.invalid_exposure_rows))

    for issue in result.issues:
        if issue.severity is Severity.ERROR:
            st.error(issue.message)
        else:
            st.warning(issue.message)


def main() -> None:
    """Streamlit entry point: upload a CSV, validate it, show the report."""
    st.set_page_config(page_title="Pricing Data Validation", layout="wide")
    st.title("Pricing data validation")
    st.caption("Upload a CSV to check for missing values, duplicate rows, negative premium, and invalid exposure.")

    uploaded_file = st.file_uploader("CSV file", type=["csv"])

    df: pd.DataFrame | None = None
    parse_error: str | None = None
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
            parse_error = f"Could not read the uploaded file as CSV: {exc}"

    columns = list(df.columns) if df is not None else []

    with st.sidebar:
        st.header("Settings")
        premium_column = column_select("Premium column", columns, default="premium")
        exposure_column = column_select("Exposure column", columns, default="exposure")
        use_max_exposure = st.checkbox("Cap maximum valid exposure", value=False)
        max_exposure = st.number_input("Maximum exposure", min_value=0.0, value=365.0) if use_max_exposure else None

    if parse_error is not None:
        st.error(parse_error)
        return

    if df is None:
        st.info("Waiting for a CSV file.")
        return

    if df.empty:
        st.warning("The uploaded file has no rows.")
        return

    st.markdown("**Preview**")
    st.dataframe(df.head(20), hide_index=True)

    result = validate_dataframe(
        df,
        premium_column=premium_column,
        exposure_column=exposure_column,
        max_exposure=max_exposure,
    )
    render_validation_report(result)


if __name__ == "__main__":
    main()
