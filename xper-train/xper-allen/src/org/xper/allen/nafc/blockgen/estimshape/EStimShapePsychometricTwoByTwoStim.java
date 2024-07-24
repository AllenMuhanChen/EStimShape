package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralStim;
import org.xper.allen.nafc.blockgen.procedural.Procedural;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import java.util.*;

public class EStimShapePsychometricTwoByTwoStim extends EStimShapeProceduralStim {

    private final String sampleSetCondition;
    private final int MAX_MUTATION_ATTEMPTS = 100;  // Maximum number of mutation attempts

    //input parameters
    EStimExperimentTrialGenerator generator;
    AllenMStickSpec sampleSetSpec;
    Map<String, AllenMStickSpec> baseProceduralDistractorSpecs;
    Double baseMagnitude;
    double drivingMagnitude;


    Procedural<String> setType = new Procedural<>();
    Map<String, AllenMStickSpec> setSpecs = new LinkedHashMap<>();
    Map<String, AllenMStickSpec> morphedSetSpecs;

    public EStimShapePsychometricTwoByTwoStim(
            EStimExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            AllenMStickSpec sampleSpec,
            Map<String,AllenMStickSpec> baseProceduralDistractorSpecs,
            boolean isEStimEnabled,
            String sampleSetCondition, double baseMagnitude, double drivingMagnitude) {
        super(generator, parameters, null, -1, isEStimEnabled);
        this.generator = (EStimExperimentTrialGenerator) generator;
        this.sampleSetSpec = sampleSpec;
        this.baseProceduralDistractorSpecs = baseProceduralDistractorSpecs;
        parameters.numChoices = baseProceduralDistractorSpecs.size() + 1 + parameters.numRandDistractors;
        this.sampleSetCondition = sampleSetCondition;
        this.baseMagnitude = baseMagnitude;
        this.drivingMagnitude = drivingMagnitude;

        setSpecs.put(sampleSetCondition, sampleSetSpec);
        for (String setCondition : baseProceduralDistractorSpecs.keySet()) {
            setSpecs.put(setCondition, baseProceduralDistractorSpecs.get(setCondition));
        }
    }


    @Override
    public void generateMatchSticksAndSaveSpecs(){
        generateMorphedSet();
        replaceSetWithMorphedSet();

        generateSample();
        generateMatch();
        generateProceduralDistractors();
        generateRandDistractors();
    }

    private void replaceSetWithMorphedSet() {
        //Replacing the specs with the morphed specs
        sampleSetSpec = morphedSetSpecs.get(sampleSetCondition);
        for (String setCondition : baseProceduralDistractorSpecs.keySet()) {
            baseProceduralDistractorSpecs.put(setCondition, morphedSetSpecs.get(setCondition));
        }
    }

    private void generateMorphedSet() {
        while (true) {

            try {
                morphedSetSpecs = new LinkedHashMap<>();
                //I* - B1* D1*
                EStimShapeTwoByTwoMatchStick morphedStickI = setMorphI();
                AllenMStickSpec morphedStickISpec = mStickToSpec(morphedStickI);
                this.morphedSetSpecs.put("I", morphedStickISpec);

                //II* - B2* D1*
                EStimShapeTwoByTwoMatchStick morphedStickII = setMorphII(morphedStickI);
                AllenMStickSpec morphedStickIISpec = mStickToSpec(morphedStickII);
                this.morphedSetSpecs.put("II", morphedStickIISpec);

                //III* - B1* D2*
                EStimShapeTwoByTwoMatchStick morphedStickIII = setMorphIII(morphedStickI);
                AllenMStickSpec morphedStickIIISpec = mStickToSpec(morphedStickIII);
                this.morphedSetSpecs.put("III", morphedStickIIISpec);

                //IV*
                EStimShapeTwoByTwoMatchStick morphedStickIV = setMorphIV(morphedStickII, morphedStickIII);
                AllenMStickSpec morphedStickIVSpec = mStickToSpec(morphedStickIV);
                this.morphedSetSpecs.put("IV", morphedStickIVSpec);

                break;
            } catch (MorphedMatchStick.MorphException e) {
                System.out.println("Morphed set generation failed: " + e.getMessage());
            }
        }
    }

    private static List<Integer> identifyBaseComps(EStimShapeTwoByTwoMatchStick B2Stick) {
        List<Integer> baseCompIds = new ArrayList<>();
        for (int compId = 1; compId <= B2Stick.getnComponent(); compId++) {
            if (compId != B2Stick.getDrivingComponent()) {
                baseCompIds.add(compId);
            }
        }
        return baseCompIds;
    }

