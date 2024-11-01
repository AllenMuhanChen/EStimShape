package org.xper.allen.pga.alexnet;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class RFLocStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData>{
    // Distance Constraints
    private static final double TOTAL_SPACE = 30.0; // Total available space (-15 to 15)
    private static final double MAX_DISTANCE_MORPH = TOTAL_SPACE / 6; // Maximum radius for magnitude 1.0

    // Size constraints
    private static final double MIN_SIZE = 1.0;
    private static final double MAX_SIZE = 5.0;
    private static final double MAX_SIZE_CHANGE = (MAX_SIZE - MIN_SIZE) / 2.0; // Maximum size change for magnitude 1.0

    public RFLocStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, RGBColor color, float[] light_position, double magnitude) {
        super(generator, parentId, stimId, null, color, null, light_position, 0, magnitude, 1.0);
    }

    @Override
    protected AlexNetGAMatchStick createMStick() {
        //Read the parent properties, including position, size, etc.
        AlexNetGAMStickData parentData = AlexNetGAMStickData.fromXml(generator.getDbUtil().readStimSpec(parentId).getSpec());
        textureType = parentData.textureType;
        color = parentData.stimColor;
        contrast = parentData.contrast;

        mutateSizeAndLocation(parentData);

        //Generate Parent Stick with Mutated Size and Location
        AlexNetGAMatchStick newMStick = new AlexNetGAMatchStick(parentData.light_position, color, location, sizeDiameter, textureType, contrast);
        newMStick.genMatchStickFromShapeSpec(parentData.stickSpec, new double[]{0,0,0});
        newMStick.positionShape();

        return newMStick;
    }

    private void mutateSizeAndLocation(AlexNetGAMStickData parentData) {
        // Initialize with parent values
        sizeDiameter = parentData.sizeDiameter;
        location = parentData.location;


        // Always do one mutation with 50/50 chance
        boolean doSize = Math.random() < 0.5;
        if (doSize) {
            sizeDiameter = mutateSize(parentData);
            // Add location mutation with probability = magnitude
            if (Math.random() < magnitude) {
                location = mutateLocation(parentData);
            }
        } else {
            location = mutateLocation(parentData);
            // Add size mutation with probability = magnitude
            if (Math.random() < magnitude) {
                sizeDiameter = mutateSize(parentData);
            }
        }
    }

    private Coordinates2D mutateLocation(AlexNetGAMStickData parentData) {
        // Get current position
        double currentX = parentData.location.getX();
        double currentY = parentData.location.getY();

        // Generate random angle in radians (0 to 2π)
        double angle = Math.random() * 2 * Math.PI;

        // Calculate maximum distance for the given magnitude
        // magnitude of 1.0 maps to half of the total space (15 units)
        double distance = magnitude * MAX_DISTANCE_MORPH;

        // Calculate new position using polar coordinates
        double deltaX = distance * Math.cos(angle);
        double deltaY = distance * Math.sin(angle);

        // Add changes to current position
        double newX = currentX + deltaX;
        double newY = currentY + deltaY;

        // Clamp values to ensure they stay within bounds (-15 to 15)
        newX = Math.max(-MAX_DISTANCE_MORPH * 2, Math.min(MAX_DISTANCE_MORPH * 2, newX));
        newY = Math.max(-MAX_DISTANCE_MORPH * 2, Math.min(MAX_DISTANCE_MORPH * 2, newY));

        return new Coordinates2D(newX, newY);
    }

    private double mutateSize(AlexNetGAMStickData parentData) {
        // Get current size
        double currentSize = parentData.sizeDiameter;

        // Calculate maximum size change for the given magnitude
        // magnitude of 1.0 maps to half of the size range
        double maxChange = magnitude * MAX_SIZE_CHANGE;

        // Generate random change between -maxChange and +maxChange
        double sizeChange = (Math.random() * 2 - 1) * maxChange;

        // Calculate new size
        double newSize = currentSize + sizeChange;

        // Clamp to ensure size stays within bounds
        return Math.max(MIN_SIZE, Math.min(MAX_SIZE, newSize));
    }
}