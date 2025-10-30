package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.nafc.blockgen.MStickGenerationUtils;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralStim;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import java.util.*;

public class EStimShapePsychometricTwoByTwoStim extends EStimShapeProceduralStim {


    private final int MAX_MUTATION_ATTEMPTS = 100;  // Maximum number of mutation attempts
    private final double percentRequiredOutsideNoise = 0.5;

    //input parameters
    EStimShapeExperimentTrialGenerator generator;
    AllenMStickSpec sampleSetSpec;
    Map<String, AllenMStickSpec> baseProceduralDistractorSpecs;
    Double baseMagnitude;
    double drivingMagnitude;
    private final boolean isDeltaNoise;
    private final String sampleSetCondition;


    Map<String, AllenMStickSpec> setSpecs = new LinkedHashMap<>();
    Map<String, AllenMStickSpec> morphedSetSpecs;
    private final List<Integer> compIdsToNoise = new ArrayList<>();
    private NAFCNoiseMapper noiseMapper;

    public EStimShapePsychometricTwoByTwoStim(
            EStimShapeExperimentTrialGenerator generator, EStimShapePsychometricTwoByTwoParameters parameters) {

        super(generator, parameters, null, -1, parameters.isEStimEnabled(), 0L, 0);

        //local variables extracted from parameters
        this.generator = generator;
        this.sampleSetSpec = parameters.getSampleSpec();
        this.baseProceduralDistractorSpecs = parameters.getBaseProceduralDistractorSpecs();
        parameters.numChoices = parameters.getBaseProceduralDistractorSpecs().size() + 1 + parameters.numRandDistractors;
        this.sampleSetCondition = parameters.getSampleSetCondition();
        this.baseMagnitude = parameters.getBaseMagnitude();
        this.drivingMagnitude = parameters.getDrivingMagnitude();
        this.isDeltaNoise = parameters.isDeltaNoise();
        this.noiseMapper = generator.getNoiseMapper();
        setSpecs.put(parameters.getSampleSetCondition(), sampleSetSpec);
        for (String setCondition : parameters.getBaseProceduralDistractorSpecs().keySet()) {
            setSpecs.put(setCondition, parameters.getBaseProceduralDistractorSpecs().get(setCondition));
        }
    }


    @Override
    public void generateMatchSticksAndSaveSpecs(){
        while (true) {
            try {
                generateMorphedSet();
                replaceSetWithMorphedSet();

                generateSample();
                generateMatch();
                generateProceduralDistractors();
                generateRandDistractors();
                return;
            } catch (Exception e) {
                System.out.println("Morphed set generation failed: " + e.getMessage());
            }
        }
    }

