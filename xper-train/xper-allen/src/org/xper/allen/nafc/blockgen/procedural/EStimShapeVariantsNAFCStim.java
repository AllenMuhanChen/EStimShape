package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.stimproperty.*;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.RGBColor;

import javax.vecmath.Point3d;
import java.util.List;

public class EStimShapeVariantsNAFCStim extends EStimShapeProceduralStim{

    private String texture;
    private Float sampleSize;
    private NAFCNoiseMapper noiseMapper;
    private RGBColor color;
    private double choiceSize;

    public EStimShapeVariantsNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, List<Integer> morphComponentIndcs, boolean isEStimEnabled, long baseMStickStimSpecId, int compId) {
        super(generator, parameters, baseMatchStick, morphComponentIndcs, isEStimEnabled, baseMStickStimSpecId, compId);
    }

    public EStimShapeVariantsNAFCStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, Long variantId, boolean isEStimEnabled){
        super(generator, parameters, null, null, isEStimEnabled, variantId, -1);
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(generator.getGaDataSource());
        RFStrategyPropertyManager rfStrategyPropertyManager = new RFStrategyPropertyManager(gaJDBCTemplate);
        SizePropertyManager sizePropertyManager = new SizePropertyManager(gaJDBCTemplate);
        TexturePropertyManager texturePropertyManager = new TexturePropertyManager(gaJDBCTemplate);
        UnderlingAverageRGBPropertyManager underlingAverageRGBPropertyManager = new UnderlingAverageRGBPropertyManager(gaJDBCTemplate);
        CompsToPreserveManager compsToPreserveManager = new CompsToPreserveManager(gaJDBCTemplate);

        sampleSize = sizePropertyManager.readProperty(variantId);
        texture = texturePropertyManager.readProperty(variantId);
        color = underlingAverageRGBPropertyManager.readProperty(variantId);

        //TODO: figure out right combinations of parameters for optimal placement of choices here...
        choiceSize = 10;

        noiseMapper = generator.getNoiseMapper();
        baseMatchStick = new PruningMatchStick(noiseMapper);
        baseMatchStick.setProperties(sampleSize, texture, is2D(), 1.0);
        baseMatchStick.setStimColor(color);

        morphComponentIndcs = (List<Integer>) compsToPreserveManager.readProperty(variantId);
    }

    protected boolean is2D() {
        return this.texture.equals("2D");
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        AllenMStickSpec baseStickSpec = new AllenMStickSpec();
        baseStickSpec.setMStickInfo(baseMatchStick, false);

        //maybe we could do some minor morphs here??

        PruningMatchStick sample = new PruningMatchStick(noiseMapper);
        sample.setProperties(sampleSize, texture, is2D(), 1.0);
        sample.setStimColor(color);


        sample.genMatchStickFromShapeSpec(baseStickSpec, new double[]{0,0,0});
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        return sample;
    }

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        PruningMatchStick match = new  PruningMatchStick(noiseMapper);
        match.setProperties(choiceSize, texture, is2D(), 1.0);
        match.setStimColor(color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.moveCenterOfMassTo(new Point3d(0,0,0));

        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
    }

    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            correctNoiseRadius(proceduralDistractor);
            proceduralDistractor.setProperties(choiceSize, texture, is2D(), 1.0);
            proceduralDistractor.setStimColor(color);
            proceduralDistractor.genNewComponentsMatchStick(sample, morphComponentIndcs, parameters.morphMagnitude, 0.5, true, proceduralDistractor.maxAttempts);
            mSticks.addProceduralDistractor(proceduralDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(proceduralDistractor));
        }
    }


    protected void writeExtraData() {
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeBaseMStickId(getStimId(), baseMStickStimSpecId, -1); //don't really need to save this info since it's present in another table
    }




}
