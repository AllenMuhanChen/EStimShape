package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.util.AllenDbUtil;

public class EStimProceduralStim extends ProceduralStim{
    public EStimProceduralStim(NAFCBlockGen generator, ProceduralStimParameters parameters, ExperimentMatchStick baseMatchStick, int morphComponentIndex, int noiseComponentIndex) {
        super(generator, parameters, baseMatchStick, morphComponentIndex);
    }


    @Override
    public void writeStim() {
        writeStimObjDataSpecs();
        assignTaskId();
        writeStimSpec();
        writeEStimSpec();
    }

    protected void writeEStimSpec() {
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeEStimObjData(getStimId(), "EStimEnabled", "");
    }
}