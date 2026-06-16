package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.pga.MStickPosition;
import org.xper.allen.pga.PositionPropertyManager;
import org.xper.allen.stimproperty.*;
import org.xper.allen.util.AllenDbUtil;

import javax.sql.DataSource;
import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

public class EStimShapeVariantsNAFCStim extends EStimShapeProceduralStim{

    public static final int MAX_CHOICE_SIZE = 5;
    protected DataSource gaDataSource;
    protected double maxSampleSize;
    protected List<Integer> noiseComponentIndcs;
    // The variant ("variant" role) of this trial's pair. For a variant trial this is the sample;
    // for a delta trial the sample is the delta and this is its parent variant.
    protected Long variantId;
    protected String gaSpecPath;
    protected String texture;
    protected Float sampleSize;
    protected NAFCNoiseMapper noiseMapper;
    protected ReceptiveField receptiveField;
    // When true, one procedural distractor slot is filled by a "removed" shape — the variant
    // with its tuned-for component deleted. Keeps the choice set composition the same across
    // variant/delta/deleted trial types so trial type can't be inferred from which choices appear.
    protected boolean includeRemovedChoice = false;

    public void setIncludeRemovedChoice(boolean includeRemovedChoice) {
        this.includeRemovedChoice = includeRemovedChoice;
    }


    public static EStimShapeVariantsNAFCStim createSampledIdEStimShapeVariantsNAFCStim(
            EStimShapeExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            boolean isEStimEnabled,
            Long eStimSpecId) {

        DataSource gaDataSource = generator.getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        // Get all non-excluded variants from IncludedVariants table
        List<Long> variantIds = gaJDBCTemplate.queryForList(
                "SELECT stim_id FROM IncludedVariants WHERE manually_excluded = FALSE",
                Long.class
        );

        if (variantIds.isEmpty()) {
            throw new RuntimeException("No included variants found in IncludedVariants table. " +
                    "Run the PlotVariants analysis pipeline first to populate this table.");
        }

        // Randomly select one
        Random random = new Random();
        long variantId = variantIds.get(random.nextInt(variantIds.size()));

        return new EStimShapeVariantsNAFCStim(generator, parameters, variantId, isEStimEnabled, eStimSpecId);
    }

