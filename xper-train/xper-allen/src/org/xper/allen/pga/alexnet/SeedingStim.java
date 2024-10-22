package org.xper.allen.pga.alexnet;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class SeedingStim extends AlexNetGAStim<AlexNetGAMAtchStick, AlexNetGAMStickData> {
    public SeedingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, String textureType, RGBColor color, Coordinates2D location, float[] light_position, double sizeDiameter) {
        super(generator, parentId, stimId, textureType, color, location, light_position, sizeDiameter);
    }

    @Override
    protected AlexNetGAMAtchStick createMStick() {
        return null;
    }
}