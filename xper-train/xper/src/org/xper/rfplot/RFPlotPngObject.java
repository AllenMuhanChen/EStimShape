package org.xper.rfplot;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.png.ImageDimensions;
import org.xper.png.PngSpec;
import org.xper.png.TranslatableResizableImages;

import java.util.ResourceBundle;

public class RFPlotPngObject implements RFPlotDrawable{

    private PngSpec spec;
    private TranslatableResizableImages images;

    public RFPlotPngObject() {
        setDefaultSpec();
    }

    @Override
    public void draw(Context context) {
        images.initTextures();
        images.loadTexture(spec.getPath(), 0);
        images.draw(context, 0, new Coordinates2D(spec.getxCenter(), spec.getyCenter()), spec.getImageDimensions());
    }

    @Override
    public void setSpec(String spec) {
        this.spec = PngSpec.fromXml(spec);
    }

    @Override
    public void setDefaultSpec() {
        spec = new PngSpec();
        spec.setPath("/home/r2_allen/Documents/EStimShape/dev_220404/pngs_dev_220404/1657907417_sample.png");
        spec.setAlpha(1);
        spec.setDimensions(new ImageDimensions(10,10));
        spec.setxCenter(0);
        spec.setyCenter(0);

        images = new TranslatableResizableImages(1);
    }

    @Override
    public String getSpec() {
        return spec.toXml();
    }
}
