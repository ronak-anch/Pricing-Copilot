from streamlit.testing.v1 import AppTest


def _render_with_columns() -> None:
    from streamlit_widgets import column_select

    column_select("Premium column", ["gross_premium", "exposure", "loss"], default="premium")
    column_select("Exposure column", ["gross_premium", "exposure", "loss"], default="exposure")


def _render_without_columns() -> None:
    from streamlit_widgets import column_select

    column_select("Premium column", [], default="premium")


def test_column_select_lists_the_dataframes_actual_columns():
    at = AppTest.from_function(_render_with_columns)
    at.run()

    assert not at.exception
    assert at.selectbox[0].options == ["gross_premium", "exposure", "loss"]
    assert at.selectbox[1].options == ["gross_premium", "exposure", "loss"]


def test_column_select_falls_back_to_first_column_when_default_absent():
    at = AppTest.from_function(_render_with_columns)
    at.run()

    # "premium" isn't among the columns, so the first column is preselected.
    assert at.selectbox[0].value == "gross_premium"
    # "exposure" is among the columns, so it's preselected directly.
    assert at.selectbox[1].value == "exposure"


def test_column_select_shows_disabled_placeholder_before_a_file_is_uploaded():
    at = AppTest.from_function(_render_without_columns)
    at.run()

    assert not at.exception
    assert at.selectbox[0].disabled is True
    assert at.selectbox[0].options == ["Upload a CSV first"]
