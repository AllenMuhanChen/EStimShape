package org.xper.rfplot;

import org.junit.Test;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.RFPlotPngObject;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.gui.PngPathScroller;
import org.xper.rfplot.gui.PngSizeScroller;
import org.xper.rfplot.gui.ScrollerParams;

import static org.junit.Assert.assertTrue;

public class RFPlotStimModulatorTest {

    @Test
    public void png_path_scroller_test_next(){
        PngPathScroller scroller = new PngPathScroller("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric");
        RFPlotPngObject pngObject = new RFPlotPngObject("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric/1653428280110274_0.png");

        String firstPath = PngSpec.fromXml(pngObject.getSpec()).getPath();
        ScrollerParams newParams = scroller.next(new ScrollerParams(pngObject, null));
        String nextPath = PngSpec.fromXml(newParams.getRfPlotDrawable().getSpec()).getPath();
        assertTrue(firstPath!=nextPath);

    }

}
