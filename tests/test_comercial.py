from shared.comercial import active_proposal, calculate_price, opportunity_amount_label


def test_calculate_price_uses_gross_margin_formula():
    result = calculate_price(
        monthly_fixed_costs=650_000,
        monthly_variable_costs=250_000,
        implementation_costs=250_000,
        expected_margin_pct=40,
        minimum_margin_pct=30,
        contract_months=5,
        setup_amount=490_000,
        contingency=0,
        discount_pct=0,
        expected_meetings=10,
    )

    assert result["monthly_cost"] == 900_000
    assert result["final_monthly"] == 1_500_000
    assert round(result["real_margin"], 1) == 40.0


def test_active_proposal_prefers_current_version():
    opportunity = {
        "proposals": [
            {"version": "Version 1", "is_current": False, "monthly_amount": 1_000_000, "total_amount": 5_000_000},
            {"version": "Version 2", "is_current": True, "monthly_amount": 1_500_000, "total_amount": 7_500_000},
        ]
    }

    assert active_proposal(opportunity)["version"] == "Version 2"
    assert "$1.500.000" in opportunity_amount_label(opportunity)
