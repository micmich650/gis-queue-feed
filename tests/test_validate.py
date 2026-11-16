import pandas as pd

from parse import validate


def make_projects(count):
    return pd.DataFrame(
        {
            "project_id": [f"26INR{i:04d}" for i in range(count)],
            "capacity_mw": [100.0] * count,
            "projected_cod": pd.to_datetime(["2027-01-01"] * count),
            "ia_signed": pd.to_datetime(["2026-01-01"] * count),
            "approved_energization": pd.to_datetime(["2026-06-01"] * count),
            "approved_synchronization": pd.to_datetime(["2026-07-01"] * count),
        }
    )


def test_good_file_has_no_problems():
    assert validate(make_projects(150)) == []


def test_too_few_projects():
    assert validate(make_projects(5)) == ["only 5 projects (expected at least 100)"]


def test_duplicate_ids():
    df = make_projects(150)
    df.loc[1, "project_id"] = df.loc[0, "project_id"]

    assert validate(df) == ["1 duplicate project IDs"]


def test_text_in_capacity_column():
    df = make_projects(150)
    df["capacity_mw"] = ["TBD"] + [100.0] * 149

    assert validate(df) == ["capacity_mw is not numeric"]