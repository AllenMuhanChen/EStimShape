package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

import java.io.File;

public class FixTrainRandImage extends FixTrainDrawable<Coordinates2D> {

    private RandImageSpec randImageSpec = new RandImageSpec();

    public FixTrainRandImage(File directory, Coordinates2D defaultDimensions) {
        this.randImageSpec.setDirectory(directory);
        this.randImageSpec.setDimensions(defaultDimensions);
        nextDrawable();
    }

    public FixTrainRandImage(String directoryPath, Coordinates2D defaultDimensions) {
        this(new File(directoryPath), defaultDimensions);
    }

    @Override
    public void draw(Context context) {
        TranslatableResizableImages images = new TranslatableResizableImages(1);
        images.initTextures();
        images.loadTexture(randImageSpec.getCurrentImgPath(), 0);
        images.draw(context, 0, fixationPosition, randImageSpec.getDimensions());
    }

    @Override
    public void setSpec(String spec) {
        this.randImageSpec = RandImageSpec.fromXml(spec);
    }

    @Override
    public void scaleSize(double scale) {
        this.randImageSpec.setDimensions(new Coordinates2D(randImageSpec.getDimensions().getX() * scale, randImageSpec.getDimensions().getY() * scale));
    }

    @Override
    public Coordinates2D getSize() {
        return randImageSpec.getDimensions();
    }

    @Override
    public void nextDrawable() {
        File randImage = RandImageFetcher.fetchRandImage(randImageSpec.getDirectory());
        this.randImageSpec.setCurrentImgPath(randImage.getAbsolutePath());
    }

    @Override
    public String getSpec() {
        return randImageSpec.toXml();
    }


}