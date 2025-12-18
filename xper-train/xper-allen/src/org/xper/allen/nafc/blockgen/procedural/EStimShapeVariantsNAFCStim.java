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
import org.xper.drawing.RGBColor;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.List;

public class EStimShapeVariantsNAFCStim extends EStimShapeProceduralStim{

    protected List<Integer> noiseComponentIndcs;
    protected String gaSpecPath;
    private String texture;
    private Float sampleSize;
    private NAFCNoiseMapper noiseMapper;



    public EStimShapeVariantsNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, List<Integer> morphComponentIndcs, boolean isEStimEnabled, long baseMStickStimSpecId, int compId) {
        super(generator, parameters, baseMatchStick, morphComponentIndcs, isEStimEnabled, baseMStickStimSpecId, compId);
    }

    public EStimShapeVariantsNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, Long variantId, boolean isEStimEnabled){
        super(generator, parameters, null, new ArrayList<>(), isEStimEnabled, variantId, -1);
        gaSpecPath = generator.getGaSpecPath();


        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(generator.getGaDataSource());
        SizePropertyManager sizePropertyManager = new SizePropertyManager(gaJDBCTemplate);
        TexturePropertyManager texturePropertyManager = new TexturePropertyManager(gaJDBCTemplate);
        ColorPropertyManager colorPropertyManager = new ColorPropertyManager(gaJDBCTemplate);
        CompsToPreserveManager compsToPreserveManager = new CompsToPreserveManager(gaJDBCTemplate);

        sampleSize = sizePropertyManager.readProperty(variantId);
        texture = texturePropertyManager.readProperty(variantId);
        color = colorPropertyManager.readProperty(variantId);

        maxChoiceSize = generator.getMaxChoiceDimensionDegrees() * 0.9;
        choiceSize = sampleSize;

        double choiceLim = calculateMinDistanceChoicesCanBeWithoutOverlap(maxChoiceSize, parameters.numChoices);

        parameters.setChoiceDistanceLims(new Lims(choiceLim, choiceLim));
        parameters.setEyeWinRadius(choiceSize*4/2); // 4 back to back limbs, and divide by two for radius corr

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

        noiseMapper.checkInNoise(sample, noiseComponentIndcs, 0.5);
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
        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick(noiseMapper);
            correctNoiseRadius(proceduralDistractor);
            proceduralDistractor.setProperties(choiceSize, texture, is2D(), 1.0);
            proceduralDistractor.setStimColor(color);
            proceduralDistractor.genNewComponentsMatchStick(sample, morphComponentIndcs, parameters.morphMagnitude, 0.5, true, proceduralDistractor.maxAttempts, maxChoiceSize);
            mSticks.addProceduralDistractor(proceduralDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(proceduralDistractor));
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
