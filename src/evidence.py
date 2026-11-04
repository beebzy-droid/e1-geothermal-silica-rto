"""
Evidence tiering for E1.

The motivating numbers for this thesis are vendor case-study claims (T3). The model
parameters must come from peer-reviewed sources (T1). Conflating the two is the single
most likely reason a JPC reviewer rejects this paper.

Every constant used in the model is declared here with its tier. `validate_target()`
refuses to let a T3 datum be used as a validation target or fitted parameter.
"""
from dataclasses import dataclass
from enum import Enum


class Tier(Enum):
    T1_PEER_REVIEWED = 1   # measurement / primary source -> parameters, validation
    T2_OPERATOR = 2        # operator or agency disclosure -> context, conditions
    T3_VENDOR = 3          # vendor / trade case study    -> motivation ONLY
    T4_ASSUMPTION = 4      # general knowledge            -> must be bounded by sensitivity


@dataclass(frozen=True)
class Datum:
    name: str
    value: float
    unit: str
    tier: Tier
    source: str
    note: str = ""


# --- Motivation only. NOT parameters. NOT validation targets. ---------------
MOTIVATION = [
    Datum("untreated_output_loss", 65.0, "%/yr", Tier.T3_VENDOR,
          "vendor case study (EDC site)", "Justifies the problem. Never fit to this."),
    Datum("inhibitor_output_uplift", 40.0, "%", Tier.T3_VENDOR,
          "vendor case study", "Benchmark to beat, not a validation target."),
    Datum("inhibitor_scaling_reduction", 70.0, "%", Tier.T3_VENDOR,
          "vendor case study", "Benchmark to beat."),
    Datum("manual_descaling_cost", 20_000.0, "USD/event", Tier.T3_VENDOR,
          "vendor case study", "~2 events/yr. Economic motivation."),
]

# --- Context (operator/agency disclosure) ----------------------------------
CONTEXT = [
    Datum("reinjection_flow", 400.0, "kg/s", Tier.T2_OPERATOR,
          "operator disclosure (Bacman)", "Binary-opportunity sizing."),
    Datum("reinjection_temperature", 150.0, "degC", Tier.T2_OPERATOR,
          "operator disclosure (Bacman)", "Binary-opportunity sizing."),
]

# --- Model parameters: fill from T1 sources during P1/P2 -------------------
PARAMETERS: list[Datum] = [
    # e.g. Datum("k_polymerization", ..., "1/s", Tier.T1_PEER_REVIEWED, "Author (Year), doi:...")
]


def validate_target(d: Datum) -> Datum:
    """Guard: a T3/T4 datum may never be a validation target or fitted parameter."""
    if d.tier in (Tier.T3_VENDOR, Tier.T4_ASSUMPTION):
        raise ValueError(
            f"{d.name!r} is {d.tier.name}: usable as motivation/benchmark only. "
            "Fitting kinetics to it, or reporting model agreement against it as "
            "validation, is not defensible. Use a T1 source."
        )
    return d
