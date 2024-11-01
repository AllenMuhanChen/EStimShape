package org.xper.allen.pga.alexnet;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class SeedingStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData> {
    public SeedingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, RGBColor color, float[] light_position) {
        super(generator, parentId, stimId, null, color, null, light_position, 0.0, 0, 1.0);
        this.location = randomLocation();
        this.sizeDiameter = randomSize();
   }

    private double randomSize() {
        double minSize = 1;
        double maxSize = 3;
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
        double length = 5;
        double height = 5;

        double x = Math.random() * length - length/2;
        double y = Math.random() * height - height/2;
        return new Coordinates2D(x, y);
    }


    @Override
    protected AlexNetGAMatchStick createMStick() {
        //ALLEN TEST - random color
//        int r = Math.random() < 0.5 ? 0 : 1;
//        int g = Math.random() < 0.5 ? 0 : 1;
//        int b = Math.random() < 0.5 ? 0 : 1;
//        color = new RGBColor(r, g, b);

        //ALLEN TEST - random texture
        if (Math.random() < 0.5) {
            if (Math.random() < 0.5) {
                textureType = "SPECULAR";
            }
            else {
                textureType = "SHADE";
            }
        }
        else {
            textureType = "2D";
        }
        contrast = Math.random();

        AlexNetGAMatchStick mStick = new AlexNetGAMatchStick(light_position, color, location, sizeDiameter, textureType, contrast);
        mStick.genMatchStickRand();

        return mStick;
    }
}