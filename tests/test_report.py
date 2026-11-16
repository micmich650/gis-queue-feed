from report import cell


def test_cell_shows_blank_for_none():
    assert cell(None) == ""


def test_cell_turns_number_into_text():
    assert cell(81.57) == "81.57"