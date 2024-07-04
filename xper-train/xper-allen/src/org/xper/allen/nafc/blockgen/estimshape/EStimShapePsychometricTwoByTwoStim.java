package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralStim;
import org.xper.allen.nafc.blockgen.procedural.Procedural;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Map;

public class EStimShapePsychometricTwoByTwoStim extends EStimShapeProceduralStim {

    private final String sampleSetCondition;
    //input parameters
    EStimExperimentTrialGenerator generator;
    AllenMStickSpec sampleSpec;
    Map<String, AllenMStickSpec> baseProceduralDistractorSpecs;

    Procedural<String> setType = new Procedural<>();

    public EStimShapePsychometricTwoByTwoStim(
            EStimExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            AllenMStickSpec sampleSpec,
            Map<String,AllenMStickSpec> baseProceduralDistractorSpecs,
            boolean isEStimEnabled,
            String sampleSetCondition) {
        super(generator, parameters, null, -1,
                isEStimEnabled);
        this.generator = (EStimExperimentTrialGenerator) generator;
        this.sampleSpec = sampleSpec;
        this.baseProceduralDistractorSpecs = baseProceduralDistractorSpecs;
        parameters.numChoices = baseProceduralDistractorSpecs.size() + 1 + parameters.numRandDistractors;
        this.sampleSetCondition = sampleSetCondition;
    }


    @Override
    public void generateMatchSticksAndSaveSpecs(){
        //sample
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        sample.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromShapeSpec(sampleSpec, new double[]{0,0,0});
        System.out.println("noise origin: " + sample.calculateNoiseOrigin(sample.getDrivingComponent()));
        noiseComponentIndex = sample.getDrivingComponent();
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        //match
        TwobyTwoMatchStick match = new TwobyTwoMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(sampleSpec, new double[]{0,0,0});
        match.centerShape();
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
        setType.setMatch(sampleSetCondition);

        //choices
        for (String setCondition : baseProceduralDistractorSpecs.keySet()) {
            AllenMStickSpec choiceSpec = baseProceduralDistractorSpecs.get(setCondition);
            TwobyTwoMatchStick choice = new TwobyTwoMatchStick();
            choice.setProperties(parameters.getSize(), parameters.textureType);
            choice.setStimColor(parameters.color);
            choice.genMatchStickFromShapeSpec(choiceSpec, new double[]{0,0,0});
            choice.centerShape();
            mSticks.addProceduralDistractor(choice);
            mStickSpecs.addProceduralDistractor(mStickToSpec(choice));
            setType.addProceduralDistractor(setCondition);
        }

        generateRandDistractors();
    }

    protected void drawPNGs() {
        AllenPNGMaker pngMaker = generator.getPngMaker();
        String generatorPngPath = generator.getGeneratorPngPath();

        drawSample(pngMaker, generatorPngPath);

        //Match
        List<String> matchLabels = Arrays.asList("match", setType.getMatch());
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), matchLabels, generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPngPathToExperiment(matchPath));
        System.out.println("Match Path: " + matchPath);

        drawProceduralDistractors(pngMaker, generatorPngPath);

        //Rand Distractor
        List<String> randDistractorLabels = Arrays.asList("rand");
        for (int i = 0; i < numRandDistractors; i++) {
            String randDistractorPath = pngMaker.createAndSavePNG(mSticks.randDistractors.get(i),stimObjIds.randDistractors.get(i), randDistractorLabels, generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPngPathToExperiment(randDistractorPath));
            System.out.println("Rand Distractor Path: " + randDistractorPath);
        }
    }

    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Procedural Distractors
        for (int i = 0; i < numProceduralDistractors; i++) {
            List<String> proceduralDistractorLabels = Arrays.asList("procedural", setType.proceduralDistractors.get(i));
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.proceduralDistractors.get(i),stimObjIds.proceduralDistractors.get(i), proceduralDistractorLabels, generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(proceduralDistractorPath));
            System.out.println("Procedural Distractor Path: " + proceduralDistractorPath);
        }
    }

    protected void drawSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Sample
        List<String> sampleLabels = Arrays.asList("sample");
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), sampleLabels, generatorPngPath);
        System.out.println("Sample Path: " + samplePath);
        experimentPngPaths.setSample(generator.convertPngPathToExperiment(samplePath));
    }
}