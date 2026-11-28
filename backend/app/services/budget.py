from app.schemas.trip import BudgetLine, BudgetSummary, ItineraryPlan


def compute_budget(plan: ItineraryPlan, budget: float, travelers: int) -> BudgetSummary:
    """Deterministic budget maths. All figures are whole-group INR estimates.

    Activities ("tickets") are summed from the itinerary items so the breakdown always
    agrees with what the user sees; the other categories come from the model's estimates.
    """
    ce = plan.cost_estimates
    tickets = sum(item.estimated_cost for day in plan.days for item in day.items)
    amounts = {
        "transport": ce.transport,
        "accommodation": ce.accommodation,
        "food": ce.food,
        "tickets": tickets,
        "local_travel": ce.local_travel,
        "misc": ce.misc,
    }
    lines = [BudgetLine(category=k, amount=round(v)) for k, v in amounts.items()]
    total = sum(line.amount for line in lines)  # sum of rounded lines => always consistent
    budget_int = round(budget)
    return BudgetSummary(
        lines=lines,
        total_estimated=total,
        per_traveler=round(total / max(travelers, 1)),
        budget=budget_int,
        remaining=budget_int - total,
        over_budget=total > budget_int,
    )
