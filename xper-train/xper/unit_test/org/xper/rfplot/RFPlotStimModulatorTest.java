package org.xper.rfplot;

import org.junit.Test;
import org.xper.rfplot.drawing.RFPlotPngObject;

public class RFPlotStimModulatorTest {

    @Test
    public void test(){
        PngPathModulator modulator = new PngPathModulator("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric");
        modulator.setClient(new MockRFPlotTaskDataSourceClient());
        RFPlotPngObject pngObject = new RFPlotPngObject("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric/1653428280110274_0.png");

        System.err.println(pngObject.getSpec());
        modulator.next(pngObject);


    }
}
