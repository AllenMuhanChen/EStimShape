package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;

import javax.vecmath.Point3d;
import java.util.Random;

public class GrowingStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    public static final int USE_SPECIAL_END_COMP = 0;
    private final double magnitude;
    private static final Random random = new Random();

    public GrowingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude, String textureType) {
        super(stimId, generator, parentId, textureType, true);
        this.magnitude = magnitude;
    }


    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void choosePosition() {
        // decide if mutate
        boolean mutate;
        Random r = new Random();
        mutate = r.nextBoolean();
        PositioningStrategy parentPositioningStrategy = positionManager.readProperty(parentId).positioningStrategy;;
        if (mutate) {
            //if mutate -- read parent strategy and apply strategy
            MStickPosition parentLocation = positionManager.readProperty(parentId);

            if (parentPositioningStrategy == PositioningStrategy.RF_STRATEGY) {
                RFStrategy parentRFStrategy = rfStrategyManager.readProperty(parentId);
                if (parentRFStrategy == RFStrategy.COMPLETELY_INSIDE) {
                    Point3d parentCenterOfMass = parentLocation.getPosition();
                    Point3d newCenterOfMass = mutatePosition(parentCenterOfMass);
                    position = new MStickPosition(PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION, newCenterOfMass);
                } else if (parentRFStrategy == RFStrategy.PARTIALLY_INSIDE) {
                    Point3d parentCenterOfMass = parentLocation.getPosition();
                    Point3d newCenterOfMass = mutatePosition(parentCenterOfMass);
                    position = new MStickPosition(PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION, USE_SPECIAL_END_COMP, newCenterOfMass);
                }
            } else if (parentPositioningStrategy == PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION) {
                Point3d parentCenterOfMass = parentLocation.getPosition();
                Point3d newCenterOfMass = mutatePosition(parentCenterOfMass);
                position = new MStickPosition(PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION, newCenterOfMass);
            } else if (parentPositioningStrategy == PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION) {
                Point3d parentCenterOfMass = parentLocation.getPosition();
                Point3d newCenterOfMass = mutatePosition(parentCenterOfMass);
                position = new MStickPosition(PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION, USE_SPECIAL_END_COMP, newCenterOfMass);
            } else {
                throw new IllegalArgumentException("Unknown PositioningStrategy: " + parentPositioningStrategy);
            }

        } else {
            // if we have undefined behavior (i.e use RF to initiate random position - then we want to change strategy to positioning)
            MStickPosition parentLocation = positionManager.readProperty(parentId);
            if (parentPositioningStrategy == PositioningStrategy.RF_STRATEGY) {
                RFStrategy parentRFStrategy = rfStrategyManager.readProperty(parentId);
                if (parentRFStrategy == RFStrategy.COMPLETELY_INSIDE) {
                    Point3d parentCenterOfMass = parentLocation.getPosition();
                    position = new MStickPosition(PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION, parentCenterOfMass);
                } else if (parentRFStrategy == RFStrategy.PARTIALLY_INSIDE) {
                    Point3d parentCenterOfMass = parentLocation.getPosition();
                    position = new MStickPosition(PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION, USE_SPECIAL_END_COMP, parentCenterOfMass);
                }
            }
            // Any other case, we should be able to reuse the same positioning strategy......
            else{
                position = positionManager.readProperty(parentId);
            }
        }
    }

    protected Point3d mutatePosition(Point3d parentCenterOfMass) {
        double minPositionChange = magnitude * generator.getReceptiveField().getRadius()*2 / 4;
        double maxPositionChange = magnitude * generator.getReceptiveField().getRadius()*2;
        Random random = new Random();

        // Random angle in 2D space (0 to 2π)
        double angle = random.nextDouble() * 2 * Math.PI;

        // Random distance between min and max
        double distance = minPositionChange + random.nextDouble() * (maxPositionChange - minPositionChange);

        // Convert to Cartesian coordinates
        double dx = distance * Math.cos(angle);
        double dy = distance * Math.sin(angle);

        // Add to parent position (keep z unchanged)
        return new Point3d(
                parentCenterOfMass.x + dx,
                parentCenterOfMass.y + dy,
                parentCenterOfMass.z
        );
    }
    @Override
    protected void chooseSize() {
        double parentSizeDiameterDegrees = sizeManager.readProperty(parentId);
        double newSize = mutateSize(parentSizeDiameterDegrees);
        sizeDiameterDegrees = newSize;
    }

    private double mutateSize(double parentSizeDiameterDegrees) {
        double minSize = generator.getRfSource().getRFRadiusDegrees();
        double maxSizeChange = magnitude * generator.getRfSource().getRFRadiusDegrees();
        double minSizeChange = magnitude * maxSizeChange / 4;
        double randomChange = (random.nextDouble() * (maxSizeChange - minSizeChange));
        Random random = new Random();

        double newSize = random.nextBoolean() ? parentSizeDiameterDegrees * randomChange : parentSizeDiameterDegrees - randomChange;
        if (newSize < minSize) {
            newSize = minSize;
        }
        return newSize;
    }

    private void mutateContrast() {
        boolean isMutate = Math.random() < magnitude;
        if (isMutate){
            if (contrast == 0.4){
                contrast = 1.0;
            } else if (contrast == 1.0){
                contrast = 0.4;
            } else {
                throw new IllegalArgumentException("Invalid contrast value: " + contrast + ". Expected 0.4 or 1.0.");
            }
        }
    }

    @Override
    protected GrowingMatchStick createMStick() {
        //Generate MStick
        GrowingMatchStick parentMStick = initializeFromFile(generator.getReceptiveField(), textureType);
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(
                generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick;
        if (position.positioningStrategy == PositioningStrategy.RF_STRATEGY) {
            childMStick = new GrowingMatchStick(
                    generator.getReceptiveField(),
                    1/3.0,
                    rfStrategy,
                    textureType);
            if (rfStrategy == RFStrategy.PARTIALLY_INSIDE) {
                position.setTargetComp(childMStick.getSpecialEndComp().get(0));
            }
        } else if (position.positioningStrategy == PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION){
            childMStick = new GrowingMatchStick(position.position, 1/3.0);
            childMStick.setRf(generator.getReceptiveField());
            childMStick.setRfStrategy(rfStrategy);
        } else if (position.positioningStrategy == PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION){
            childMStick = new GrowingMatchStick(position.targetComp, position.position,1/3.0);
            childMStick.setRf(generator.getReceptiveField());
            childMStick.setRfStrategy(rfStrategy);
        } else{
            throw new IllegalArgumentException("Invalid position strategy in a GrowingStim: " + position.positioningStrategy);
        }

        childMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        childMStick.setStimColor(color);
        childMStick.setMaxDiameterDegrees(generator.getImageDimensionsDegrees());
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        position.setTargetComp(childMStick.getSpecialEndComp().get(0));
        return childMStick;
    }

    public static GrowingMatchStick initializeFromFile(ReceptiveField receptiveField, String textureType) {
        return new GrowingMatchStick(receptiveField,
                1 / 3.0,
                null,
                textureType);
    }


}