package org.xper.allen.nafc.experiment.bias;

import java.util.List;

import javax.sql.DataSource;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim.ProceduralStimParameters;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCPunisher;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.nafc.experiment.juice.NAFCDynamicNoiseController;
import org.xper.drawing.Context;

/**
 * Anti-bias juice controller for the NAFC task. Decorates {@link NAFCDynamicNoiseController} (keeping
 * all its noise/streak reward behaviour) and, on each completed trial, measures per-stimulus choice
 * bias and shapes reward/ITI to discourage it.
 *
 * <p>Per trial it reads two flags from the trial's {@code StimSpec.data} (by stim id):
 * <ul>
 *   <li>{@code biasDataEligible} &mdash; if set, the trial updates the {@link BiasTracker} (measurement).</li>
 *   <li>{@code biasShapingEnabled} &mdash; if set (and not in shadow mode), reward/ITI shaping is
 *       applied on this trial.</li>
 * </ul>
 * These are independent: the no-estim control feeds the tracker without being shaped.
 *
 * <p>Shaping uses the bias state as of the <em>start</em> of the trial (the tracker is updated with
 * the current trial only afterwards). All bias logic is wrapped so that any failure degrades to
 * normal reward and never disrupts the trial.
 */
public class BiasControlNoiseController extends NAFCDynamicNoiseController {

    private LineageResolver lineageResolver;
    private BiasTracker biasTracker;
    private BiasControllerDao biasControllerDao;
    private RewardShaper rewardShaper;
    private NAFCPunisher punisher;
    private DataSource experimentDataSource;

    private JdbcTemplate paramsJdbc;
    private boolean stateLoaded = false;

    // Per-trial transient state.
    private NAFCExperimentTask currentTask;
    private int currentSelection = -1;
    private double pendingRewardFactor = 1.0;
    private BiasEvent pendingEvent;
    private TrialLineage pendingLineage;
    private boolean pendingEligible;

    /** Load persisted bias state into the tracker. Safe to call before any trial (lazily invoked). */
    public void init() {
        if (stateLoaded) {
            return;
        }
        try {
            biasTracker.load(biasControllerDao.loadState());
        } catch (Exception e) {
            System.err.println("BiasControl: failed to load persisted state: " + e.getMessage());
        }
        stateLoaded = true;
    }

    @Override
    public void sampleOn(long timestamp, NAFCTrialContext context) {
        super.sampleOn(timestamp, context);
        init();
        currentTask = context.getCurrentTask();
        currentSelection = -1;
        resetPending();
    }

    @Override
    public void choiceSelectionSuccess(long timestamp, int choice) {
        super.choiceSelectionSuccess(timestamp, choice);
        currentSelection = choice;
    }

    @Override
    public void choiceSelectionCorrect(long timestamp, int[] rewardList, Context context) {
        try {
            decide(timestamp, true);
        } catch (Exception e) {
            resetPending();
            System.err.println("BiasControl: decide (correct) failed: " + e.getMessage());
        }
        // Delivers reward; applyRewardShaping() scales the pulse count by pendingRewardFactor.
        super.choiceSelectionCorrect(timestamp, rewardList, context);
        finalizeTrialSafely(timestamp);
    }

    @Override
    public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {
        try {
            decide(timestamp, false);
        } catch (Exception e) {
            resetPending();
            System.err.println("BiasControl: decide (incorrect) failed: " + e.getMessage());
        }
        super.choiceSelectionIncorrect(timestamp, rewardList);
        finalizeTrialSafely(timestamp);
    }

    @Override
    protected double applyRewardShaping(double basePulses) {
        if (pendingEvent != null) {
            pendingEvent.rewardPulsesBase = basePulses;
            pendingEvent.rewardPulsesDelivered = basePulses * pendingRewardFactor;
        }
        return basePulses * pendingRewardFactor;
    }

