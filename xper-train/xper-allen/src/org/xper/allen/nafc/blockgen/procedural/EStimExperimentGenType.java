package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.intan.stimulation.EStimParameters;

import javax.swing.*;
import java.util.LinkedList;
import java.util.List;

public class EStimExperimentGenType extends ProceduralRandGenType<EStimExperimentGenType.EStimExperimentGenParameters> {

    protected JTextField numDeltaTrialSetsField;

    public EStimExperimentGenType(NAFCBlockGen generator) {
        super(generator);
    }

    public String getLabel() {
        return "EStimExperiment";
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        //Generate the base matchstick
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(generator.getMaxImageDimensionDegrees(), "SHADE");
        baseMStick.setStimColor(parameters.getProceduralStimParameters().color);
        baseMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parameters.stimId + "_spec.xml");
        int morphIndex = parameters.compId;
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < parameters.getNumTrials(); i++) {
            //using estim values set on the IntanGUI
            EStimProceduralStim stim = new EStimProceduralStim(generator, parameters.getProceduralStimParameters(), baseMStick, morphIndex, noiseIndex);
            newBlock.add(stim);
        }

        //ADD DELTA TRIALS
        //choose random trials to make delta trials from
        List<ProceduralStim> deltaTrials = new LinkedList<>();
        for (int i=0; i<parameters.numDeltaTrialSets; i++){
            int randIndex = (int) (Math.random() * parameters.getNumTrials());
            ProceduralStim baseStim = (ProceduralStim) newBlock.get(randIndex);
            ProceduralStim deltaMorph = new DeltaStim(baseStim, true, false);
            ProceduralStim deltaNoise = new DeltaStim(baseStim, false, true);
            ProceduralStim deltaBoth = new DeltaStim(baseStim, true, true);
            deltaTrials.add(deltaMorph);
            deltaTrials.add(deltaNoise);
            deltaTrials.add(deltaBoth);
        }
        newBlock.addAll(deltaTrials);
        return newBlock;
    }

    public class EStimExperimentGenParameters extends MockExperimentGenType.MockExperimentGenParameters {
        public long stimId;
        public int compId;


    }
}