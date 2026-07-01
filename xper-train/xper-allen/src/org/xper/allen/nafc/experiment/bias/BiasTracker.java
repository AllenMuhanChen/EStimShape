package org.xper.allen.nafc.experiment.bias;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Pure, I/O-free detector of per-stimulus choice bias in the NAFC task. It maintains three EWMAs per
 * stimulus lineage id (see {@link BiasKeyState}) and a hysteretic, min-sample, inversion-guarded state
 * machine that flags a stimulus as "biased" when the animal keeps choosing it on trials where it is a
 * wrong option. Detection is separated from any reward/persistence concern: the controller feeds
 * completed, bias-eligible trials to {@link #update} and reads {@link #isBiased}/{@link #biasScore} to
 * decide shaping; a DAO handles load/persist of the {@link BiasKeyState}s.
 *
 * <p>Runs across every stimulus simultaneously, so a bias that shifts from one stimulus to another is
 * caught automatically.
 */
public class BiasTracker {

    private final BiasTrackerConfig config;
    private final Map<Long, BiasKeyState> states = new HashMap<>();

    public BiasTracker(BiasTrackerConfig config) {
        this.config = config;
    }

    /** Restore previously persisted states (e.g. on experiment startup). */
    public void load(Collection<BiasKeyState> persisted) {
        for (BiasKeyState s : persisted) {
            states.put(s.stimId, s);
        }
    }

    /**
     * Fold one completed, bias-eligible trial into the tracker.
     *
     * @param variantId  group id (variant) shared by every stimulus on this trial
     * @param presentIds lineage ids of all choices shown this trial
     * @param correctId  lineage id of the correct (matching) choice
     * @param chosenId   lineage id the animal selected
     * @param numChoices number of choices N shown this trial (sets the chance baseline 1/N)
     * @return the states touched this trial, for persistence by the caller
     */
    public List<BiasKeyState> update(long variantId, Collection<Long> presentIds,
                                     long correctId, long chosenId, int numChoices) {
        double chance = 1.0 / numChoices;
        List<BiasKeyState> touched = new ArrayList<>(presentIds.size());
        for (long id : presentIds) {
            BiasKeyState s = states.get(id);
            if (s == null) {
                s = new BiasKeyState(id, variantId);
                // Seed EWMAs to neutral so early estimates are faithful rather than biased toward 0:
                // chance for the choice signals, and a benefit-of-the-doubt 1.0 for the hit-rate so the
                // inversion guard cannot mis-fire before any evidence (also gated by nMinInversion).
                s.ewmaChose = chance;
                s.ewmaChoseWhenWrong = chance;
                s.ewmaHitWhenCorrect = 1.0;
                states.put(id, s);
            }
            s.variantId = variantId;
            s.numChoices = numChoices;

            double chose = (id == chosenId) ? 1.0 : 0.0;
            s.nPresent++;
            s.ewmaChose = ewma(s.ewmaChose, chose);
            if (id == correctId) {
                s.nCorrectPresent++;
                s.ewmaHitWhenCorrect = ewma(s.ewmaHitWhenCorrect, chose);
            } else {
                s.nDistractor++;
                s.ewmaChoseWhenWrong = ewma(s.ewmaChoseWhenWrong, chose);
            }

            s.biasScore = clamp((s.ewmaChoseWhenWrong - chance) / (1.0 - chance), 0.0, 1.0);
            updateBiasedState(s);
            touched.add(s);
        }
        return touched;
    }

    /** Hysteretic entry/exit with a minimum-sample gate on entry and an inversion guard on exit. */
    private void updateBiasedState(BiasKeyState s) {
        if (!s.biased) {
            if (s.biasScore >= config.getSHigh() && s.nDistractor >= config.getNMin()) {
                s.biased = true;
            }
        } else {
            boolean decayedOut = s.biasScore <= config.getSLow();
            boolean inverted = s.nCorrectPresent >= config.getNMinInversion()
                    && s.ewmaHitWhenCorrect < config.getHMin();
            if (inverted) {
                // We over-corrected: the animal is now avoiding the stimulus even when it is the
                // correct answer. Stop shaping and reset the wrong-pick estimate to neutral so the
                // state cannot immediately re-flag on the still-high B; the bias must be
                // re-demonstrated from scratch before we intervene again.
                s.biased = false;
                s.ewmaChoseWhenWrong = 1.0 / s.numChoices;
                s.biasScore = 0.0;
            } else if (decayedOut) {
                s.biased = false;
            }
        }
    }

    private double ewma(double prev, double sample) {
        double lambda = config.getLambda();
        return lambda * prev + (1.0 - lambda) * sample;
    }

    private static double clamp(double v, double lo, double hi) {
        return v < lo ? lo : (v > hi ? hi : v);
    }

    public BiasKeyState get(long id) {
        return states.get(id);
    }

    public boolean isBiased(long id) {
        BiasKeyState s = states.get(id);
        return s != null && s.biased;
    }

    public double biasScore(long id) {
        BiasKeyState s = states.get(id);
        return s == null ? 0.0 : s.biasScore;
    }

    public Collection<BiasKeyState> all() {
        return states.values();
    }
}