    /** Read flags, resolve lineage, and (pre-update) decide reward/ITI shaping for this trial. */
    private void decide(long timestamp, boolean correct) {
        resetPending();
        if (currentTask == null) {
            return;
        }
        ProceduralStimParameters params = readParams(currentTask.getStimId());
        boolean eligible = params != null && params.biasDataEligible;
        boolean shapingFlagged = params != null && params.biasShapingEnabled;
        if (!eligible && !shapingFlagged) {
            return; // controller inert for this trial
        }

        TrialLineage tl = lineageResolver.resolve(currentTask, currentSelection);
        if (!tl.resolvable) {
            return;
        }
        pendingLineage = tl;
        pendingEligible = eligible;

        Long chosenId = tl.chosenId;
        boolean chosenBiased = chosenId != null && biasTracker.isBiased(chosenId);
        boolean anyBiasedDistractor = false;
        for (Long id : tl.presentIds) {
            if (id != tl.correctId && biasTracker.isBiased(id)) {
                anyBiasedDistractor = true;
                break;
            }
        }

        boolean shapeNow = shapingFlagged && !rewardShaper.isShadowMode();
        double factor = 1.0;
        long extraItiMicros = 0L;
        boolean avoided = false;
        if (shapeNow) {
            if (correct) {
                if (chosenBiased) {
                    factor = rewardShaper.reducedRewardFraction(biasTracker.biasScore(chosenId));
                } else if (anyBiasedDistractor) {
                    factor = rewardShaper.biasBreakFraction();
                    avoided = true;
                }
            } else if (chosenBiased) {
                extraItiMicros = rewardShaper.extraItiMicros();
            }
        }
        pendingRewardFactor = factor;
        if (extraItiMicros > 0L && punisher != null) {
            punisher.setItiPunishmentTime((int) extraItiMicros);
        }

        BiasEvent ev = new BiasEvent();
        ev.tstamp = timestamp;
        ev.trialStimId = currentTask.getStimId();
        ev.variantId = tl.variantId;
        ev.sampleId = tl.correctId;
        ev.chosenId = chosenId;
        ev.numChoices = tl.numChoices;
        ev.correct = correct;
        ev.chosenBiased = chosenBiased;
        ev.avoidedBiased = avoided;
        ev.biasScore = chosenId != null ? biasTracker.biasScore(chosenId) : 0.0;
        ev.extraItiMs = (int) (extraItiMicros / 1000L);
        ev.shapingApplied = shapeNow;
        ev.shadowMode = rewardShaper.isShadowMode();
        pendingEvent = ev;
    }

    private void finalizeTrialSafely(long timestamp) {
        try {
            if (pendingLineage != null && pendingEligible) {
                long chosen = pendingLineage.chosenId != null ? pendingLineage.chosenId : -1L;
                List<BiasKeyState> touched = biasTracker.update(pendingLineage.variantId,
                        pendingLineage.presentIds, pendingLineage.correctId, chosen, pendingLineage.numChoices);
                biasControllerDao.saveState(touched, timestamp);
            }
            if (pendingEvent != null) {
                biasControllerDao.logEvent(pendingEvent);
            }
        } catch (Exception e) {
            System.err.println("BiasControl: finalize failed: " + e.getMessage());
        } finally {
            resetPending();
        }
    }

    private void resetPending() {
        pendingRewardFactor = 1.0;
        pendingEvent = null;
        pendingLineage = null;
        pendingEligible = false;
    }

    private ProceduralStimParameters readParams(long stimId) {
        try {
            List<String> data = paramsJdbc().queryForList(
                    "SELECT data FROM StimSpec WHERE id = ? LIMIT 1", new Object[] { stimId }, String.class);
            if (data.isEmpty() || data.get(0) == null) {
                return null;
            }
            NAFCTrialParameters p = new NAFCTrialParameters().fromXml(data.get(0));
            return (p instanceof ProceduralStimParameters) ? (ProceduralStimParameters) p : null;
        } catch (Exception e) {
            return null;
        }
    }

    private JdbcTemplate paramsJdbc() {
        if (paramsJdbc == null) {
            paramsJdbc = new JdbcTemplate(experimentDataSource);
        }
        return paramsJdbc;
    }

    public void setLineageResolver(LineageResolver lineageResolver) { this.lineageResolver = lineageResolver; }
    public void setBiasTracker(BiasTracker biasTracker) { this.biasTracker = biasTracker; }
    public void setBiasControllerDao(BiasControllerDao dao) { this.biasControllerDao = dao; }
    public void setRewardShaper(RewardShaper rewardShaper) { this.rewardShaper = rewardShaper; }
    public void setPunisher(NAFCPunisher punisher) { this.punisher = punisher; }
    public void setExperimentDataSource(DataSource experimentDataSource) { this.experimentDataSource = experimentDataSource; }
}
