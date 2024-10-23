package org.xper.allen.pga.alexnet;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class SeedingStim extends AlexNetGAStim<AlexNetGAMAtchStick, AlexNetGAMStickData> {
    public SeedingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, String textureType, RGBColor color, Coordinates2D location, float[] light_position, double sizeDiameter) {
        super(generator, parentId, stimId, textureType, color, location, light_position, sizeDiameter);
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
    protected AlexNetGAMAtchStick createMStick() {
        AlexNetGAMAtchStick mStick = new AlexNetGAMAtchStick(light_position, color, location, sizeDiameter, textureType);
        mStick.genMatchStickRand();

        return mStick;
    }
}