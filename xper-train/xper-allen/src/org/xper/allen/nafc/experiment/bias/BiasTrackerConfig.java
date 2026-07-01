package org.xper.allen.nafc.experiment.bias;

/**
 * Tuning for the NAFC anti-bias detector ({@link BiasTracker}). All detection parameters live here so
 * they can be set once (e.g. from Spring) and shared. The human-readable framing agreed with the
 * experimenter maps onto these numeric fields as follows:
 *
 * <ul>
 *   <li><b>memory (appearances)</b> &rarr; {@link #lambda}: effective window &asymp; 1/(1-lambda).
 *       lambda=0.8 &asymp; the last ~5 times a stimulus appeared as a wrong option.</li>
 *   <li><b>flag / un-flag wrong-pick rate</b> &rarr; {@link #sHigh}/{@link #sLow}: the bias score is
 *       the wrong-pick rate rescaled so 0 = chance (1/N) and 1 = always-picks-when-wrong. For a
 *       triplet, sHigh=0.6 &asymp; picking the stimulus ~73% of the times it is wrong; sLow=0.35
 *       &asymp; ~57%.</li>
 *   <li><b>minimum appearances</b> &rarr; {@link #nMin}: don't flag until the stimulus has been a
 *       wrong option at least this many times.</li>
 *   <li><b>inversion guard</b> &rarr; {@link #hMin}: if, while flagged, the hit-rate on trials where
 *       the stimulus IS the answer falls below this, the animal is avoiding it &mdash; un-flag so we
 *       never train avoidance.</li>
 * </ul>
 */
public class BiasTrackerConfig {

    /** EWMA decay. Higher = longer memory, slower to react and slower to forgive. */
    private double lambda = 0.8;

    /** Enter the biased state when the bias score rises to at least this (0 = chance, 1 = total lock-on). */
    private double sHigh = 0.60;

    /** Exit the biased state when the bias score falls to at most this. Must be &lt; sHigh (hysteresis). */
    private double sLow = 0.35;

    /** Minimum number of appearances as a wrong option before a stimulus may be flagged. */
    private int nMin = 8;

    /** Inversion guard: while biased, un-flag if hit-rate on correct-answer trials drops below this. */
    private double hMin = 0.40;

    /** Minimum appearances as the correct answer before the inversion guard is allowed to fire. */
    private int nMinInversion = 8;

    public double getLambda() { return lambda; }
    public void setLambda(double lambda) { this.lambda = lambda; }

    public double getSHigh() { return sHigh; }
    public void setSHigh(double sHigh) { this.sHigh = sHigh; }

    public double getSLow() { return sLow; }
    public void setSLow(double sLow) { this.sLow = sLow; }

    public int getNMin() { return nMin; }
    public void setNMin(int nMin) { this.nMin = nMin; }

    public double getHMin() { return hMin; }
    public void setHMin(double hMin) { this.hMin = hMin; }

    public int getNMinInversion() { return nMinInversion; }
    public void setNMinInversion(int nMinInversion) { this.nMinInversion = nMinInversion; }
}
