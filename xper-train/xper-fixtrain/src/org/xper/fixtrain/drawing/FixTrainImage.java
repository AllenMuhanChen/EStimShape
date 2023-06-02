package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.fixtrain.drawing.TranslatableResizableImages;

/**
 * For drawing a specific image.
 */
public class FixTrainImage extends FixTrainDrawable<Coordinates2D>{

    private ImageSpec spec;
    private TranslatableResizableImages images;

    public FixTrainImage(ImageSpec spec) {
        this.spec = spec;
    }

    @Override
    public void draw(Context context) {
        images = new TranslatableResizableImages(1);
        images.initTextures();
        images.loadTexture(spec.getPath(), 0);
        images.draw(context, 0, spec.getCenter(), spec.getDimensions());
    }

    @Override
    public void setSpec(String spec) {
        this.spec = ImageSpec.fromXml(spec);
    }

    @Override
    public void scaleSize(double scale) {
        spec.setDimensions(new Coordinates2D(spec.getDimensions().getX() * scale, spec.getDimensions().getY() * scale));
    }

    @Override
    public Coordinates2D getSize() {
        return spec.getDimensions();
    }

    @Override
    protected void nextDrawable() {

    }

    @Override
    public String getSpec() {
        return spec.toXml();
    }
}