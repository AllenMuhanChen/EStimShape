package org.xper.rfplot;

import org.junit.Test;
import org.xper.rfplot.drawing.RFPlotPngObject;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.gui.PngPathScroller;
import org.xper.rfplot.gui.PngSizeScroller;

import static org.junit.Assert.assertTrue;

public class RFPlotStimModulatorTest {

    @Test
    public void png_path_scroller_test_next(){
        PngPathScroller scroller = new PngPathScroller(new MockRFPlotTaskDataSourceClient(), "/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric");
        RFPlotPngObject pngObject = new RFPlotPngObject("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric/1653428280110274_0.png");

        String firstPath = PngSpec.fromXml(pngObject.getSpec()).getPath();
        scroller.next(pngObject);
        String nextPath = PngSpec.fromXml(pngObject.getSpec()).getPath();
        assertTrue(firstPath!=nextPath);

    }

    @Test
    public void png_size_scroller_test_next(){
        PngSizeScroller scroller = new PngSizeScroller(new MockRFPlotTaskDataSourceClient());

        RFPlotPngObject pngObject = new RFPlotPngObject("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404_psychometric/1653428280110274_0.png");
        ImageDimensions firstDimensions = PngSpec.fromXml(pngObject.getSpec()).getDimensions();
        scroller.next(pngObject);
        ImageDimensions nextDimensions = PngSpec.fromXml(pngObject.getSpec()).getDimensions();
        assertTrue(firstDimensions.getHeight() > nextDimensions.getHeight());
    }
}