    public EStimShapeVariantsNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, Long variantId, boolean isEStimEnabled, Long eStimSpecId){
        super(generator, parameters, null, new ArrayList<>(), isEStimEnabled, variantId, -1, eStimSpecId);
        this.variantId = variantId;
        gaSpecPath = generator.getGaSpecPath();

        gaDataSource = generator.getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);
        SizePropertyManager sizePropertyManager = new SizePropertyManager(gaJDBCTemplate);
        TexturePropertyManager texturePropertyManager = new TexturePropertyManager(gaJDBCTemplate);
        ColorPropertyManager colorPropertyManager = new ColorPropertyManager(gaJDBCTemplate);
        UnderlingAverageRGBPropertyManager underlingAverageRGBPropertyManager = new UnderlingAverageRGBPropertyManager(gaJDBCTemplate);
        HypothesizedCompManager hypothesizedCompManager = new HypothesizedCompManager(gaJDBCTemplate);

        sampleSize = sizePropertyManager.readProperty(variantId);

        texture = texturePropertyManager.readProperty(variantId);
        if (texture.equals("2D")){
            color = underlingAverageRGBPropertyManager.readProperty(variantId);
        } else {
            color = colorPropertyManager.readProperty(variantId);
        }

        maxChoiceSize = generator.getMaxChoiceDimensionDegrees() * 0.8;
        maxSampleSize = generator.getMaxSampleDimensionDegrees();

        choiceSize = Math.min(sampleSize, MAX_CHOICE_SIZE);

        double choiceLim = calculateMinDistanceChoicesCanBeWithoutOverlap(maxChoiceSize, parameters.numChoices) + 1;

        parameters.setChoiceDistanceLims(new Lims(choiceLim, choiceLim));
        parameters.setEyeWinRadius(maxChoiceSize/2); // 4 back to back limbs, and divide by two for radius corr

        noiseMapper = generator.getNoiseMapper();
        receptiveField = generator.getRfSource().getReceptiveField();
        List<Integer> hypothesizedComp = resolveHypothesizedComp(variantId, gaJDBCTemplate, hypothesizedCompManager);
        morphComponentIndcs = hypothesizedComp;
        noiseComponentIndcs = hypothesizedComp;
    }

    /**
     * Resolve the variant's hypothesized (driving) component: the one whose junction we noise,
     * whose limb we morph for procedural distractors, and which the deleted trial removes.
     *
     * <p>The GA may have exploited a component other than the variant's original (often random)
     * hypothesized comp, so we prefer the component that the variant's <em>included deltas</em>
     * actually mutated — that is the empirically discovered driver. This holds even for
     * variant-only trials: the deltas still tell us which component to test. We fall back to the
     * variant's own stored hypothesized comp when no usable delta information exists (e.g. the
     * IncludedDeltas table hasn't been populated, or the variant has no included deltas).
     *
     * <p>On a legacy (un-migrated) DB we keep the original behavior outright, because old delta
     * rows were written as copies of their parent's row and so don't reliably record what the
     * delta mutated.
     */
    protected List<Integer> resolveHypothesizedComp(Long variantId, JdbcTemplate gaJDBCTemplate,
                                                    HypothesizedCompManager hypothesizedCompManager) {
        if (hypothesizedCompManager.isLegacyTable()) {
            List<Integer> legacy = hypothesizedCompManager.readHypothesizedCompOrNull(variantId);
            if (legacy != null) {
                return legacy;
            }
            return fallbackToPositionTargetComp(variantId, gaJDBCTemplate);
        }

        if (tableExists(gaJDBCTemplate, "IncludedDeltas")) {
            List<Long> deltaIds = gaJDBCTemplate.queryForList(
                    "SELECT delta_id FROM IncludedDeltas WHERE variant_id = ? AND included = TRUE",
                    new Object[]{variantId}, Long.class);
            // The GA's explore phase deliberately tries several components, so included deltas may
            // span more than one. Take the component the majority of them mutated: the exploit
            // phase converges on the true driver, so that is the most frequent comp. Ties break on
            // the lower component index for determinism.
            Map<List<Integer>, Integer> counts = new HashMap<>();
            for (Long deltaId : deltaIds) {
                if (hypothesizedCompManager.hasProperty(deltaId)) {
                    List<Integer> mutated = hypothesizedCompManager.readProperty(deltaId).getParentHypothesizedComps();
                    if (mutated != null && !mutated.isEmpty()) {
                        counts.merge(mutated, 1, Integer::sum);
                    }
                }
            }
            List<Integer> majority = null;
            int bestCount = -1;
            for (Map.Entry<List<Integer>, Integer> e : counts.entrySet()) {
                if (e.getValue() > bestCount
                        || (e.getValue() == bestCount && compareComps(e.getKey(), majority) < 0)) {
                    majority = e.getKey();
                    bestCount = e.getValue();
                }
            }
            if (majority != null) {
                return majority;
            }
            // no usable delta rows: fall through to the variant's own hypothesized comp
        }

        List<Integer> own = hypothesizedCompManager.readHypothesizedCompOrNull(variantId);
        if (own != null) {
            return own;
        }
        return fallbackToPositionTargetComp(variantId, gaJDBCTemplate);
    }

    /**
     * Last-resort source for the hypothesized comp: the preserved component recorded on the
     * variant's stored position (its target comp), which every preserved-comp-based GA stim
     * writes. Fails with a clear message if even that is unavailable, instead of an opaque
     * EmptyResultDataAccessException from an unguarded read.
     */
    private List<Integer> fallbackToPositionTargetComp(Long variantId, JdbcTemplate gaJDBCTemplate) {
        try {
            PositionPropertyManager positionManager = new PositionPropertyManager(gaJDBCTemplate);
            MStickPosition variantPosition = positionManager.readProperty(variantId);
            if (variantPosition != null && variantPosition.getTargetComp() != null) {
                System.err.println("################################################################################");
                System.err.println("## CRITICAL WARNING: HypothesizedComp FALLBACK TRIGGERED - THIS SHOULD NEVER HAPPEN");
                System.err.println("## NAFC: variant " + variantId + " has no usable HypothesizedComp row (missing or");
                System.err.println("## empty comp list) and no usable included-delta information. Falling back to the");
                System.err.println("## target comp on its stored position: " + variantPosition.getTargetComp());
                System.err.println("## Every preserved-comp-based GA stimulus should persist its hypothesized comp at");
                System.err.println("## generation time. If you see this, HypothesizedComp rows are not being written");
                System.err.println("## (or are being read from the wrong table) - investigate before trusting trials.");
                System.err.println("################################################################################");
                return new ArrayList<>(Collections.singletonList(variantPosition.getTargetComp()));
            }
        } catch (EmptyResultDataAccessException e) {
            // fall through to the explicit error below
        }
        throw new RuntimeException("Could not resolve hypothesized comp for variant " + variantId +
                ": no usable HypothesizedComp row (missing or empty), no included-delta information," +
                " and no target comp on its stored position. Was this stimulus generated with an" +
                " older pipeline, or did its generation fail?");
    }

    /** Lexicographic comparison of component lists, used only to break majority-vote ties. */
    private int compareComps(List<Integer> a, List<Integer> b) {
        if (b == null) return -1;
        for (int i = 0; i < Math.min(a.size(), b.size()); i++) {
            int c = Integer.compare(a.get(i), b.get(i));
            if (c != 0) return c;
        }
        return Integer.compare(a.size(), b.size());
    }

    private boolean tableExists(JdbcTemplate jt, String name) {
        Integer count = (Integer) jt.queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = ?",
                new Object[]{name}, Integer.class);
        return count != null && count > 0;
    }

    protected boolean is2D() {
        return this.texture.equals("2D");
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            try {
                PruningMatchStick sample = (PruningMatchStick) generateSample();

                generateMatch(sample);

                generateProceduralDistractors(sample);

                generateRandDistractors();

                break;
            } catch (Exception e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
                System.out.println("BaseMStickId is: " + baseMStickStimSpecId);
            }
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

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        PruningMatchStick match = new  PruningMatchStick(noiseMapper);
        match.setProperties(choiceSize, texture, is2D(), 1.0);
        match.setStimColor(color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.moveCenterOfMassTo(new Point3d(0,0,0));

        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
    }

    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        int startIndex = 0;
        if (includeRemovedChoice && numProceduralDistractors >= 1) {
            ProceduralMatchStick removed = createRemovedDistractor();
            mSticks.addProceduralDistractor(removed);
            mStickSpecs.addProceduralDistractor(mStickToSpec(removed));
            startIndex = 1;
        }
        for (int i = startIndex; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick(noiseMapper);
            correctNoiseRadius(proceduralDistractor);
            proceduralDistractor.setProperties(choiceSize, texture, is2D(), 1.0);
            proceduralDistractor.setStimColor(color);
            proceduralDistractor.setMaxDiameterDegrees(maxSampleSize); //TODO: using max sample size here due to weird glitch with using max choice size...
            proceduralDistractor.genNewComponentsMatchStick(sample, morphComponentIndcs, parameters.morphMagnitude, 0.5, true, proceduralDistractor.maxAttempts, noiseComponentIndcs);
            mSticks.addProceduralDistractor(proceduralDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(proceduralDistractor));
        }
    }

    /**
     * Build a choice-sized matchstick that is the variant ({@link #baseMStickStimSpecId}) with
     * its tuned-for components ({@link #noiseComponentIndcs}) deleted. Used by subclasses as a
     * distractor; the returned mStick is centered (no anchor alignment) since each choice is
     * rendered into its own tile and doesn't need to align with the sample's world frame.
     */
    protected ProceduralMatchStick createRemovedDistractor() {
        PruningMatchStick variantSource = new PruningMatchStick(noiseMapper);
        variantSource.setProperties(choiceSize, texture, is2D(), 1.0);
        variantSource.setStimColor(color);
        variantSource.genMatchStickFromFile(gaSpecPath + "/" + baseMStickStimSpecId + "_spec.xml");
        variantSource.centerShape();

        ProceduralMatchStick removed = new ProceduralMatchStick(noiseMapper);
        correctNoiseRadius(removed);
        removed.setProperties(choiceSize, texture, is2D(), 1.0);
        removed.setStimColor(color);
        removed.genRemovedLimbsMatchStick(variantSource, new HashSet<>(noiseComponentIndcs));
        return removed;
    }

    @Override
    protected void assignLabels() {
        labels.setSample(new LinkedList<>(Arrays.asList("sample")));
        labels.setMatch(new LinkedList<>(Arrays.asList("match")));
        for (int i = 0; i < numProceduralDistractors; i++) {
            if (i == 0 && includeRemovedChoice) {
                labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("removed")));
            } else {
                labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("procedural")));
            }
        }
        for (int i = 0; i < numRandDistractors; i++) {
            labels.addRandDistractor(new LinkedList<>(Arrays.asList("rand")));
        }
    }

    protected void generateRandDistractors() {
        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            randDistractor.setProperties(choiceSize, texture, is2D(),1.0);
            randDistractor.setStimColor(color);
            randDistractor.genMatchStickRand();
            mSticks.addRandDistractor(randDistractor);
            mStickSpecs.addRandDistractor(mStickToSpec(randDistractor));
        }
    }

    protected void generateNoiseMap() {
        String generatorNoiseMapPath = samplePngMaker.createAndSaveNoiseMap(
                mSticks.getSample(),
                stimObjIds.getSample(),
                labels.getSample(),
                generator.getGeneratorNoiseMapPath(),
                parameters.noiseChance, noiseComponentIndcs);
        experimentNoiseMapPath = generator.convertGeneratorNoiseMapToExperiment(generatorNoiseMapPath);
    }


    protected void writeExtraData() {
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeBaseMStickId(getStimId(), baseMStickStimSpecId); //don't really need to save this info since it's present in another table
        // Record the sample's role unambiguously for analysis (needed for delta->delta chains).
        dbUtil.writeSampleRole(getStimId(), isSampleDelta(), variantId);
    }

    /**
     * Whether this trial's sample is the delta (hypothesized-changed) rather than the variant
     * (hypothesized-preserved). Variant and deleted trials override to the variant role (false);
     * delta trials override to true.
     */
    protected boolean isSampleDelta() {
        return false;
    }




}
