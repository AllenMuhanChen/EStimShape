package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.stimproperty.*;
import org.xper.allen.util.AllenDbUtil;

import javax.sql.DataSource;
import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.Set;

public class EStimShapeVariantsNAFCStim extends EStimShapeProceduralStim{

    public static final int MAX_CHOICE_SIZE = 5;
    protected DataSource gaDataSource;
    protected double maxSampleSize;
    protected List<Integer> noiseComponentIndcs;
    protected String gaSpecPath;
    protected String texture;
    protected Float sampleSize;
    protected NAFCNoiseMapper noiseMapper;
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
        gaSpecPath = generator.getGaSpecPath();

        gaDataSource = generator.getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);
        SizePropertyManager sizePropertyManager = new SizePropertyManager(gaJDBCTemplate);
        TexturePropertyManager texturePropertyManager = new TexturePropertyManager(gaJDBCTemplate);
        ColorPropertyManager colorPropertyManager = new ColorPropertyManager(gaJDBCTemplate);
        UnderlingAverageRGBPropertyManager underlingAverageRGBPropertyManager = new UnderlingAverageRGBPropertyManager(gaJDBCTemplate);
        CompsToPreserveManager compsToPreserveManager = new CompsToPreserveManager(gaJDBCTemplate);

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

        double choiceLim = calculateMinDistanceChoicesCanBeWithoutOverlap(maxChoiceSize, parameters.numChoices);

        parameters.setChoiceDistanceLims(new Lims(choiceLim, choiceLim));
        parameters.setEyeWinRadius(maxChoiceSize/2); // 4 back to back limbs, and divide by two for radius corr

        noiseMapper = generator.getNoiseMapper();
        morphComponentIndcs = compsToPreserveManager.readProperty(variantId).getCompsToPreserve();
        noiseComponentIndcs = compsToPreserveManager.readProperty(variantId).getCompsToPreserve();
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
        variantSource.setMaxDiameterDegrees(maxSampleSize);
        variantSource.genMatchStickFromFile(gaSpecPath + "/" + baseMStickStimSpecId + "_spec.xml");
        variantSource.centerShape();

        ProceduralMatchStick removed = new ProceduralMatchStick(noiseMapper);
        correctNoiseRadius(removed);
        removed.setProperties(choiceSize, texture, is2D(), 1.0);
        removed.setStimColor(color);
        removed.setMaxDiameterDegrees(maxSampleSize);
        removed.genRemovedLimbsMatchStick(variantSource, new HashSet<>(noiseComponentIndcs));

        // setProperties / scaleForMAxisShape is a multiplicative factor on unit-space comp data;
        // it doesn't fit the rendered shape to a target diameter. After deleting a component the
        // remaining comp data covers a smaller fraction of the variant's original unit-space
        // footprint, so the obj1 mesh ends up smaller than variant/delta tiles by however much
        // the removed comp contributed to extent. Match the variant's rendered radius so the
        // three choice tiles read at the same visual size.
        rescaleObjToMatchReference(removed, variantSource);
        return removed;
    }

    /** Scales subject.obj1 in place so its max distance from origin matches reference.obj1's. */
    private static void rescaleObjToMatchReference(ProceduralMatchStick subject, ProceduralMatchStick reference) {
        if (subject.getObj1() == null || reference.getObj1() == null) return;
        double subjectMaxR = maxRadiusFromOrigin(subject.getObj1());
        double referenceMaxR = maxRadiusFromOrigin(reference.getObj1());
        if (subjectMaxR <= 0 || referenceMaxR <= 0) return;
        if (subjectMaxR >= referenceMaxR) return;
        subject.getObj1().scaleTheObj(referenceMaxR / subjectMaxR);
    }

    private static double maxRadiusFromOrigin(org.xper.drawing.stick.MStickObj4Smooth obj) {
        double maxR = 0;
        for (int i = 1; i <= obj.getnVect(); i++) {
            javax.vecmath.Point3d v = obj.vect_info[i];
            if (v == null) continue;
            double r = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
            if (r > maxR) maxR = r;
        }
        return maxR;
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
    }




}
