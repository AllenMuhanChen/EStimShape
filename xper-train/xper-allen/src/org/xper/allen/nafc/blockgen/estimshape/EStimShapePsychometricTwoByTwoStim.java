package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStick;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralStim;
import org.xper.allen.nafc.blockgen.procedural.Procedural;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

public class EStimShapePsychometricTwoByTwoStim extends EStimShapeProceduralStim {

    private final String sampleSetCondition;
    private final int MAX_MUTATION_ATTEMPTS = 100;  // Maximum number of mutation attempts

    //input parameters
    EStimExperimentTrialGenerator generator;
    AllenMStickSpec sampleSetSpec;
    Map<String, AllenMStickSpec> baseProceduralDistractorSpecs;

    Procedural<String> setType = new Procedural<>();

    public EStimShapePsychometricTwoByTwoStim(
            EStimExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            AllenMStickSpec sampleSpec,
            Map<String,AllenMStickSpec> baseProceduralDistractorSpecs,
            boolean isEStimEnabled,
            String sampleSetCondition) {
        super(generator, parameters, null, -1, isEStimEnabled);
        this.generator = (EStimExperimentTrialGenerator) generator;
        this.sampleSetSpec = sampleSpec;
        this.baseProceduralDistractorSpecs = baseProceduralDistractorSpecs;
        parameters.numChoices = baseProceduralDistractorSpecs.size() + 1 + parameters.numRandDistractors;
        this.sampleSetCondition = sampleSetCondition;
    }

    @Override
    public void generateMatchSticksAndSaveSpecs(){
        generateSample();
        generateMatch();
        generateProceduralDistractors();
        generateRandDistractors();
    }

    public ProceduralMatchStick generateSample() {
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        sample.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromShapeSpec(sampleSetSpec, new double[]{0,0,0});

        boolean mutationSuccess = attemptSetMutation(sample);
        if (!mutationSuccess) {
            System.out.println("Warning: Failed to generate a valid mutation for sample after " + MAX_MUTATION_ATTEMPTS + " attempts.");
            throw new RuntimeException();
        }

        System.out.println("noise origin: " + sample.calculateNoiseOrigin(sample.getDrivingComponent()));
        noiseComponentIndex = sample.getDrivingComponent();
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;
    }

    private void generateMatch() {
        TwoByTwoMatchStick match = new TwoByTwoMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.centerShape();
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
        setType.setMatch(sampleSetCondition);
    }

    private void generateProceduralDistractors() {
        for (String setCondition : baseProceduralDistractorSpecs.keySet()) {
            AllenMStickSpec choiceSpec = baseProceduralDistractorSpecs.get(setCondition);
            TwoByTwoMatchStick choice = new TwoByTwoMatchStick();
            choice.setProperties(parameters.getSize(), parameters.textureType);
            choice.setStimColor(parameters.color);
            choice.genMatchStickFromShapeSpec(choiceSpec, new double[]{0,0,0});

            boolean mutationSuccess = attemptSetMutation(choice);
            if (!mutationSuccess) {
                System.out.println("Warning: Failed to generate a valid mutation for procedural distractor after " + MAX_MUTATION_ATTEMPTS + " attempts.");
            }

            choice.centerShape();
            mSticks.addProceduralDistractor(choice);
            mStickSpecs.addProceduralDistractor(mStickToSpec(choice));
            setType.addProceduralDistractor(setCondition);
        }
    }

    private boolean attemptSetMutation(TwoByTwoMatchStick matchStick) {
        for (int attempt = 0; attempt < MAX_MUTATION_ATTEMPTS; attempt++) {
            try {
                matchStick.doSmallMutation(
                        true,
                        false);
                return true;  // Mutation successful
            } catch (Exception e) {
                System.out.println("Mutation attempt " + (attempt + 1) + " failed: " + e.getMessage());

            }
        }
        return false;  // All mutation attempts failed
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

    public String getSampleSetCondition() {
        return sampleSetCondition;
    }
}