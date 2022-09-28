package org.xper.rfplot.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.drawing.png.TranslatableResizableImages;

public class RFPlotPngObject extends DefaultSpecRFPlotDrawable{

    private PngSpec spec;
    private TranslatableResizableImages images;

    private String defaultPath;

    public RFPlotPngObject(String defaultPath) {
        this.defaultPath = defaultPath;
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
        spec.setPath(defaultPath);
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
