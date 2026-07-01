package org.xper.allen.nafc.experiment.bias;

/**
 * One row of the append-only {@code bias_controller_events} log: a per-trial record of what the
 * anti-bias controller saw and did, for offline diagnostics/plotting in Python. Public fields so the
 * controller fills it directly and the DAO writes it directly.
 */
public class BiasEvent {

    /** Choice-event timestamp (microseconds), from the trial. */
    public long tstamp;

    /** Trial's StimSpec id. */
    public long trialStimId;

    /** Variant id of the trial's group. */
    public long variantId;

    /** Correct (sample) lineage id. */
    public long sampleId;

    /** Lineage id the animal picked, or null if it wasn't a plain lineage member (rand/removed/...). */
    public Long chosenId;

    /** Number of choices N shown this trial. */
    public int numChoices;

    /** Whether the animal's choice was correct. */
    public boolean correct;

    /** Whether the chosen stimulus was in the biased state at decision time. */
    public boolean chosenBiased;

    /** Whether the animal correctly avoided a currently-biased stimulus this trial (bias-break). */
    public boolean avoidedBiased;

    /** Bias score of the stimulus that drove the shaping decision, at decision time. */
    public double biasScore;

    /** Reward the trial would have delivered with no shaping (in juice pulses). */
    public double rewardPulsesBase;

    /** Reward actually delivered after shaping (in juice pulses). */
    public double rewardPulsesDelivered;

    /** Extra inter-trial-interval added as bias punishment (ms); 0 if none. */
    public int extraItiMs;

    /** Whether shaping actually altered reward/ITI on this trial (false in shadow mode or when off). */
    public boolean shapingApplied;

    /** Whether the controller was in shadow mode (detect + log only, no reward change) this trial. */
    public boolean shadowMode;
}
