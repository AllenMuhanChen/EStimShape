package org.xper.rfplot;

import org.junit.Test;
import org.xper.rfplot.drawing.RFPlotImgObject;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.gui.scroller.ImgPathScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;
import org.xper.util.ResourceUtil;

import static org.junit.Assert.assertTrue;

public class RFPlotStimModulatorTest {

    @Test
    public void png_path_scroller_test_next(){
        String resourcePath = ResourceUtil.getResource("RFPlotStimModulatorTest-TestLibrary");
        ImgPathScroller scroller = new ImgPathScroller(resourcePath, resourcePath);

        RFPlotImgObject pngObject = new RFPlotImgObject(ResourceUtil.getResource("RFPlotStimModulatorTest-DefaultPng.png"));

        String firstPath = PngSpec.fromXml(pngObject.getSpec()).getPath();
        ScrollerParams newParams = scroller.next(new ScrollerParams(pngObject, null));
        String nextPath = PngSpec.fromXml(newParams.getRfPlotDrawable().getSpec()).getPath();
        assertTrue(firstPath!=nextPath);

    }

}