package org.xper.allen.drawing.bubbles;

import java.awt.image.BufferedImage;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public abstract class Bubble<LocationT, SizeT> {
    public LocationT location;
    public SizeT size;
    public String imgPath;
    public Bubble(LocationT location, SizeT size, String imgPath) {
        this.location = location;
        this.size = size;
        this.imgPath = imgPath;
    }

    public List<NoisyPixel> noisyPixels = new ArrayList<>();

    public abstract void generateBubblePixels() throws IOException;

    protected int getBackgroundColor(BufferedImage image) {
        int backgroundColor = image.getRGB(0, 0);
        return backgroundColor;
    }

    public LocationT getLocation() {
        return location;
    }

    public void setLocation(LocationT location) {
        this.location = location;
    }

    public SizeT getSize() {
        return size;
    }

    public void setSize(SizeT size) {
        this.size = size;
    }

    public List<NoisyPixel> getNoisyPixels() {
        return noisyPixels;
    }
}