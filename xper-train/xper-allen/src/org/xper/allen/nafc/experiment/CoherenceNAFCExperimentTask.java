package org.xper.allen.nafc.experiment;

/**
 * A {@link NAFCExperimentTask} for the coherence (interleaved variant/delta) trial type. In addition
 * to the normal sample, it carries the second sample's spec (the delta) and the coherence level, so
 * the scene can build a per-pixel mixture of the two shapes.
 *
 * <p>The task type is the runtime discriminator: {@code NoisyNAFCPngScene} switches on
 * {@code instanceof CoherenceNAFCExperimentTask}, and {@code AllenDbUtil} builds this subclass only
 * when the stored {@code NAFCStimSpecSpec.stimType} equals {@link #STIM_TYPE}. Every other stimType
 * (named or {@code "None"}) yields a plain {@link NAFCExperimentTask} and the existing draw path.
 *
 * @author Allen Chen
 */
public class CoherenceNAFCExperimentTask extends NAFCExperimentTask {

    /**
     * The {@code stimType} label that identifies a coherence trial. Must match the value the coherence
     * block generator writes into {@code NAFCStimSpecSpec.stimType} (by convention the generator's
     * {@code getClass().getSimpleName()}).
     */
    public static final String STIM_TYPE = "EStimShapeCoherenceNAFCStim";

    /** XML spec (a {@code NoisyPngSpec}) of the second shape to mix with the sample, e.g. the delta. */
    private String secondSampleSpec;

    /** Signed coherence in [-1, 1]: -1 = all second shape, 0 = balanced (0% coherence), +1 = all sample. */
    private double coherence;

    public String getSecondSampleSpec() {
        return secondSampleSpec;
    }

    public void setSecondSampleSpec(String secondSampleSpec) {
        this.secondSampleSpec = secondSampleSpec;
    }

    public double getCoherence() {
        return coherence;
    }

    public void setCoherence(double coherence) {
        this.coherence = coherence;
    }
}
