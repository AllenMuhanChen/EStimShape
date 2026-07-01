package org.xper.allen.nafc.experiment.bias;

/**
 * Turns a bias score into a concrete reward/punishment adjustment, and holds the operator-facing
 * knobs and feature toggles for the anti-bias controller. All reward knobs are expressed as a
 * fraction of the trial's normal reward (1.0 = 100%).
 *
 * <p>Reduced reward for a correct pick of a biased stimulus interpolates linearly from
 * {@link #rewardFractionAtFlag} (at the flag threshold {@link #sHigh}) down to
 * {@link #rewardFractionAtFullBias} (at total lock-on, score 1.0). A correct pick that avoids a
 * currently-biased stimulus pays {@link #biasBreakRewardFraction}. A wrong guess of a biased
 * stimulus adds {@link #extraItiMs} of inter-trial interval.
 *
 * <p>Each mechanism has its own toggle, and {@link #shadowMode} disables all shaping (detect + log
 * only) so the detector can be validated on real sessions before it drives reward.
 */
public class RewardShaper {

    private boolean shadowMode = true;              // start safe: measure + log, change nothing
    private boolean enableReducedReward = true;
    private boolean enableBiasBreakReward = true;
    private boolean enableBiasIti = true;

    private double rewardFractionAtFlag = 0.60;     // reward at the moment a stimulus is flagged
    private double rewardFractionAtFullBias = 0.20; // reward at total lock-on (the floor)
    private double biasBreakRewardFraction = 1.50;  // reward for correctly avoiding a flagged stimulus
    private int extraItiMs = 3000;                  // extra ITI on a biased wrong guess

    /** Flag threshold, mirrored from the tracker so reduced-reward interpolation starts at the flag. */
    private double sHigh = 0.60;

    /** Reward fraction for correctly picking a biased stimulus, given its current bias score. */
    public double reducedRewardFraction(double biasScore) {
        if (!enableReducedReward) {
            return 1.0;
        }
        double span = 1.0 - sHigh;
        double t = span <= 0 ? 1.0 : (biasScore - sHigh) / span;
        t = clamp01(t);
        return rewardFractionAtFlag + (rewardFractionAtFullBias - rewardFractionAtFlag) * t;
    }

    /** Reward fraction for a correct choice that avoided a currently-biased stimulus. */
    public double biasBreakFraction() {
        return enableBiasBreakReward ? biasBreakRewardFraction : 1.0;
    }

    /** Extra ITI to impose on a biased wrong guess, in microseconds (0 if disabled). */
    public long extraItiMicros() {
        return enableBiasIti ? (long) extraItiMs * 1000L : 0L;
    }

    private static double clamp01(double v) {
        return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v);
    }

    public boolean isShadowMode() { return shadowMode; }
    public void setShadowMode(boolean shadowMode) { this.shadowMode = shadowMode; }

    public boolean isEnableReducedReward() { return enableReducedReward; }
    public void setEnableReducedReward(boolean v) { this.enableReducedReward = v; }

    public boolean isEnableBiasBreakReward() { return enableBiasBreakReward; }
    public void setEnableBiasBreakReward(boolean v) { this.enableBiasBreakReward = v; }

    public boolean isEnableBiasIti() { return enableBiasIti; }
    public void setEnableBiasIti(boolean v) { this.enableBiasIti = v; }

    public double getRewardFractionAtFlag() { return rewardFractionAtFlag; }
    public void setRewardFractionAtFlag(double v) { this.rewardFractionAtFlag = v; }

    public double getRewardFractionAtFullBias() { return rewardFractionAtFullBias; }
    public void setRewardFractionAtFullBias(double v) { this.rewardFractionAtFullBias = v; }

    public double getBiasBreakRewardFraction() { return biasBreakRewardFraction; }
    public void setBiasBreakRewardFraction(double v) { this.biasBreakRewardFraction = v; }

    public int getExtraItiMs() { return extraItiMs; }
    public void setExtraItiMs(int v) { this.extraItiMs = v; }

    public double getSHigh() { return sHigh; }
    public void setSHigh(double v) { this.sHigh = v; }
}
