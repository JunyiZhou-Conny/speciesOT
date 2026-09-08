from speciesot.evaluation import HEADLINE, DecodedFrameEvaluation, frac_gap_closed_decoded


def test_headline_key():
    assert HEADLINE == "frac_gap_closed_decoded"
    assert DecodedFrameEvaluation.headline == "frac_gap_closed_decoded"


def test_rank_ignores_raw_frac():
    ev = DecodedFrameEvaluation()
    rows = [
        {"frac_gap_closed_decoded": 0.2, "frac_gap_closed": 0.9},
        {"frac_gap_closed_decoded": 0.8, "frac_gap_closed": 0.1},
    ]
    ranked = ev.rank(rows)
    assert ranked[0]["frac_gap_closed_decoded"] == 0.8
    assert ranked[0]["frac_gap_closed"] == 0.1


def test_formula_matches_script():
    c, m, f = 0.30, 0.10, 0.08
    assert frac_gap_closed_decoded(c, m, f) == (c - m) / (c - f)


if __name__ == "__main__":
    test_headline_key()
    test_rank_ignores_raw_frac()
    test_formula_matches_script()
    print("test_decoded_eval ok")
