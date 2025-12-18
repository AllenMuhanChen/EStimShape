package org.xper.allen.pga.sidetest;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.pga.FromDbGABlockGenerator;
import org.xper.allen.pga.GAStim;
import org.xper.allen.pga.MStickPosition;
import org.xper.allen.pga.RFStrategy;

import javax.vecmath.Point3d;

import static org.xper.allen.pga.GrowingStim.USE_SPECIAL_END_COMP;

public class SideTestStim extends GAStim<GAMatchStick, AllenMStickData> {


    public SideTestStim(Long stimId, FromDbGABlockGenerator generator, Long parentId) {
        super(stimId, generator, parentId);
    }

    @Override
    protected void chooseRFStrategy() {
        this.rfStrategy = this.rfStrategyManager.readProperty(parentId);
    }


    @Override
    protected void chooseSize() {
        this.sizeDiameterDegrees = this.sizeManager.readProperty(parentId);
    }

    @Override
    protected void chooseTextureType() {
        if (isParent2D()) {
            // We want to make a 3D stimulus from a 2D parent stimulus.
            this.is2d = false;
            this.textureType = underlyingTextureManager.readProperty(parentId);
        } else {
            // We want to make a 2D stimulus from a 3D parent stimulus.
            this.is2d = true;
            this.textureType = "2D";
        }
    }

    private boolean isParent2D() {
        return this.textureManager.readProperty(parentId).equals("2D");
    }

    @Override
    protected void choosePosition() {
        MStickPosition parentLocation = positionManager.readProperty(parentId);
        if (parentLocation.getPositioningStrategy() == PositioningStrategy.RF_STRATEGY){
            RFStrategy parentRFStrategy = rfStrategyManager.readProperty(parentId);
            if (parentRFStrategy == RFStrategy.COMPLETELY_INSIDE) {
                Point3d parentCenterOfMass = parentLocation.getPosition();
                position = new MStickPosition(PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION, parentCenterOfMass);
            } else if (parentRFStrategy == RFStrategy.PARTIALLY_INSIDE) {
                Point3d parentCenterOfMass = parentLocation.getPosition();
                position = new MStickPosition(PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION, USE_SPECIAL_END_COMP, parentCenterOfMass);
            }
        } else{
            position = parentLocation;
        }
    }

    @Override
    protected GAMatchStick createMStick() {
//        Point3d centerOfMass = getTargetsCenterOfMass(parentId);

        GAMatchStick mStick;
        if (position.getPositioningStrategy() == PositioningStrategy.MOVE_CENTER_TO_SPECIFIC_LOCATION) {
            mStick = new GAMatchStick(position.getPosition());
        }
        else if (position.getPositioningStrategy() == PositioningStrategy.MOVE_COMP_TO_SPECIFIC_LOCATION){
            mStick = new GAMatchStick(position.getTargetComp(), position.getPosition());
        }
        else if (position.getPositioningStrategy() == PositioningStrategy.PRESERVED_COMP_BASED){
            mStick = new GAMatchStick(position.getTargetComp(), position.getPosition());
        }
        else {
            throw new IllegalArgumentException("Unknown PositioningStrategy: " + position.getPositioningStrategy());
        }
        mStick.setRf(generator.getReceptiveField());
        mStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        return mStick;
    }

}