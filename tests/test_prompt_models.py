from domain.prompt_models import ExecutiveSummaryPrompt


def test_as_messages_returns_single_user_turn():
    prompt = ExecutiveSummaryPrompt(system_prompt="Be professional.", user_prompt="Summarize these KPIs.")
    messages = prompt.as_messages()
    assert messages == [{"role": "user", "content": "Summarize these KPIs."}]


def test_combined_includes_both_prompts_in_order():
    prompt = ExecutiveSummaryPrompt(system_prompt="SYSTEM_TEXT", user_prompt="USER_TEXT")
    combined = prompt.combined()
    assert combined.index("SYSTEM_TEXT") < combined.index("USER_TEXT")
