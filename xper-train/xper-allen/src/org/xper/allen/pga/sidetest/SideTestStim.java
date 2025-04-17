package org.xper.allen.pga.sidetest;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.pga.FromDbGABlockGenerator;
import org.xper.allen.pga.GAStim;
import org.xper.allen.pga.StimType;

import javax.vecmath.Point3d;

import static org.xper.allen.pga.GrowingStim.initializeFromFile;

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
        // We just have SIDETEST_2Dvs3D instead of variations. Might not even need these to be HONEST.
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



    private Point3d getTargetsCenterOfMass(long targetStimId) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.getDbUtil().getDataSource());

        // Read the data XML from StimSpec table
        String dataXml = (String) jdbcTemplate.queryForObject(
                "SELECT data FROM StimSpec WHERE id = ?",
                new Object[]{targetStimId},
                String.class
        );

        if (dataXml == null || dataXml.isEmpty()) {
            throw new RuntimeException("No data found for stimId " + targetStimId + " in StimSpec table");
        }

        // Parse the XML into AllenMStickData
        AllenMStickData mStickData = (AllenMStickData) AllenMStickData.fromXml(dataXml);


        // Get center of mass
        Point3d centerOfMass = mStickData.getMassCenter();
        if (centerOfMass == null) {
            throw new RuntimeException("No center of mass found for stimId " + targetStimId + " in StimSpec table");
        }

        return centerOfMass;
    }
}