package org.xper.allen.pga.alexnet;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class SeedingStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData> {
    public SeedingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, String textureType, RGBColor color, float[] light_position) {
        super(generator, parentId, stimId, textureType, color, null, light_position, 0.0, 0);
        this.location = randomLocation();
        this.sizeDiameter = randomSize();
   }

    private double randomSize() {
        double minSize = 1;
        double maxSize = 10;
        return Math.random() * (maxSize - minSize) + minSize;
    }

    /**
     * The absolute length of the 227x227 image in the coords that matter here
     * is 30mm.
     *
     * It wouldn't make sense to sample from locations all over since we expect RFs
     * to be closer to zero,zero, so I will use a third of the length of the image
     * @return
     */
    private Coordinates2D randomLocation() {
        double length = 10;
        double height = 10;

        double x = Math.random() * length - length/2;
        double y = Math.random() * height - height/2;
        return new Coordinates2D(x, y);
    }


    @Override
    protected AlexNetGAMatchStick createMStick() {
        AlexNetGAMatchStick mStick = new AlexNetGAMatchStick(light_position, color, location, sizeDiameter, textureType);
        mStick.genMatchStickRand();

        return mStick;
    }
}