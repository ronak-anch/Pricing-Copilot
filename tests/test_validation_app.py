"""Tests for the Streamlit presentation layer in validation.py.

Uses streamlit.testing.v1.AppTest to run real Streamlit scripts headlessly
and inspect the rendered element tree, rather than mocking `st.*` calls.
"""

from streamlit.testing.v1 import AppTest


def _render_clean_report() -> None:
    import pandas as pd

    from validation import render_validation_report, validate_dataframe

    df = pd.DataFrame({"premium": [100, 200], "exposure": [1, 0.5]})
    result = validate_dataframe(df)
    render_validation_report(result)


def _render_report_with_issues() -> None:
    import pandas as pd

    from validation import render_validation_report, validate_dataframe

    df = pd.DataFrame(
        {
            "premium": [100, 100, -50, None],
            "exposure": [1, 1, 1, 0],
        }
    )
    result = validate_dataframe(df)
    render_validation_report(result)


def test_render_validation_report_shows_success_for_clean_data():
    at = AppTest.from_function(_render_clean_report)
    at.run()

    assert not at.exception
    assert any("No blocking errors" in success.value for success in at.success)


def test_render_validation_report_shows_errors_and_warnings_for_dirty_data():
    at = AppTest.from_function(_render_report_with_issues)
    at.run()

    assert not at.exception
    assert len(at.error) >= 1
    assert len(at.warning) >= 1
    assert any("blocking error" in error.value for error in at.error)


def test_main_app_renders_upload_prompt_before_any_file_is_provided():
    at = AppTest.from_file("../validation.py")
    at.run()

    assert not at.exception
    assert at.title[0].value == "Pricing data validation"
    assert any("Waiting for a CSV file" in info.value for info in at.info)
