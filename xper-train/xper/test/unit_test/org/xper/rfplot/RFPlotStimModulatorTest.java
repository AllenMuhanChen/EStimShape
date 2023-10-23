package org.xper.rfplot;

import org.junit.Test;
import org.xper.rfplot.drawing.RFPlotPngObject;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.gui.scroller.PngPathScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;
import org.xper.util.ResourceUtil;

import static org.junit.Assert.assertTrue;

public class RFPlotStimModulatorTest {

    @Test
    public void png_path_scroller_test_next(){
        String resourcePath = ResourceUtil.getResource("RFPlotStimModulatorTest-TestLibrary");
        PngPathScroller scroller = new PngPathScroller(resourcePath, resourcePath);

        RFPlotPngObject pngObject = new RFPlotPngObject(ResourceUtil.getResource("RFPlotStimModulatorTest-DefaultPng.png"));

        String firstPath = PngSpec.fromXml(pngObject.getSpec()).getPath();
        ScrollerParams newParams = scroller.next(new ScrollerParams(pngObject, null));
        String nextPath = PngSpec.fromXml(newParams.getRfPlotDrawable().getSpec()).getPath();
        assertTrue(firstPath!=nextPath);

    }

}