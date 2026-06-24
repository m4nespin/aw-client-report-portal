from backend.calculations import AccountValue, LiabilityValue, TrustValue, calculate_household_summary, calculate_sacs


def test_sacs_calculates_excess_and_reserve_target() -> None:
    result = calculate_sacs(
        monthly_inflow=25_000,
        monthly_outflow=16_500,
        deductibles=4_000,
        private_reserve_balance=80_000,
    )

    assert result["excess_transfer"] == 8_500
    assert result["private_reserve_target"] == 103_000
    assert result["private_reserve_gap"] == 23_000


def test_household_summary_keeps_liabilities_separate_from_tcc_total() -> None:
    result = calculate_household_summary(
        accounts=[
            AccountValue(owner="Primary", category="retirement", balance=400_000),
            AccountValue(owner="Spouse", category="retirement", balance=300_000),
            AccountValue(owner="Joint", category="non_retirement", balance=250_000),
        ],
        liabilities=[LiabilityValue(balance=125_000)],
        trust_assets=[TrustValue(value=500_000)],
    )

    assert result["retirement_by_owner"] == {"Primary": 400_000, "Spouse": 300_000}
    assert result["non_retirement_total"] == 250_000
    assert result["trust_total"] == 500_000
    assert result["grand_total"] == 1_450_000
    assert result["liabilities_total"] == 125_000
    assert result["net_worth_after_liabilities"] == 1_325_000
