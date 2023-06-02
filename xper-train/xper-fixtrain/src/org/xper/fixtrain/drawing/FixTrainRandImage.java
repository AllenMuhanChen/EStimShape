package org.xper.fixtrain.drawing;

import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

import java.io.File;

public class FixTrainRandImage extends FixTrainDrawable<Coordinates2D> {

    private File directory;
    private String currentImgPath;
    private Coordinates2D dimensions;

    public FixTrainRandImage(File directory, Coordinates2D defaultDimensions) {
        this.directory = directory;
        this.dimensions = defaultDimensions;
        nextDrawable();
    }

    public FixTrainRandImage(String directoryPath, Coordinates2D defaultDimensions) {
        this(new File(directoryPath), defaultDimensions);
    }

    @Override
    public void draw(Context context) {
        TranslatableResizableImages images = new TranslatableResizableImages(1);
        images.initTextures();
        images.loadTexture(currentImgPath, 0);
        images.draw(context, 0, fixationPosition, dimensions);
    }

    @Override
    public void setSpec(String spec) {
        this.directory = new File(spec);
    }

    @Override
    public void scaleSize(double scale) {
        this.dimensions = new Coordinates2D(dimensions.getX() * scale, dimensions.getY() * scale);
    }

    @Override
    public Coordinates2D getSize() {
        return dimensions;
    }

    @Override
    public void nextDrawable() {
        File randImage = RandImageFetcher.fetchRandImage(directory);
        this.currentImgPath = randImage.getAbsolutePath();
    }

    @Override
    public String getSpec() {
        return directory.getAbsolutePath();
    }


}