    private EStimShapeTwoByTwoMatchStick setMorphI() {
        EStimShapeTwoByTwoMatchStick stickI = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        stickI.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);

        stickI.genMatchStickFromShapeSpec(setSpecs.get("I"), new double[]{0,0,0});

        //Mutate all compIds -> gives us B1* and D1*
        LinkedList<Integer> baseCompIds = new LinkedList<>();
        for (int compId = 1; compId <= stickI.getnComponent(); compId++) {
            if (compId != stickI.getDrivingComponent()) {
                baseCompIds.add(compId);
            }
        }

        boolean setMutationSuccess = attemptSetMutation(stickI, baseCompIds, baseMagnitude);
        setMutationSuccess = attemptSetMutation(stickI, Collections.singletonList(stickI.getDrivingComponent()), drivingMagnitude);

        return stickI;
    }

    private EStimShapeTwoByTwoMatchStick setMorphII(EStimShapeTwoByTwoMatchStick morphedStickI) {
        EStimShapeTwoByTwoMatchStick B2Stick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );

        B2Stick.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);
        B2Stick.genMatchStickFromShapeSpec(setSpecs.get("II"), new double[]{0, 0, 0});

        List<Integer> baseCompIds = identifyBaseComps(B2Stick);

        boolean setMutationSuccess = attemptSetMutation(B2Stick, baseCompIds, baseMagnitude);

        EStimShapeTwoByTwoMatchStick morphedStickII = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        morphedStickII.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);
        morphedStickII.genComponentSwappedMatchStick(
                B2Stick, B2Stick.getDrivingComponent(),
                morphedStickI, morphedStickI.getDrivingComponent(),
                100, true);
        return morphedStickII;
    }

    private EStimShapeTwoByTwoMatchStick setMorphIII(EStimShapeTwoByTwoMatchStick morphedStickI) {
        EStimShapeTwoByTwoMatchStick D2Stick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        D2Stick.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);
        D2Stick.genMatchStickFromShapeSpec(setSpecs.get("III"), new double[]{0,0,0});
        attemptSetMutation(D2Stick, Collections.singletonList(D2Stick.getDrivingComponent()), drivingMagnitude);

        EStimShapeTwoByTwoMatchStick morphedStickIII = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );

        morphedStickIII.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);

        morphedStickIII.genComponentSwappedMatchStick(
                morphedStickI, morphedStickI.getDrivingComponent(),
                D2Stick, D2Stick.getDrivingComponent(),
                100, true);
        return morphedStickIII;
    }

    private EStimShapeTwoByTwoMatchStick setMorphIV(EStimShapeTwoByTwoMatchStick morphedStickII, EStimShapeTwoByTwoMatchStick morphedStickIII) {
        EStimShapeTwoByTwoMatchStick morphedStickIV = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );

        morphedStickIV.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);

        morphedStickIV.genComponentSwappedMatchStick(
                morphedStickII, morphedStickII.getDrivingComponent(),
                morphedStickIII, morphedStickIII.getDrivingComponent(),
                100, true);
        return morphedStickIV;
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

            choice.centerShape();
            mSticks.addProceduralDistractor(choice);
            mStickSpecs.addProceduralDistractor(mStickToSpec(choice));
            setType.addProceduralDistractor(setCondition);
        }
    }

    /**
     * A set mutation is a morph of the entire set of components. So, if our four components are:
     * B1 B2 D1 and D2 (B: base, D: driving) and our four two by two stimuli were:
     * I - B1 D1
     * II - B2 D1
     * III - B1 D2
     * IV - B2 D2
     *
     * then a set mutation would be a morph of all four components to:
     * B1* B2* D1* and D2* and then make the set of two by two stimuli based on this mutated set:
     *
     * I* - B1* D1*
     * II* - B2* D1*
     * III* - B1* D2*
     * IV* - B2* D2*
     * @param matchStick
     * @param compsToMorph
     * @param magnitude
     * @return
     */
    private boolean attemptSetMutation(EStimShapeTwoByTwoMatchStick matchStick, List<Integer> compsToMorph, Double magnitude) {
        for (int attempt = 0; attempt < MAX_MUTATION_ATTEMPTS; attempt++) {
            try {
                if (magnitude > 1.0 && magnitude <= 2.0){
                    matchStick.doMediumMutation(
                            matchStick,
                            compsToMorph, magnitude -1, 0.5,
                            true,
                            false,
                            true);
                } else if (magnitude <= 1.0 && magnitude >= 0.0){
                    matchStick.doSmallMutation(
                            matchStick, compsToMorph, magnitude,
                            true,
                            false,
                            true);
                } else{
                    throw new IllegalArgumentException("Magnitude must be between 0 and 2");
                }

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