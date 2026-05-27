package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;

import javax.sql.DataSource;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;

public class EStimShapeVariantsDeltaNAFCStim extends EStimShapeVariantsNAFCStim{
    protected boolean isDelta;
    // The non-sample shapes offered as procedural distractors. In a variant trial these are the
    // variant's included deltas; in a delta trial they are the variant plus the other deltas.
    protected List<Long> distractorMStickStimSpecIds;

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

        List<Long> includedDeltaIds = getDeltaIdsFromVariantId(variantId);

        if (isDelta){
            // Sample is one of the deltas; the remaining choices are the variant and the other deltas.
            Random random = new Random();
            long sampleDeltaId = includedDeltaIds.get(random.nextInt(includedDeltaIds.size()));
            baseMStickStimSpecId = sampleDeltaId;

            distractorMStickStimSpecIds = new ArrayList<>();
            distractorMStickStimSpecIds.add(variantId);
            for (Long deltaId : includedDeltaIds) {
                if (!deltaId.equals(sampleDeltaId)) {
                    distractorMStickStimSpecIds.add(deltaId);
                }
            }
        } else{
            // Sample is the variant; the choices are the variant's included deltas.
            baseMStickStimSpecId = variantId;
            distractorMStickStimSpecIds = new ArrayList<>(includedDeltaIds);
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

    private List<Long> getDeltaIdsFromVariantId(Long variantId) {
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

        return deltaIds;
    }



    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        // The number of delta distractors autowires from numProceduralDistractors (which the GUI
        // derives as numChoices - numRandDistractors - 1), minus the removed-choice slot when used.
        int numRemovedSlots = includeRemovedChoice ? 1 : 0;
        int numDeltaSlots = numProceduralDistractors - numRemovedSlots;

        if (numDeltaSlots < 0) {
            throw new IllegalStateException("includeRemovedChoice requires at least 1 procedural distractor slot for the removed choice, but numProceduralDistractors=" + numProceduralDistractors + ". Increase numChoices or reduce numRandDistractors.");
        }
        // No-go: can't ask for more delta distractors than there are delta pairs for this variant.
        if (numDeltaSlots > distractorMStickStimSpecIds.size()) {
            throw new IllegalStateException("Requested " + numDeltaSlots + " procedural delta distractor(s) for variant/delta trial, but only " + distractorMStickStimSpecIds.size() + " delta pair(s) are available for this variant. Reduce numChoices, increase numRandDistractors, or produce more deltas.");
        }

        // Slots 0..numDeltaSlots-1: the non-sample shapes (deltas if sample is variant; variant +
        // other deltas if sample is delta).
        for (int i = 0; i < numDeltaSlots; i++) {
            long specId = distractorMStickStimSpecIds.get(i);
            PruningMatchStick distractorMStick = new PruningMatchStick(noiseMapper);
            correctNoiseRadius(distractorMStick);
            distractorMStick.setProperties(choiceSize, texture, is2D(), 1.0);
            distractorMStick.setStimColor(color);
            distractorMStick.setMaxDiameterDegrees(maxSampleSize);
            distractorMStick.genMatchStickFromFile(gaSpecPath + "/" + specId + "_spec.xml");
            distractorMStick.centerShape();
            mSticks.addProceduralDistractor(distractorMStick);
            mStickSpecs.addProceduralDistractor(mStickToSpec(distractorMStick));
        }

        // Last slot: the variant with the tuned-for comp deleted.
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
        // The delta slots are always labeled "delta" — this is the established analysis convention
        // (nafc_database_fields.py IsHypothesizedField). The label denotes "non-match
        // procedural slot," not the literal identity: in a variant trial those files hold the
        // real deltas; in a delta trial they hold the variant and the other deltas.
        // IsHypothesizedField forks on IsDelta to interpret it correctly.
        int numRemovedSlots = includeRemovedChoice ? 1 : 0;
        int numDeltaSlots = numProceduralDistractors - numRemovedSlots;
        for (int i = 0; i < numDeltaSlots; i++) {
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("delta")));
        }
        if (includeRemovedChoice) {
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("removed")));
        }
        for (int i = 0; i < numRandDistractors; i++) {
            labels.addRandDistractor(new LinkedList<>(Arrays.asList("rand")));
        }
    }

}
