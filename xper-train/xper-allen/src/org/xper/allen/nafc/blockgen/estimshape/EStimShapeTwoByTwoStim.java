package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralStim;
import org.xper.allen.nafc.blockgen.procedural.NAFCBlockGen;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.rfplot.drawing.png.ImageDimensions;

import java.awt.*;
import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedList;
import java.util.List;

public class EStimShapeTwoByTwoStim extends EStimShapeProceduralStim {

    //input parameters
    EStimExperimentTrialGenerator generator;
    AllenMStickSpec sampleSpec;
    Collection<AllenMStickSpec> baseProceduralDistractorSpecs;


    public EStimShapeTwoByTwoStim(
            EStimExperimentTrialGenerator generator,
            ProceduralStimParameters parameters,
            AllenMStickSpec sampleSpec,
            Collection<AllenMStickSpec> baseProceduralDistractorSpecs) {
        super(generator, parameters, null, -1,
                false);
        this.generator = (EStimExperimentTrialGenerator) generator;
        this.sampleSpec = sampleSpec;
        this.baseProceduralDistractorSpecs = baseProceduralDistractorSpecs;
    }


    @Override
    public void generateMatchSticksAndSaveSpecs(){
        //sample
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        sample.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource()),
                parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromShapeSpec(sampleSpec, new double[]{0,0,0});
        System.out.println("noise origin: " + sample.calculateNoiseOrigin(sample.getDrivingComponent()));
        noiseComponentIndex = sample.getDrivingComponent();
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        //match
        TwobyTwoMatchStick match = new TwobyTwoMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(sampleSpec, new double[]{0,0,0});
        match.centerShape();
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));

        //choices
        for (AllenMStickSpec choiceSpec : baseProceduralDistractorSpecs) {
            TwobyTwoMatchStick choice = new TwobyTwoMatchStick();
            choice.setProperties(parameters.getSize(), parameters.textureType);
            choice.setStimColor(parameters.color);
            choice.genMatchStickFromShapeSpec(choiceSpec, new double[]{0,0,0});
            choice.centerShape();
            mSticks.addProceduralDistractor(choice);
            mStickSpecs.addProceduralDistractor(mStickToSpec(choice));
        }
    }
}