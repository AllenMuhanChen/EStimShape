"""
Derived EStim "hyperparameters": composite quantities built from the base
EStimParameters (a1, num_channels, pulse count, pulse timing). These combine the
raw stimulation parameters into physically meaningful aggregates that several
analyses want to relate behaviour to, so they live here behind a small reusable
API rather than being recomputed ad hoc.

All quantities are per estim spec, read from the first active (a1 > 0) channel,
and num_channels counts only active channels — the same convention as
EStimParameterClassifier.active_channel_sql_subquery().

Provided hyperparameters:

  total_current_per_pulse = a1 * num_channels                  (µA delivered per pulse)
  total_current           = a1 * num_channels * num_pulses     (µA summed over the train)
  current_per_second      = a1 * num_channels * pulse_rate_hz  (µA·Hz, current delivery rate)

Public API
----------
  compute_estim_hyperparameters(a1, num_channels, n_pulses, rate_hz) -> dict
      Pure math, no DB. Returns {name: value-or-None}.
  get_estim_hyperparameters(session_id, estim_spec_id) -> dict
      DB-backed: reads the base params for a spec, derives the pulse count and
      pulse rate, and computes the hyperparameters.
  get_base_params(session_id, estim_spec_id) -> dict | None
      The raw base parameters used as inputs.
  num_pulses(pulse_repetition, num_repetitions) -> int
  pulse_rate_hz(trigger_edge_or_level, pulse_train_period,
                post_stim_refractory_period, post_trigger_delay) -> float | None
      The two derivations, exposed for reuse.
"""

from clat.util.connection import Connection
from src.analysis.nafc.estim_parameter_classifier import EStimParameterClassifier

# Hyperparameter identifiers (use these as dict keys / column names downstream).
TOTAL_CURRENT_PER_PULSE = 'total_current_per_pulse'
TOTAL_CURRENT = 'total_current'
CURRENT_PER_SECOND = 'current_per_second'
HYPERPARAMETER_NAMES = (TOTAL_CURRENT_PER_PULSE, TOTAL_CURRENT, CURRENT_PER_SECOND)

# Base EStimParameters columns read to compute the hyperparameters (from the
# first active channel). num_channels is the active-channel count from the subquery.
_BASE_PARAM_COLUMNS = [
    'a1', 'num_channels', 'pulse_repetition', 'num_repetitions',
    'trigger_edge_or_level', 'pulse_train_period',
    'post_stim_refractory_period', 'post_trigger_delay',
]


def _to_float(x):
    """Coerce a DB value (Decimal/str/None) to float, or None if not numeric."""
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def num_pulses(pulse_repetition, num_repetitions):
    """Number of pulses delivered per trigger.

    SinglePulse → 1. PulseTrain → num_repetitions (the pulse count per trigger,
    per EStimNumPulsesField). A missing or non-positive count falls back to 1.
    """
    if pulse_repetition is not None and str(pulse_repetition).strip().lower() == 'singlepulse':
        return 1
    n = _to_float(num_repetitions)
    if n is None or n < 1:
        return 1
    return int(round(n))


def pulse_rate_hz(trigger_edge_or_level, pulse_train_period,
                  post_stim_refractory_period, post_trigger_delay):
    """Pulse repetition rate (Hz) derived from Intan timing parameters.

    Edge-triggered: one pulse train per trigger edge with pulses spaced by
    pulse_train_period, so the period is just pulse_train_period.
    Level-triggered: pulses repeat while the trigger is held high; the period is
    post_stim_refractory_period + post_trigger_delay.

    All timing columns are stored in microseconds, so rate_hz = 1e6 / period_us.
    Returns None if the relevant period is missing or non-positive.
    """
    if str(trigger_edge_or_level).strip().lower() == 'level':
        period_us = (_to_float(post_stim_refractory_period) or 0.0) + \
                    (_to_float(post_trigger_delay) or 0.0)
    else:  # Edge (or unspecified): trust the pulse train period
        period_us = _to_float(pulse_train_period)
    if not period_us or period_us <= 0:
        return None
    return 1e6 / period_us


def compute_estim_hyperparameters(a1=None, num_channels=None, n_pulses=None, rate_hz=None):
    """Compute the derived hyperparameters from base quantities (pure, no DB).

    Any hyperparameter whose inputs are missing is returned as None.
    """
    a1 = _to_float(a1)
    nch = _to_float(num_channels)
    npul = _to_float(n_pulses)
    rate = _to_float(rate_hz)

    per_pulse = a1 * nch if a1 is not None and nch is not None else None
    total = per_pulse * npul if per_pulse is not None and npul is not None else None
    per_second = per_pulse * rate if per_pulse is not None and rate is not None else None

    return {
        TOTAL_CURRENT_PER_PULSE: per_pulse,
        TOTAL_CURRENT: total,
        CURRENT_PER_SECOND: per_second,
    }


def get_base_params(session_id, estim_spec_id):
    """Return {column: value} of the base EStimParameters for (session, spec) from
    the first active channel, or None if the spec has no active channel."""
    conn = Connection("allen_data_repository")
    cols = ", ".join(f"ep.{c}" for c in _BASE_PARAM_COLUMNS)
    conn.execute(f"""
        SELECT {cols}
        FROM ({EStimParameterClassifier.active_channel_sql_subquery()}) ep
        WHERE ep.session_id = %s AND ep.estim_spec_id = %s
    """, (session_id, int(estim_spec_id)))
    rows = conn.fetch_all()
    if not rows:
        return None
    return dict(zip(_BASE_PARAM_COLUMNS, rows[0]))


def get_estim_hyperparameters(session_id, estim_spec_id):
    """Read the base params for a spec and compute its derived hyperparameters.

    Returns {name: value-or-None}; all None if the spec isn't found.
    """
    raw = get_base_params(session_id, estim_spec_id)
    if raw is None:
        return {name: None for name in HYPERPARAMETER_NAMES}
    n_pulses = num_pulses(raw.get('pulse_repetition'), raw.get('num_repetitions'))
    rate = pulse_rate_hz(raw.get('trigger_edge_or_level'),
                         raw.get('pulse_train_period'),
                         raw.get('post_stim_refractory_period'),
                         raw.get('post_trigger_delay'))
    return compute_estim_hyperparameters(
        a1=raw.get('a1'), num_channels=raw.get('num_channels'),
        n_pulses=n_pulses, rate_hz=rate)
