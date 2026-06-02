package org.xper.allen.intan.stimulation;

/**
 * How non-stim "ground only" channels are configured when decorating an EStim spec.
 *
 * PostTrain:
 *   Ground channels mirror the stim train exactly (same trigger type, num pulses,
 *   period) but with zero amplitude. Charge recovery still happens AFTER the train
 *   completes (this is an Intan RHS hardware limitation — there is no per-pulse
 *   charge recovery within a train). Use this when you want grounding behavior
 *   that lines up cycle-for-cycle with the stim train and you don't need
 *   between-pulse grounding.
 *
 * BetweenPulse:
 *   Ground channels use Level + SinglePulse trigger with a refractory period
 *   sized so each ground pulse fires between successive stim pulses. This
 *   reproduces the original "edge hold to ground" paradigm and is intended
 *   for use with a sustained (held-high) digital trigger that lasts the full
 *   stim train duration. Caveat: the stim channels run on Edge + PulseTrain
 *   (which fires once per rising edge and ignores the held level), so the
 *   user must construct the trigger signal carefully so the held duration
 *   matches the stim train duration.
 */
public enum GroundMode {
    PostTrain,
    BetweenPulse
}
