from dataclasses import dataclass


RETIREMENT_CATEGORY = "retirement"
TRUST_CATEGORY = "trust"


@dataclass(frozen=True)
class AccountValue:
    owner: str
    category: str
    balance: float


@dataclass(frozen=True)
class LiabilityValue:
    balance: float


@dataclass(frozen=True)
class TrustValue:
    value: float


def money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def calculate_sacs(
    monthly_inflow: float,
    monthly_outflow: float,
    deductibles: float,
    private_reserve_balance: float = 0,
) -> dict[str, float]:
    inflow = money(monthly_inflow)
    outflow = money(monthly_outflow)
    reserve_target = money(outflow * 6 + deductibles)
    return {
        "monthly_inflow": inflow,
        "monthly_outflow": outflow,
        "excess_transfer": money(inflow - outflow),
        "deductibles": money(deductibles),
        "private_reserve_balance": money(private_reserve_balance),
        "private_reserve_target": reserve_target,
        "private_reserve_gap": money(reserve_target - private_reserve_balance),
    }


def calculate_household_summary(
    accounts: list[AccountValue],
    liabilities: list[LiabilityValue],
    trust_assets: list[TrustValue],
) -> dict[str, float | dict[str, float]]:
    retirement_by_owner: dict[str, float] = {}
    retirement_total = 0.0
    non_retirement_total = 0.0

    for account in accounts:
        balance = money(account.balance)
        if account.category == RETIREMENT_CATEGORY:
            retirement_by_owner[account.owner] = money(retirement_by_owner.get(account.owner, 0) + balance)
            retirement_total += balance
        else:
            non_retirement_total += balance

    trust_total = sum(money(asset.value) for asset in trust_assets)
    liability_total = sum(money(liability.balance) for liability in liabilities)
    grand_total = retirement_total + non_retirement_total + trust_total

    return {
        "retirement_by_owner": retirement_by_owner,
        "retirement_total": money(retirement_total),
        "non_retirement_total": money(non_retirement_total),
        "trust_total": money(trust_total),
        "grand_total": money(grand_total),
        "liabilities_total": money(liability_total),
        "net_worth_after_liabilities": money(grand_total - liability_total),
    }
