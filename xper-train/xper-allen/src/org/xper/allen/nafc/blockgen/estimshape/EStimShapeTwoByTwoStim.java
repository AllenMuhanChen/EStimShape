package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.nafc.blockgen.procedural.NAFCBlockGen;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import java.util.List;

public class EStimShapeTwoByTwoStim extends ProceduralStim {

    //input parameters
    EStimExperimentTrialGenerator generator;
    AllenMStickSpec sampleSpec;
    List<AllenMStickSpec> baseProceduralDistractorSpecs;


    public EStimShapeTwoByTwoStim(NAFCBlockGen generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex) {
        super(generator, parameters, baseMatchStick, morphComponentIndex);
    }


    @Override
    public void generateMatchSticksAndSaveSpecs(){
        //sample
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()), textureType);
        sample.genMatchStickFromShapeSpec(sampleSpec, new double[]{0,0,0});
        sample.setStimColor(parameters.color);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        //match
        TwobyTwoMatchStick match = new TwobyTwoMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.genMatchStickFromShapeSpec(sampleSpec, new double[]{0,0,0});
        sample.setStimColor(parameters.color);
        match.centerShape();
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));

        //choices
        for (AllenMStickSpec choiceSpec : baseProceduralDistractorSpecs) {
            TwobyTwoMatchStick choice = new TwobyTwoMatchStick();
            choice.setProperties(parameters.getSize(), parameters.textureType);
            sample.setStimColor(parameters.color);
            choice.genMatchStickFromShapeSpec(choiceSpec, new double[]{0,0,0});
            choice.centerShape();
            mSticks.addProceduralDistractor(choice);
            mStickSpecs.addProceduralDistractor(mStickToSpec(choice));
        }
    }
}