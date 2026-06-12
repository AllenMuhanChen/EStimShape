from enum import Enum


class StimType(Enum):
    REGIME_ZERO = "REGIME_ZERO"
    REGIME_ZERO_2D = "REGIME_ZERO_2D"
    REGIME_ONE = "REGIME_ONE"
    REGIME_ONE_2D = "REGIME_ONE_2D"
    REGIME_TWO = "REGIME_TWO"
    REGIME_TWO_2D = "REGIME_TWO_2D"
    REGIME_THREE = "REGIME_THREE"
    REGIME_THREE_2D = "REGIME_THREE_2D"
    REGIME_ESTIM_VARIANTS = "REGIME_ESTIM_VARIANTS"
    REGIME_ESTIM_DELTA = "REGIME_ESTIM_DELTA"
    BASELINE="BASELINE"


# Substrings that mark a stimulus as a terminal test output: it should never be selected as a
# parent for mutation by the general GA machinery (growing/canopy/leafing/zooming/estim phases)
# nor by the top-responder side tests (Dness/zooming/shuffle/...).
#
# These are matched as substrings so suffixed types are covered too (e.g. "SHUFFLE_PIXEL",
# "SHUFFLE_PHASE"). When you add a new side test whose stimuli must not be mutated, register its
# mutation-type token here and every parent selector picks it up automatically.
#
# Note: SIDETEST_2Dvs3D is intentionally NOT excluded - those are valid mutation/zoom targets.
NON_MUTATABLE_MUTATION_TYPE_TOKENS = (
    "BASELINE",
    "CATCH",
    "SHUFFLE",
)


def is_mutatable(stimulus) -> bool:
    """Whether a stimulus may be chosen as a parent / mutated by the general GA.

    Purely type-based (see NON_MUTATABLE_MUTATION_TYPE_TOKENS). Callers that also require a
    response should additionally check ``stimulus.response_rate is not None``.
    """
    mutation_type = stimulus.mutation_type
    if mutation_type is None:
        return False
    return not any(token in mutation_type for token in NON_MUTATABLE_MUTATION_TYPE_TOKENS)