    /**
     * Has new noise map procedure that accepts a list of comps to try to put in the noise.
     *
     */
    @Override
    protected void generateNoiseMap() {
        String generatorNoiseMapPath = generator.getPngMaker().createAndSaveNoiseMap(
                mSticks.getSample(),
                stimObjIds.getSample(),
                labels.getSample(),
                generator.getGeneratorNoiseMapPath(),
                parameters.noiseChance, compIdsToNoise);
        experimentNoiseMapPath = generator.convertGeneratorNoiseMapToExperiment(generatorNoiseMapPath);
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

        return MStickGenerationUtils.attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                EStimShapeTwoByTwoMatchStick stickI = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                stickI.setProperties(
                        RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                        parameters.textureType, 1.0);

                stickI.genMatchStickFromShapeSpec(setSpecs.get("I"), new double[]{0, 0, 0});
                System.out.println("Pre Set Mute driving component: " + stickI.getDrivingComponent());
                System.out.println("Pre Set Mute center of mass: " + stickI.getMassCenterForComponent(stickI.getDrivingComponent()));
                System.out.println("Pre Set Mute real center: " + stickI.getComp()[stickI.getDrivingComponent()].getMassCenter());
                //Mutate all compIds -> gives us B1* and D1*
                LinkedList<Integer> baseCompIds = new LinkedList<>();
                for (int compId = 1; compId <= stickI.getnComponent(); compId++) {
                    if (compId != stickI.getDrivingComponent()) {
                        baseCompIds.add(compId);
                    }
                }

                attemptSetMutation(stickI, baseCompIds, baseMagnitude);

                List<Integer> compsToNoise = identifyCompsToNoise(stickI, isDeltaNoise);
                noiseMapper.checkInNoise(stickI, compsToNoise, percentRequiredOutsideNoise);
                return stickI;
            }
        }, 15);
    }

    private EStimShapeTwoByTwoMatchStick setMorphII(EStimShapeTwoByTwoMatchStick morphedStickI) {
        return MStickGenerationUtils.attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                EStimShapeTwoByTwoMatchStick B2Stick = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);

                B2Stick.setProperties(
                        RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                        parameters.textureType, 1.0);
                B2Stick.genMatchStickFromShapeSpec(setSpecs.get("II"), new double[]{0, 0, 0});

                List<Integer> baseCompIds = identifyBaseComps(B2Stick);

                attemptSetMutation(B2Stick, baseCompIds, baseMagnitude);

                EStimShapeTwoByTwoMatchStick morphedStickII = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                morphedStickII.setProperties(
                        RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                        parameters.textureType, 1.0);
                morphedStickII.genComponentSwappedMatchStick(
                        B2Stick, B2Stick.getDrivingComponent(),
                        morphedStickI, morphedStickI.getDrivingComponent(),
                        5, true);

                List<Integer> compsToNoise = identifyCompsToNoise(morphedStickII, isDeltaNoise);
                noiseMapper.checkInNoise(morphedStickII, compsToNoise, percentRequiredOutsideNoise);
                return morphedStickII;
            }
        }, 15);
    }

    private EStimShapeTwoByTwoMatchStick setMorphIII(EStimShapeTwoByTwoMatchStick morphedStickI) {
        return MStickGenerationUtils.attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                EStimShapeTwoByTwoMatchStick D2Stick = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                D2Stick.setProperties(
                        RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                        parameters.textureType, 1.0);
                D2Stick.genMatchStickFromShapeSpec(setSpecs.get("III"), new double[]{0,0,0});
                attemptSetMutation(D2Stick, Collections.singletonList(D2Stick.getDrivingComponent()), drivingMagnitude);

                EStimShapeTwoByTwoMatchStick morphedStickIII = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);

                morphedStickIII.setProperties(
                        RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                        parameters.textureType, 1.0);

                morphedStickIII.genComponentSwappedMatchStick(
                        morphedStickI, morphedStickI.getDrivingComponent(),
                        D2Stick, D2Stick.getDrivingComponent(),
                        5, true);

                List<Integer> compsToNoise = identifyCompsToNoise(morphedStickIII, isDeltaNoise);
                noiseMapper.checkInNoise(morphedStickIII, compsToNoise, percentRequiredOutsideNoise);
                return morphedStickIII;
            }
        }, 15);
    }

    private EStimShapeTwoByTwoMatchStick setMorphIV(EStimShapeTwoByTwoMatchStick morphedStickII, EStimShapeTwoByTwoMatchStick morphedStickIII) {
        return MStickGenerationUtils.attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                EStimShapeTwoByTwoMatchStick morphedStickIV = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);

                morphedStickIV.setProperties(
                        RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                        parameters.textureType, 1.0);

                morphedStickIV.genComponentSwappedMatchStick(
                        morphedStickII, morphedStickII.getDrivingComponent(),
                        morphedStickIII, morphedStickIII.getDrivingComponent(),
                        5, true);


                List<Integer> compsToNoise = identifyCompsToNoise(morphedStickIV, isDeltaNoise);
                noiseMapper.checkInNoise(morphedStickIV, compsToNoise, percentRequiredOutsideNoise);
                return morphedStickIV;
            }
        }, 15);
    }

    public ProceduralMatchStick generateSample() {
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF(),
                noiseMapper);
        sample.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees()),
                parameters.textureType, 1.0);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromShapeSpec(sampleSetSpec, new double[]{0,0,0});
        List<Integer> compsToNoise = identifyCompsToNoise(sample, isDeltaNoise);
        noiseMapper.checkInNoise(sample, compsToNoise, 0.5);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        labels.getSample().add(isDeltaNoise ? "isDeltaNoise" : "notDeltaNoise");
        return sample;
    }

    protected List<Integer> identifyCompsToNoise(ProceduralMatchStick sample, boolean isDeltaNoise) {
        if (!isDeltaNoise) {
            compIdsToNoise.add(sample.getDrivingComponent());
        } else {
            for (int compId = 1; compId <= sample.getnComponent(); compId++) {
                if (compId != sample.getDrivingComponent()) {
                    compIdsToNoise.add(compId);
                }
            }
        }
        return compIdsToNoise;
    }

    private void generateMatch() {
        TwoByTwoMatchStick match = new TwoByTwoMatchStick(noiseMapper);
        match.setProperties(parameters.getSize(), parameters.textureType, 1.0);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.centerShape();
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
        labels.getMatch().add(sampleSetCondition);
    }

    private void generateProceduralDistractors() {
        int i = 0;
        for (String setCondition : baseProceduralDistractorSpecs.keySet()) {
            AllenMStickSpec choiceSpec = baseProceduralDistractorSpecs.get(setCondition);
            TwoByTwoMatchStick choice = new TwoByTwoMatchStick(noiseMapper);
            choice.setProperties(parameters.getSize(), parameters.textureType, 1.0);
            choice.setStimColor(parameters.color);
            choice.genMatchStickFromShapeSpec(choiceSpec, new double[]{0,0,0});

            choice.centerShape();
            mSticks.addProceduralDistractor(choice);
            mStickSpecs.addProceduralDistractor(mStickToSpec(choice));
            labels.getProceduralDistractors().get(i).add(setCondition);
            i++;
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
     * @param stickToMorph
     * @param compsToMorph
     * @param magnitude
     * @return
     */
    private void attemptSetMutation(EStimShapeTwoByTwoMatchStick stickToMorph, List<Integer> compsToMorph, Double magnitude) {
        List<Integer> compsToNoise = identifyCompsToNoise(stickToMorph, isDeltaNoise);
        EStimShapeTwoByTwoMatchStick backup = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF(),
                noiseMapper);
        backup.copyFrom(stickToMorph);
        for (int attempt = 0; attempt < MAX_MUTATION_ATTEMPTS; attempt++) {
            try {
                if (magnitude > 1.0 && magnitude <= 2.0){
                    stickToMorph.doMediumMutation(
                            backup,
                            compsToMorph, magnitude-1, percentRequiredOutsideNoise,
                            true,
                            false,
                            compsToNoise);
                } else if (magnitude <= 1.0 && magnitude >= 0.0){
                    stickToMorph.doSmallMutation(
                            backup, compsToMorph, magnitude,
                            true,
                            false,
                            true, compsToNoise);
                } else{
                    throw new IllegalArgumentException("Magnitude must be between 0 and 2");
                }


                return;  // Mutation successful
            } catch (Exception e) {
                e.printStackTrace();
                stickToMorph.copyFrom(backup);
                System.out.println("Mutation attempt " + (attempt + 1) + " failed: " + e.getMessage());

            }

        }
        throw new ProceduralMatchStick.MorphRepetitionException("Could not do set mutation after " + MAX_MUTATION_ATTEMPTS + " attempts");  // All mutation attempts failed
    }

    protected void drawPNGs() {
        AllenPNGMaker pngMaker = generator.getPngMaker();
        String generatorPngPath = generator.getGeneratorPngPath();

        drawSample(pngMaker, generatorPngPath);

        //Match
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), labels.getMatch(), generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPngPathToExperiment(matchPath));
        System.out.println("Match Path: " + matchPath);

        drawProceduralDistractors(pngMaker, generatorPngPath);

        //Rand Distractor
        List<String> randDistractorLabels = Arrays.asList("rand");
        for (int i = 0; i < numRandDistractors; i++) {
            String randDistractorPath = pngMaker.createAndSavePNG(mSticks.getRandDistractors().get(i), stimObjIds.getRandDistractors().get(i), labels.getRandDistractors().get(i), generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPngPathToExperiment(randDistractorPath));
            System.out.println("Rand Distractor Path: " + randDistractorPath);
        }
    }

    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Procedural Distractors
        for (int i = 0; i < numProceduralDistractors; i++) {
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.getProceduralDistractors().get(i), stimObjIds.getProceduralDistractors().get(i), labels.getProceduralDistractors().get(i), generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(proceduralDistractorPath));
            System.out.println("Procedural Distractor Path: " + proceduralDistractorPath);
        }
    }

    protected void drawSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Sample
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), labels.getSample(), generatorPngPath);
        System.out.println("Sample Path: " + samplePath);
        experimentPngPaths.setSample(generator.convertPngPathToExperiment(samplePath));
    }

    public String getSampleSetCondition() {
        return sampleSetCondition;
    }
}