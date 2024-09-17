package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.util.LinkedList;
import java.util.List;

public class EStimShapeDeltaStim extends EStimShapeProceduralStim{

    private final EStimShapeProceduralStim baseStim;
    private final boolean isDeltaMorph;
    private final boolean isDeltaNoise;

    public EStimShapeDeltaStim(EStimShapeProceduralStim baseStim, boolean isDeltaMorph, boolean isDeltaNoise){
        super(
                (EStimShapeExperimentTrialGenerator) baseStim.generator,
                baseStim.getParameters(),
                baseStim.baseMatchStick,
                -1, true);
        this.baseStim = baseStim;
        this.isDeltaMorph = isDeltaMorph;
        this.isDeltaNoise = isDeltaNoise;
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            System.out.println("Trying to generate EStimShapeDeltaStim");
            try {
                EStimShapeProceduralMatchStick sample = generateSample();

                assignDrivingAndDeltaIndices(sample);

                generateMatch(sample);

                generateProceduralDistractors(sample);

                generateRandDistractors();

                break;
            } catch (ProceduralMatchStick.MorphRepetitionException mre){
                System.out.println(mre.getMessage());
            }
        }
    }

    @Override
    protected EStimShapeProceduralMatchStick generateSample() {
        //Generate Sample
        EStimShapeProceduralMatchStick sample = (EStimShapeProceduralMatchStick) baseStim.mSticks.getSample();

        System.out.println("New Noise Component Index: " + noiseComponentIndex);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;
    }


    protected void assignDrivingAndDeltaIndices(ProceduralMatchStick sample){
        int drivingIndex = sample.getDrivingComponent();
        int deltaIndex = sample.assignDeltaCompId();

        morphComponentIndex = drivingIndex;
        noiseComponentIndex = drivingIndex;
        if (isDeltaMorph){
            System.out.println("Is Delta Morph");
            morphComponentIndex = deltaIndex;
        }
        if (isDeltaNoise) {
            System.out.println("Is Delta Noise");
            noiseComponentIndex = deltaIndex;
        }

    }

    @Override
    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Procedural Distractors
        List<String> labels = new LinkedList<>();
        labels.add("procedural");
        if (isDeltaMorph){
            labels.add("deltaMorph");
        }
        for (int i = 0; i < numProceduralDistractors; i++) {
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.getProceduralDistractors().get(i), stimObjIds.getProceduralDistractors().get(i), labels, generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(proceduralDistractorPath));
            System.out.println("Procedural Distractor Path: " + proceduralDistractorPath);
        }
    }

    @Override
    protected void generateNoiseMap() {
        List<String> noiseMapLabels = new LinkedList<>();
        noiseMapLabels.add("sample");
        if (isDeltaNoise){
            noiseMapLabels.add("deltaNoise");
            System.out.println("Delta: Noise Component Index: " + noiseComponentIndex);
        } else {
            System.out.println("Not Delta: Noise Component Index: " + noiseComponentIndex);
        }
        String generatorNoiseMapPath = generator.getPngMaker().createAndSaveNoiseMap(mSticks.getSample(), stimObjIds.getSample(), noiseMapLabels, generator.getGeneratorNoiseMapPath(), parameters.noiseChance, noiseComponentIndex);
        experimentNoiseMapPath = generator.convertGeneratorNoiseMapToExperiment(generatorNoiseMapPath);
    }

}