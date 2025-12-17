package org.xper.allen.pga.sidetest;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.pga.FromDbGABlockGenerator;
import org.xper.allen.pga.GAStim;

import javax.vecmath.Point3d;

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
    protected GAMatchStick createMStick() {
        Point3d centerOfMass = getTargetsCenterOfMass(parentId);

        GAMatchStick mStick = new GAMatchStick(centerOfMass);
        mStick.setRf(generator.getReceptiveField());
        mStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        return mStick;
    }

}