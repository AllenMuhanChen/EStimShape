package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

import java.io.File;

public class FixTrainRandImage extends FixTrainDrawable {

    private File directory;
    private String currentImgPath;

    public FixTrainRandImage(File directory) {
        this.directory = directory;
        updateDrawable();
    }

    public FixTrainRandImage(String directoryPath) {
        this(new File(directoryPath));
    }

    @Override
    public void draw(Context context) {
        TranslatableResizableImages images = new TranslatableResizableImages(1);
        images.initTextures();
        images.loadTexture(currentImgPath, 0);
        images.draw(context, 0, new Coordinates2D(0,0), new Coordinates2D(10,10));
    }

    @Override
    public void setSpec(String spec) {
        this.directory = new File(spec);
    }

    @Override
    public void updateDrawable() {
        File randImage = RandImageFetcher.fetchRandImage(directory);
        this.currentImgPath = randImage.getAbsolutePath();
    }

    @Override
    public String getSpec() {
        return directory.getAbsolutePath();
    }


}