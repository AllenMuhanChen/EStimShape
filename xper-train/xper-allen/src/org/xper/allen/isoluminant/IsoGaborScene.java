package org.xper.allen.isoluminant;

import com.thoughtworks.xstream.converters.ConversionException;
import org.xper.Dependency;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.allen.rfplot.IsochromaticGabor;

/**
 * Scene to present Isochromatic/Isoluminant Gabor stimuli

 */
public class IsoGaborScene extends AbstractTaskScene {

    @Dependency
    LookUpTableCorrector lutCorrector;

    @Dependency
    SinusoidGainCorrector sinusoidGainCorrector;

    @Dependency
    int targetLuminanceCandela;

    private Gabor obj;

    @Override
    public void setTask(ExperimentTask task) {
        String stimSpecXml = task.getStimSpec();

        try {
            IsoGaborSpec stimSpec;
            stimSpec = IsoGaborSpec.fromXml(stimSpecXml);
            if (stimSpec.getType().equals("RedGreen") || stimSpec.getType().equals("CyanYellow")) {
                obj = new IsoluminantGabor(stimSpec, targetLuminanceCandela, lutCorrector, sinusoidGainCorrector);
            } else if (stimSpec.getType().equals("Red") ||
                    stimSpec.getType().equals("Green") ||
                    stimSpec.getType().equals("Blue") ||
                    stimSpec.getType().equals("Yellow") ||
                    stimSpec.getType().equals("Cyan") ||
                    stimSpec.getType().equals("Gray")) {
                obj = new IsochromaticGabor(stimSpec, targetLuminanceCandela, lutCorrector);
            } else {
                throw new RuntimeException("Unknown color space: " + stimSpec.getType());
            }
        } catch (ConversionException ce) {
            try{
                MixedGaborSpec stimSpec = MixedGaborSpec.fromXml(stimSpecXml);
                obj = new CombinedGabor(stimSpec.chromaticSpec, stimSpec.luminanceSpec, targetLuminanceCandela, lutCorrector, sinusoidGainCorrector);
            } catch (Exception e) {
                throw new RuntimeException("Error in parsing stimulus spec: " + stimSpecXml, e);
            }
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

    public int getTargetLuminanceCandela() {
        return targetLuminanceCandela;
    }

    public void setTargetLuminanceCandela(int targetLuminanceCandela) {
        this.targetLuminanceCandela = targetLuminanceCandela;
    }
}