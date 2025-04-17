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

    private final StimType stimType;

    public SideTestStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, StimType stimType) {
        super(stimId, generator, parentId);
        this.stimType = stimType;
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
        if (stimType == StimType.SIDETEST_2Dvs3D_3D_SHADE) {
            this.textureType = "SHADE";
        }
        else if (stimType == StimType.SIDETEST_2Dvs3D_3D_SPECULAR) {
            this.textureType = "SPECULAR";
        }
        else if (stimType == StimType.SIDETEST_2Dvs3D_2D_LOW || stimType == StimType.SIDETEST_2Dvs3D_2D_HIGH){
            this.textureType = "2D";
        }
        else {
            throw new IllegalArgumentException("Unknown stimType: " + stimType + " for SideTestStim. You shouldn't" +
                    "Give this stimType to this class.");
        }
    }


    @Override
    protected GAMatchStick createMStick() {
        Point3d centerOfMass = getTargetsCenterOfMass(parentId);

        GAMatchStick mStick = new GAMatchStick(centerOfMass);
        mStick.setRf(generator.getReceptiveField());
        mStick.setProperties(sizeDiameterDegrees, textureType, contrast);
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