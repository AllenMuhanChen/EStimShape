package org.xper.allen.isoluminant;

import org.xper.Dependency;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

/**
 * Scene to present Isochromatic/Isoluminant Gabor stimuli

 */
public class IsoGaborScene extends AbstractTaskScene {

    @Dependency
    LookUpTableCorrector lutCorrector;

    @Dependency
    SinusoidGainCorrector sinusoidGainCorrector;

    private IsoluminantGabor obj;



    @Override
    public void setTask(ExperimentTask task) {
        String stimSpecXml = task.getStimSpec();

        IsoGaborSpec stimSpec;
        stimSpec = IsoGaborSpec.fromXml(stimSpecXml);
        if (stimSpec.type.equals("RedGreen")) {
            obj = new IsoluminantGabor(stimSpec, 150, lutCorrector, sinusoidGainCorrector);
        } else if (stimSpec.type.equals("CyanYellow")){
            obj = new IsoluminantGabor(stimSpec, 150, lutCorrector, sinusoidGainCorrector);
        }
        else {
            throw new RuntimeException("Unknown color space: " + stimSpec.type);
        }
    }



    @Override
    public void drawStimulus(Context context) {
        obj.draw(context);
    }

    public LookUpTableCorrector getLutCorrector() {
        return lutCorrector;
    }

    public void setLutCorrector(LookUpTableCorrector lutCorrector) {
        this.lutCorrector = lutCorrector;
    }

    public SinusoidGainCorrector getSinusoidGainCorrector() {
        return sinusoidGainCorrector;
    }

    public void setSinusoidGainCorrector(SinusoidGainCorrector sinusoidGainCorrector) {
        this.sinusoidGainCorrector = sinusoidGainCorrector;
    }
}