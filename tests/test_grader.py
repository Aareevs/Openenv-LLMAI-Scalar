from grader.grader import VaultGrader


def _sample_text(gold_entry):
    return (
        f"Employee note for {gold_entry['name']} ({gold_entry['role']}). "
        f"Reach at {gold_entry['email']} and {gold_entry['phone']}. "
        f"Key: {gold_entry['api_key']}. "
        "Project details and non-sensitive operational context must be preserved."
    )


def test_over_deletion_returns_zero_score():
    grader = VaultGrader()
    gold = grader.get_gold(0)
    original_text = _sample_text(gold)

    # Very short output triggers over-deletion guard (<30% of original length).
    agent_output = "[REDACTED]"

    score = grader.grade(original_text, agent_output, gold)
    assert score == 0.0


def test_partial_redaction_above_threshold_is_allowed():
    grader = VaultGrader()
    gold = grader.get_gold(0)
    original_text = _sample_text(gold)

    agent_output = (
        original_text
        .replace(gold["email"], "[REDACTED]")
        .replace(gold["phone"], "[REDACTED]")
        .replace(gold["api_key"], "[REDACTED]")
    )

    # Keep most utility; should not be auto-zeroed by length guard.
    assert len(agent_output) >= 0.3 * len(original_text)
    score = grader.grade(original_text, agent_output, gold)
    assert score > 0.0
