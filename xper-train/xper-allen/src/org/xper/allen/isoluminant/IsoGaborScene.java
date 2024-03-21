package org.xper.allen.isoluminant;

import org.xper.Dependency;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.gabor.IsoluminantGaborSpec;

public class IsoGaborScene extends AbstractTaskScene {

    @Dependency
    LookUpTableCorrector lutCorect;

    @Dependency
    SinusoidGainCorrector sinusoidGainCorrector;

    private IsoluminantGabor obj;

    @Override
    public void setTask(ExperimentTask task) {
        String stimSpecXml = task.getStimSpec();

        IsoluminantGaborSpec stimSpec;
        try {
            stimSpec = IsoluminantGaborSpec.fromXml(stimSpecXml);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }

        obj = new IsoluminantGabor(stimSpec, 150, lutCorect, sinusoidGainCorrector);

    }

    @Override
    public void drawStimulus(Context context) {
        obj.draw(context);

    }
}