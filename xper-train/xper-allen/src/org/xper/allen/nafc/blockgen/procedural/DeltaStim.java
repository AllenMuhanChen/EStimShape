package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.util.LinkedList;
import java.util.List;

public class DeltaStim extends ProceduralStim {
    private final ProceduralStim baseStim;
    private final boolean isDeltaMorph;
    private final boolean isDeltaNoise;

    public DeltaStim(ProceduralStim baseStim, boolean isDeltaMorph, boolean isDeltaNoise){
        super(
                baseStim.generator,
                baseStim.getParameters(),
                baseStim.baseMatchStick,
                -1, -1);
        this.baseStim = baseStim;
        this.isDeltaMorph = isDeltaMorph;
        this.isDeltaNoise = isDeltaNoise;
    }


    @Override
    public void preWrite() {
        assignDrivingAndDeltaIndices();
        super.preWrite();
    }

    protected void assignDrivingAndDeltaIndices(){
        int drivingIndex = getDrivingIndex();
        int deltaIndex = chooseDeltaIndex();

        morphComponentIndex = drivingIndex;
        noiseComponentIndex = drivingIndex;
        if (isDeltaMorph){
            morphComponentIndex = deltaIndex;
        }
        if (isDeltaNoise) {
            noiseComponentIndex = deltaIndex;
        }

    }


    private Integer getDrivingIndex() {
        return baseStim.mSticks.getSample().getSpecialEndComp().get(0);
    }

    private int chooseDeltaIndex(){
        int drivingComponent = getDrivingIndex();
        List<Integer> allComps = baseStim.mSticks.getSample().getCompIds();
        baseStim.mSticks.getSample().decideLeafBranch();
        boolean[] leafBranch = baseStim.mSticks.getSample().getLeafBranch();

        List<Integer> elegibleComps = new LinkedList<>();
        for (int i=1; i<allComps.size(); i++){
            if (allComps.get(i) != drivingComponent){
                if (leafBranch[i]) {
                    elegibleComps.add(allComps.get(i));
                }
            }
        }

        //choose a random one
        int randIndex = (int) (Math.random() * elegibleComps.size());
        Integer deltaComp = elegibleComps.get(randIndex);
        System.out.println("Delta Comp: " + deltaComp);
        return deltaComp;
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        //Generate Sample
        ProceduralMatchStick sample = baseStim.mSticks.getSample();
        noiseComponentIndex = baseStim.noiseComponentIndex;
        System.out.println("New Noise Component Index: " + noiseComponentIndex);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
        return sample;
    }

    @Override
    protected void drawSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Sample
        List<String> labels = new LinkedList<>();
        labels.add("sample");
        if (isDeltaNoise){
            labels.add("deltaNoise");
        }
        List<String> sampleLabels = labels;
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), sampleLabels, generatorPngPath);
        System.out.println("Sample Path: " + samplePath);
        experimentPngPaths.setSample(generator.convertPngPathToExperiment(samplePath));
    }

    @Override
    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Procedural Distractors
        List<String> labels = new LinkedList<>();
        labels.add("procedural");
        if (isDeltaMorph){
            labels.add("deltaMorph");
        }
        List<String> proceduralDistractorLabels = labels;
        for (int i = 0; i < numProceduralDistractors; i++) {
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.proceduralDistractors.get(i),stimObjIds.proceduralDistractors.get(i), proceduralDistractorLabels, generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(proceduralDistractorPath));
            System.out.println("Procedural Distractor Path: " + proceduralDistractorPath);
        }
    }


}