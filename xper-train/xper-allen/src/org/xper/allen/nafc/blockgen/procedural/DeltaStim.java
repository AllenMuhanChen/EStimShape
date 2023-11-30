package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.util.LinkedList;
import java.util.List;

public class DeltaStim extends ProceduralStim {
    public DeltaStim(ProceduralStim baseStim, int morphComponentIndex, int noiseComponentIndex){
        super(
                baseStim.generator,
                baseStim.getParameters(),
                baseStim.mSticks.getSample(),
                morphComponentIndex,
                noiseComponentIndex);
    }

    public static DeltaStim createDeltaNoise(ProceduralStim baseStim){
        int deltaIndex = DeltaStim.chooseDeltaIndex(baseStim);
        int drivingIndex = getDrivingIndex(baseStim);
        return new DeltaStim(baseStim, drivingIndex, deltaIndex);
    }

    public static DeltaStim createDeltaMorph(ProceduralStim baseStim){
        int deltaIndex = DeltaStim.chooseDeltaIndex(baseStim);
        int drivingIndex = getDrivingIndex(baseStim);
        return new DeltaStim(baseStim, deltaIndex, drivingIndex);
    }

    public static DeltaStim createDeltaNoiseDeltaMorph(ProceduralStim baseStim){
        int deltaIndex = DeltaStim.chooseDeltaIndex(baseStim);
        return new DeltaStim(baseStim, deltaIndex, deltaIndex);
    }

    private static Integer getDrivingIndex(ProceduralStim baseStim) {
        return baseStim.mSticks.getSample().getSpecialEndComp().get(0);
    }

    public static int chooseDeltaIndex(ProceduralStim baseStim){
        int drivingComponent = getDrivingIndex(baseStim);
        List<Integer> allComps = baseStim.mSticks.getSample().getCompList();
        List<Integer> elegibleComps = new LinkedList<>();
        for (int i=0; i<allComps.size(); i++){
            if (allComps.get(i) != drivingComponent){
                elegibleComps.add(allComps.get(i));
            }
        }

        //choose a random one
        int randIndex = (int) (Math.random() * elegibleComps.size());
        return elegibleComps.get(randIndex);
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        //Generate Sample
        ProceduralMatchStick sample = new ProceduralMatchStick();
        sample.setProperties(generator.getMaxImageDimensionDegrees());
        sample.setStimColor(parameters.color);
        sample.genNewComponentMatchStick(baseMatchStick, morphComponentIndex, parameters.morphMagnitude);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
        return sample;
    }



}