package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

import java.io.File;
import java.util.Arrays;
import java.util.function.Predicate;

public class FixTrainRandImage extends FixTrainDrawable {

    private File directory;

    @Override
    public void draw(Context context) {
        File randImage = RandImageFetcher.fetchRandImage(directory);
        TranslatableResizableImages images = new TranslatableResizableImages(1);
        images.initTextures();
        images.loadTexture(randImage.getAbsolutePath(), 0);
        images.draw(context, 0, new Coordinates2D(0,0), new Coordinates2D(10,10));
    }

    @Override
    public void setSpec(String spec) {
        this.directory = new File(spec);
    }

    @Override
    public String getSpec() {
        return directory.getAbsolutePath();
    }


}