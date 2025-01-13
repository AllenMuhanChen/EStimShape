package org.xper.allen.twodvsthreed;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.stimproperty.RFStrategyPropertyManager;
import org.xper.allen.stimproperty.SizePropertyManager;
import org.xper.drawing.RGBColor;

public class TwoDVsThreeDStim implements Stim {
    private final RFStrategyPropertyManager rfStrategyManager;
    private final SizePropertyManager sizeManager;
    private final RFStrategy rfStrategy;
    private final double sizeDiameterDegrees;
    TwoDVsThreeDTrialGenerator generator;
    long targetStimId;
    String textureType;
    RGBColor color;
    private String targetSpecPath;
    private ReceptiveField receptiveField;

    public TwoDVsThreeDStim(TwoDVsThreeDTrialGenerator generator, long targetStimId, String textureType, RGBColor color) {
        this.generator = generator;
        this.targetStimId = targetStimId;
        this.textureType = textureType;
        this.color = color;


        rfStrategyManager = new RFStrategyPropertyManager(new JdbcTemplate(generator.gaDataSource));
        sizeManager = new SizePropertyManager(new JdbcTemplate(generator.gaDataSource));

        rfStrategy = rfStrategyManager.readProperty(targetStimId);
        sizeDiameterDegrees = sizeManager.readProperty(targetStimId);

        targetSpecPath = generator.gaSpecPath + "/" + targetStimId + "_spec.xml";
        receptiveField = generator.rfSource.getReceptiveField();
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        GAMatchStick mStick = new GAMatchStick(receptiveField, rfStrategy);
        mStick.setProperties(sizeDiameterDegrees, textureType);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(targetSpecPath, new double[]{0,0,0});
    }

    @Override
    public Long getStimId() {
        return null;
    }
}