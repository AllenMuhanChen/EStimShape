package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;

import javax.sql.DataSource;
import javax.vecmath.Point3d;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.Set;

/**
 * NAFC trial where the sample has the tuned-for component deleted.
 *
 * <p>When {@code includeRemovedChoice} is true the choices are the deleted shape itself (the
 * match) plus the variant (original shape, tuned-for component intact) and the delta (shape
 * where the tuned-for component was changed to a non-driving variant). The deleted shape is the
 * unambiguous correct answer; variant and delta are rewarded only on ambiguous/eStim trials.
 *
 * <p>When {@code includeRemovedChoice} is false the deleted shape is not offered as a choice.
 * Since no exact match for a deleted sample exists, the variant stands in as the match slot and
 * the delta is the sole procedural distractor; the trial is forced ambiguous so both are
 * rewarded. This keeps the choice set ({variant, delta}) consistent with the variant/delta
 * trial types under the same setting. Random distractors are produced per the parent class.
 */
public class EStimShapeVariantsDeletedNAFCStim extends EStimShapeVariantsNAFCStim {

    protected long deltaMStickStimSpecId;

    public static EStimShapeVariantsDeletedNAFCStim createSampledDeletedNAFCStim(
            EStimShapeExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            boolean isEStimEnabled,
            Long eStimSpecId) {

        DataSource gaDataSource = generator.getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        List<Long> variantIds = gaJDBCTemplate.queryForList(
                "SELECT DISTINCT variant_id FROM IncludedDeltas WHERE included = TRUE",
                Long.class
        );

        if (variantIds.isEmpty()) {
            throw new RuntimeException("No variants with included deltas found in IncludedDeltas table. " +
                    "Run the PlotVariantDeltas analysis pipeline first to populate this table.");
        }

        Random random = new Random();
        long variantId = variantIds.get(random.nextInt(variantIds.size()));

        return new EStimShapeVariantsDeletedNAFCStim(generator, parameters, variantId, isEStimEnabled, eStimSpecId);
    }

    public EStimShapeVariantsDeletedNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, Long variantId, boolean isEStimEnabled, Long eStimSpecId) {
        super(generator, parameters, variantId, isEStimEnabled, eStimSpecId);
        // Sample is built from the variant (its tuned-for comp is then deleted).
        baseMStickStimSpecId = variantId;
        deltaMStickStimSpecId = getDeltaIdFromVariantId(variantId);
    }

    private long getDeltaIdFromVariantId(Long variantId) {
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        List<Long> deltaIds = gaJDBCTemplate.queryForList(
                "SELECT delta_id FROM IncludedDeltas WHERE variant_id = ? AND included = TRUE",
                new Object[]{variantId},
                Long.class
        );

        if (deltaIds.isEmpty()) {
            throw new RuntimeException("No included deltas found for variant_id: " + variantId);
        }

        Random random = new Random();
        return deltaIds.get(random.nextInt(deltaIds.size()));
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        // Load the variant (intact) — this is both the source for deletion and the geometry
        // we use to compute where the noise circle should appear. Variant/delta trials place
        // the noise at the preserved comp's junction; we want the deleted trial's noise to
        // land at the same screen location so trial type can't be inferred from noise.
        AllenMStickSpec variantSpec = new AllenMStickSpec();
        PruningMatchStick variantMStick = new PruningMatchStick(noiseMapper);
        variantMStick.setProperties(sampleSize, texture, is2D(), 1.0);
        variantMStick.setStimColor(color);
        variantMStick.setRf(rfSource.getReceptiveField());
        variantMStick.genMatchStickFromFile(gaSpecPath + "/" + baseMStickStimSpecId + "_spec.xml");
        variantSpec.setMStickInfo(variantMStick, false);

        // Compute noise origin from the intact variant. checkInNoise both validates and
        // populates variantMStick.noiseOrigin; we reuse that on the deleted sample below.
        noiseMapper.checkInNoise(variantMStick, noiseComponentIndcs, 0.45);
        Point3d variantNoiseOrigin = variantMStick.getNoiseOrigin();

        // Pick a positioning anchor: the first variant component that isn't being deleted.
        // After deletion the preserved comp is gone, so positionShape can't use it.
        Set<Integer> toRemove = new HashSet<>(noiseComponentIndcs);
        Integer anchorInParent = null;
        for (Integer compId : variantMStick.getCompIds()) {
            if (compId != 0 && !toRemove.contains(compId)) {
                anchorInParent = compId;
                break;
            }
        }
        if (anchorInParent == null) {
            throw new RuntimeException("No non-preserved component available to anchor positioning for deleted sample (variantId=" + baseMStickStimSpecId + ")");
        }
        // removeComponent compacts indices: surviving comps keep their relative order, so the
        // child index equals the parent index minus the number of removed comps that came before it.
        int anchorInChild = anchorInParent;
        for (Integer removedComp : toRemove) {
            if (removedComp < anchorInParent) {
                anchorInChild--;
            }
        }

        PruningMatchStick sample = new PruningMatchStick(noiseMapper);
        sample.setProperties(sampleSize, texture, is2D(), 1.0);
        sample.setStimColor(color);
        sample.setRf(rfSource.getReceptiveField());
        sample.setPositioningAnchor(variantMStick, anchorInChild, anchorInParent);
        sample.genRemovedLimbsMatchStick(variantMStick, toRemove);

        // Carry the variant's noise origin onto the deleted sample so generateGaussianNoiseMapFor
        // renders the noise circle in the same world location as the variant/delta would.
        sample.setNoiseOrigin(variantNoiseOrigin);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        return sample;
    }

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        if (includeRemovedChoice) {
            // The removed shape is offered as a choice, so the match is a clean copy of the
            // deleted sample (parent regenerates match from the sample spec).
            super.generateMatch(sample);
        } else {
            // The removed shape is not offered. There is no exact match for a deleted sample,
            // so the variant stands in as slot 0 to keep reward indexing valid. Both the
            // variant (match) and the delta (procedural distractor) are rewarded via the
            // forced-ambiguous policy (see isAmbiguousTrial).
            PruningMatchStick match = buildChoiceFromSpec(baseMStickStimSpecId);
            mSticks.setMatch(match);
            mStickSpecs.setMatch(mStickToSpec(match));
        }
    }

    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        if (includeRemovedChoice) {
            // Removed shape is the sample/match; variant and delta are both procedural choices.
            if (numProceduralDistractors != 2) {
                throw new IllegalStateException("Deleted trial with includeRemovedChoice requires exactly 2 procedural distractors (variant + delta), got " + numProceduralDistractors + ". Set numChoices=" + (3 + numRandDistractors) + " or adjust numRandDistractors.");
            }
            PruningMatchStick variantDistractor = buildChoiceFromSpec(baseMStickStimSpecId);
            mSticks.addProceduralDistractor(variantDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(variantDistractor));

            PruningMatchStick deltaDistractor = buildChoiceFromSpec(deltaMStickStimSpecId);
            mSticks.addProceduralDistractor(deltaDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(deltaDistractor));
        } else {
            // Removed shape is hidden; variant is the match (see generateMatch), delta is the
            // sole procedural distractor.
            if (numProceduralDistractors != 1) {
                throw new IllegalStateException("Deleted trial without includeRemovedChoice requires exactly 1 procedural distractor (delta), got " + numProceduralDistractors + ". Set numChoices=" + (2 + numRandDistractors) + " or adjust numRandDistractors.");
            }
            PruningMatchStick deltaDistractor = buildChoiceFromSpec(deltaMStickStimSpecId);
            mSticks.addProceduralDistractor(deltaDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(deltaDistractor));
        }
    }

    private PruningMatchStick buildChoiceFromSpec(long specId) {
        PruningMatchStick choice = new PruningMatchStick(noiseMapper);
        correctNoiseRadius(choice);
        choice.setProperties(choiceSize, texture, is2D(), 1.0);
        choice.setStimColor(color);
        choice.setMaxDiameterDegrees(maxSampleSize);
        choice.genMatchStickFromFile(gaSpecPath + "/" + specId + "_spec.xml");
        choice.centerShape();
        return choice;
    }

    @Override
    protected boolean isAmbiguousTrial() {
        // Without the removed choice there is no exact match for the deleted sample: both the
        // variant and the delta are reasonable completions, so reward both regardless of noise.
        return !includeRemovedChoice || super.isAmbiguousTrial();
    }

    @Override
    protected void assignLabels() {
        labels.setSample(new LinkedList<>(Arrays.asList("sample")));
        if (includeRemovedChoice) {
            labels.setMatch(new LinkedList<>(Arrays.asList("match")));
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("variant")));
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("delta")));
        } else {
            labels.setMatch(new LinkedList<>(Arrays.asList("variant")));
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("delta")));
        }
        for (int i = 0; i < numRandDistractors; i++) {
            labels.addRandDistractor(new LinkedList<>(Arrays.asList("rand")));
        }
    }
}
