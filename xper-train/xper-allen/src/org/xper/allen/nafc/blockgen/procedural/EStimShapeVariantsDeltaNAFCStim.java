package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;

import javax.sql.DataSource;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;

public class EStimShapeVariantsDeltaNAFCStim extends EStimShapeVariantsNAFCStim{
    protected boolean isDelta;
    protected long distractorMStickStimSpecId;

    public static EStimShapeVariantsDeltaNAFCStim createSampledDeltaNAFCStim(
            EStimShapeExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            boolean isDelta,
            boolean isEStimEnabled,
            Long eStimSpecId) {

        DataSource gaDataSource = generator.getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        // Get all non-excluded variants that have included deltas
        List<Long> variantIds = gaJDBCTemplate.queryForList(
                "SELECT DISTINCT variant_id FROM IncludedDeltas WHERE included = TRUE",
                Long.class
        );

        if (variantIds.isEmpty()) {
            throw new RuntimeException("No variants with included deltas found in IncludedDeltas table. " +
                    "Run the PlotVariantDeltas analysis pipeline first to populate this table.");
        }

        // Randomly select one variant
        Random random = new Random();
        long variantId = variantIds.get(random.nextInt(variantIds.size()));

        return new EStimShapeVariantsDeltaNAFCStim(generator, parameters, variantId, isDelta, isEStimEnabled, eStimSpecId);
    }

    public EStimShapeVariantsDeltaNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, Long variantId, boolean isDelta, boolean isEStimEnabled, Long eStimSpecId) {
        super(generator, parameters, variantId, isEStimEnabled, eStimSpecId);
        this.isDelta = isDelta;

        if (isDelta){
            baseMStickStimSpecId = getDeltaIdFromVariantId(variantId);
            distractorMStickStimSpecId = variantId;
        } else{
            baseMStickStimSpecId = variantId;
            distractorMStickStimSpecId = getDeltaIdFromVariantId(variantId);
        }
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        AllenMStickSpec baseStickSpec = new AllenMStickSpec();
        PruningMatchStick baseMatchStick = new PruningMatchStick(noiseMapper);

        baseMatchStick.setProperties(sampleSize, texture, is2D(), 1.0);
        baseMatchStick.setStimColor(color);
        baseMatchStick.genMatchStickFromFile(gaSpecPath + "/" + baseMStickStimSpecId + "_spec.xml");
        baseStickSpec.setMStickInfo(baseMatchStick, false);

        PruningMatchStick sample = new PruningMatchStick(noiseMapper);
        sample.setProperties(sampleSize, texture, is2D(), 1.0);
        sample.setStimColor(color);
        sample.setRf(rfSource.getReceptiveField());


        sample.genMatchStickFromShapeSpec(baseStickSpec, new double[]{0,0,0});

        noiseMapper.checkInNoise(sample, noiseComponentIndcs, 0.45);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        return sample;
    }

    private long getDeltaIdFromVariantId(Long variantId) {
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        // Get all included deltas for this variant
        List<Long> deltaIds = gaJDBCTemplate.queryForList(
                "SELECT delta_id FROM IncludedDeltas WHERE variant_id = ? AND included = TRUE",
                new Object[]{variantId},
                Long.class
        );

        if (deltaIds.isEmpty()) {
            throw new RuntimeException("No included deltas found for variant_id: " + variantId);
        }

        // Randomly select one delta
        Random random = new Random();
        return deltaIds.get(random.nextInt(deltaIds.size()));
    }



    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        int required = 1 + (includeRemovedChoice ? 1 : 0);
        if (numProceduralDistractors > required) {
            throw new IllegalStateException("Excess procedural distractor slots for variant/delta trial: numProceduralDistractors=" + numProceduralDistractors + ", but only " + required + " procedural choices are defined (non-sample" + (includeRemovedChoice ? " + removed" : "") + "). Reduce numChoices or increase numRandDistractors.");
        }
        if (numProceduralDistractors < required) {
            throw new IllegalStateException("Not enough procedural distractor slots for variant/delta trial: need " + required + " (non-sample" + (includeRemovedChoice ? " + removed" : "") + ") but only " + numProceduralDistractors + " available. Random distractors are taking the slots — reduce numRandDistractors or increase numChoices.");
        }

        // Slot 0: the non-sample shape (delta if sample is variant; variant if sample is delta).
        PruningMatchStick distractorMStick = new PruningMatchStick(noiseMapper);
        correctNoiseRadius(distractorMStick);
        distractorMStick.setProperties(choiceSize, texture, is2D(), 1.0);
        distractorMStick.setStimColor(color);
        distractorMStick.setMaxDiameterDegrees(maxSampleSize);
        distractorMStick.genMatchStickFromFile(gaSpecPath + "/" + distractorMStickStimSpecId + "_spec.xml");
        distractorMStick.centerShape();
        mSticks.addProceduralDistractor(distractorMStick);
        mStickSpecs.addProceduralDistractor(mStickToSpec(distractorMStick));

        // Slot 1: the variant with the tuned-for comp deleted.
        if (includeRemovedChoice) {
            ProceduralMatchStick removed = createRemovedDistractor();
            mSticks.addProceduralDistractor(removed);
            mStickSpecs.addProceduralDistractor(mStickToSpec(removed));
        }
    }

    @Override
    protected void assignLabels() {
        labels.setSample(new LinkedList<>(Arrays.asList("sample")));
        labels.setMatch(new LinkedList<>(Arrays.asList("match")));
        // Slot 0 is the non-sample: if the sample is the variant, the distractor is the delta, and vice versa.
        String nonSampleLabel = isDelta ? "variant" : "delta";
        if (numProceduralDistractors >= 1) {
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList(nonSampleLabel)));
        }
        if (numProceduralDistractors >= 2 && includeRemovedChoice) {
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("removed")));
        }
        for (int i = 0; i < numRandDistractors; i++) {
            labels.addRandDistractor(new LinkedList<>(Arrays.asList("rand")));
        }
    }

}
