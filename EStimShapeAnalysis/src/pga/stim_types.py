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
    "LIGHTING",
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


# Texture types (StimTexture.texture_type) that count as 3D. "2D" is the only 2D value.
THREE_D_TEXTURES = ("SHADE", "SPECULAR")


def get_texture_type(conn, stim_id):
    """Read a stimulus's texture_type from the StimTexture table, or None if absent."""
    conn.execute("SELECT texture_type FROM StimTexture WHERE stim_id = %s", (stim_id,))
    return conn.fetch_one()


def is_3d(conn, stim_id) -> bool:
    """Whether a stimulus is 3D (SHADE/SPECULAR texture). 2D and missing rows are not 3D."""
    return get_texture_type(conn, stim_id) in THREE_D_TEXTURES


