package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import static org.xper.allen.pga.RFUtils.checkCompCanFitInRF;

public class EStimShapeProceduralBehavioralStim extends EStimShapeProceduralStim{

    private final AllenPNGMaker samplePngMaker;
    private ReceptiveField rf;
    private AllenPNGMaker choicePNGMaker;

    public EStimShapeProceduralBehavioralStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, ReceptiveField rf) {
        super(
                generator,
                parameters,
                null,
                -1,
                false);
        this.rf = rf;
        samplePngMaker = generator.getSamplePngMaker();
        choicePNGMaker = generator.getPngMaker();
    }

    @Override
    public void preWrite() {
        assignStimObjIds();
        assignLabels();
        generateMatchSticksAndSaveSpecs();
        drawPNGs();
        assignCoords();
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            System.out.println("Trying to generate EStimShapeProceduralBehavioralStim");
            try {
                baseMatchStick = genRandBaseMStick();
                baseMatchStick.setMaxAttempts(15);
                generateNonBaseMatchSticksAndSaveSpecs();
                break;
            } catch (ProceduralMatchStick.MorphRepetitionException me) {
                System.err.println("MorphRepetition FAILED: " + me.getMessage());
            } catch(ProceduralMatchStick.MorphException me) {
                System.err.println("Morph EXCEPTION: " + me.getMessage());
            } catch (Exception e) {
                System.err.println("EXCEPTION: " + e.getMessage());
            }
            System.out.println("Starting over from a new base match stick");
        }

    }

    protected void generateNonBaseMatchSticksAndSaveSpecs() {
        int nAttempts = 0;
        int maxAttempts = 2;
        while(nAttempts < maxAttempts) {
            nAttempts++;
            try {
                EStimShapeProceduralMatchStick sample = generateSample();

                morphComponentIndex = sample.getDrivingComponent();
                noiseComponentIndex = sample.getDrivingComponent();

                generateMatch(sample);

                generateProceduralDistractors(sample);

                generateRandDistractors();

                break;
            } catch (ProceduralMatchStick.MorphRepetitionException e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
            }
        }
        if (nAttempts == maxAttempts) {
            throw new ProceduralMatchStick.MorphRepetitionException("MorphRepetition FAILED: " + nAttempts + " attempts");
        }
    }

    @Override
    protected EStimShapeProceduralMatchStick generateSample() {
        //Check Random Base Match Stick
        int randLeaf = baseMatchStick.chooseRandLeaf();
        checkCompCanFitInRF(baseMatchStick, rf, randLeaf);


        //Generate Sample
        EStimShapeProceduralMatchStick sample = new EStimShapeProceduralMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                rf, generator.getPngMaker().getNoiseMapper()
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimShapeExperimentTrialGenerator) generator).getRfSource().getRFRadiusDegrees()), parameters.textureType, 1.0);
        sample.setStimColor(parameters.color);
        baseMatchStick.setMaxAttempts(3);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, randLeaf, 0, true, sample.maxAttempts, generator.getPngMaker().getNoiseMapper());

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
        baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimShapeExperimentTrialGenerator) generator).getRfSource().getRFRadiusDegrees()), parameters.textureType, 1.0);
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();

        return baseMStick;
    }

    /**
     * Modified to open separate drawing windows for sample and choices. This is because sample and choice
     * need to be drawn at different sizes to accommodate fitting sample in RF.
     */
    protected void drawPNGs() {
        String generatorPngPath = generator.getGeneratorPngPath();

        samplePngMaker.createDrawerWindow();
        drawSample(samplePngMaker, generatorPngPath);
        generateNoiseMap();
        generateSampleCompMap();
        samplePngMaker.close();

        //Match
        choicePNGMaker.createDrawerWindow();
        String matchPath = choicePNGMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), labels.getMatch(), generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPngPathToExperiment(matchPath));
        System.out.println("Match Path: " + matchPath);

        drawProceduralDistractors(choicePNGMaker, generatorPngPath);

        //Rand Distractor
        for (int i = 0; i < numRandDistractors; i++) {
            String randDistractorPath = choicePNGMaker.createAndSavePNG(mSticks.getRandDistractors().get(i), stimObjIds.getRandDistractors().get(i), labels.getRandDistractors().get(i), generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPngPathToExperiment(randDistractorPath));
            System.out.println("Rand Distractor Path: " + randDistractorPath);
        }
        choicePNGMaker.close();
    }

    protected void generateNoiseMap() {
        String generatorNoiseMapPath = samplePngMaker.createAndSaveNoiseMap(
                mSticks.getSample(),
                stimObjIds.getSample(),
                labels.getSample(),
                generator.getGeneratorNoiseMapPath(),
                parameters.noiseChance, noiseComponentIndex);
        experimentNoiseMapPath = generator.convertGeneratorNoiseMapToExperiment(generatorNoiseMapPath);
    }

    protected void generateSampleCompMap() {
        samplePngMaker.createAndSaveCompMap(mSticks.getSample(), stimObjIds.getSample(), labels.getSample(), generator.getGeneratorPngPath());
    }



}