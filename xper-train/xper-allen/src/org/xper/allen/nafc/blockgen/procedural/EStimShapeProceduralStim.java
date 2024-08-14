package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.rfplot.drawing.png.ImageDimensions;

import javax.vecmath.Point3d;
import java.awt.*;

public class EStimShapeProceduralStim extends ProceduralStim{
    protected final ReceptiveFieldSource rfSource;
    protected final boolean isEStimEnabled;
    protected long[] eStimObjData;

    public EStimShapeProceduralStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, boolean isEStimEnabled) {
        super(generator, parameters, baseMatchStick, morphComponentIndex);
        this.rfSource = generator.getRfSource();
        this.isEStimEnabled = isEStimEnabled;
    }

    @Override
    public void writeStim() {
        writeStimObjDataSpecs();
        assignTaskId();
        writeEStimSpec();
        writeStimSpec();
    }

    @Override
    public void preWrite(){
        super.preWrite();
        generateSampleCompMap();
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            System.out.println("Trying to generate EStimShapeProceduralStim");
            try {
                EStimShapeProceduralMatchStick sample = (EStimShapeProceduralMatchStick) generateSample();

                morphComponentIndex = sample.getDrivingComponent();
                noiseComponentIndex = sample.getDrivingComponent();

                generateMatch(sample);

                generateProceduralDistractors(sample);

                generateRandDistractors();

                break;
            } catch (Exception e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
            }
        }
    }

    @Override
    protected ProceduralMatchStick generateSample() {

        //Generate Sample
        EStimShapeProceduralMatchStick sample = new EStimShapeProceduralMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                ((EStimExperimentTrialGenerator) generator).getRF(), generator.getPngMaker().getNoiseMapper()
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimExperimentTrialGenerator) generator).getRfSource().getRFRadiusDegrees()), parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, morphComponentIndex, 0, true, sample.maxAttempts, generator.getPngMaker().getNoiseMapper());

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;

    }

    private void generateSampleCompMap() {
        generator.getPngMaker().createAndSaveCompMap(mSticks.getSample(), stimObjIds.getSample(), labels.getSample(), generator.getGeneratorPngPath());
    }

    /**
     * Instead of just shallow copying the sample, we generate a new match stick from the sample
     * by generating from shapespec, this ensures we convert from the sample's coordinate system
     * to one appropiate for the match.
     * @param sample
     */
    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        ProceduralMatchStick match = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.moveCenterOfMassTo(new Point3d(0,0,0));


        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
    }

    protected void writeEStimSpec() {
        if (isEStimEnabled) {
            AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
            eStimObjData = new long[]{getStimId()};
            dbUtil.writeEStimObjData(eStimObjData[0], "EStimEnabled", "");
        } else {
            eStimObjData = new long[]{1L};
        }

    }


    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            correctNoiseRadius(proceduralDistractor);
            proceduralDistractor.setProperties(parameters.getSize(), parameters.textureType);
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewComponentMatchStick(sample, morphComponentIndex, parameters.morphMagnitude, 0.5, true, proceduralDistractor.maxAttempts);
            mSticks.addProceduralDistractor(proceduralDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(proceduralDistractor));
        }
    }

    /**
     * Because the procedural distractors are drawn zoomed in, we need to adjust the noise
     * radius for the checkInNoise to work properly. We basically just calculate the ratio
     * of the image dimensions in degrees and the specified size of the match stick, and
     * then multiply this ratio by the size of noiseRadius to scale it properly.
     * @param proceduralDistractor
     */
    protected void correctNoiseRadius(ProceduralMatchStick proceduralDistractor) {
        double scaleFactor = generator.getImageDimensionsDegrees() / RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource.getRFRadiusDegrees());
        proceduralDistractor.noiseRadiusMm = rfSource.getRFRadiusMm() * scaleFactor;
    }

    @Override
    protected void writeStimSpec(){
        RewardBehavior result = specifyRewardBehavior();
        NAFCStimSpecWriter stimSpecWriter = NAFCStimSpecWriter.createForEStim(
                this.getClass().getSimpleName(),
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds,
                eStimObjData,
                result.rewardPolicy, result.rewardList);

        stimSpecWriter.writeStimSpec();
    }

    @Override
    public RewardBehavior specifyRewardBehavior() {
        if (isEStimEnabled) {
            return RewardBehaviors.rewardAnyChoice();
        } else{
            return RewardBehaviors.rewardMatchOnly();
        }
    }

    /**
     * Different from super class in that there is separate image dimensions for sample and choices.
     * For the sample, we use the size specified in SystemVars
     * For the choices, we use size specified by RFUtils.calculateMStickMaxSizeDegrees
     * so that the size of choices are going to be approximately similar to the sample.
     */
    @Override
    protected void writeStimObjDataSpecs() {
        double imageSizeSample = generator.getImageDimensionsDegrees();
        ImageDimensions dimensionsSample = new ImageDimensions(imageSizeSample, imageSizeSample);

        double imageSizeChoices = RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource.getRFRadiusDegrees());
        ImageDimensions dimensionsChoices = new ImageDimensions(imageSizeChoices, imageSizeChoices);

        //Sample
        double xCenter = coords.getSample().getX();
        double yCenter = coords.getSample().getY();
        String path = experimentPngPaths.getSample();
        String noiseMapPath = experimentNoiseMapPath;
        Color color = parameters.color;
        double numNoiseFrames = parameters.noiseRate;
        NoisyPngSpec sampleSpec = new NoisyPngSpec(
                xCenter, yCenter,
                dimensionsSample,
                path,
                noiseMapPath,
                color,
                numNoiseFrames,
                parameters.noiseChance);
        MStickStimObjData sampleMStickObjData = new MStickStimObjData("sample", mStickSpecs.getSample());
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeStimObjData(stimObjIds.getSample(), sampleSpec.toXml(), sampleMStickObjData.toXml());

        //Match
        xCenter = coords.getMatch().getX();
        yCenter = coords.getMatch().getY();
        path = experimentPngPaths.getMatch();
        noiseMapPath = "";
        NoisyPngSpec matchSpec = new NoisyPngSpec(
                xCenter, yCenter,
                dimensionsChoices,
                path,
                noiseMapPath,
                color);
        MStickStimObjData matchMStickObjData = new MStickStimObjData("match", mStickSpecs.getMatch());
        dbUtil.writeStimObjData(stimObjIds.getMatch(), matchSpec.toXml(), matchMStickObjData.toXml());

        //Procedural Distractors
        for (int i = 0; i < numProceduralDistractors; i++) {
            xCenter = coords.getProceduralDistractors().get(i).getX();
            yCenter = coords.getProceduralDistractors().get(i).getY();
            path = experimentPngPaths.getProceduralDistractors().get(i);
            NoisyPngSpec proceduralDistractorSpec = new NoisyPngSpec(
                    xCenter, yCenter,
                    dimensionsChoices,
                    path,
                    noiseMapPath,
                    color);
            MStickStimObjData proceduralDistractorMStickObjData = new MStickStimObjData("procedural", mStickSpecs.getProceduralDistractors().get(i));
            dbUtil.writeStimObjData(stimObjIds.getProceduralDistractors().get(i), proceduralDistractorSpec.toXml(), proceduralDistractorMStickObjData.toXml());
        }

        //Rand Distractors
        for (int i = 0; i < numRandDistractors; i++) {
            xCenter = coords.getRandDistractors().get(i).getX();
            yCenter = coords.getRandDistractors().get(i).getY();
            path = experimentPngPaths.getRandDistractors().get(i);
            NoisyPngSpec randDistractorSpec = new NoisyPngSpec(
                    xCenter, yCenter,
                    dimensionsChoices,
                    path,
                    noiseMapPath,
                    color);
            MStickStimObjData randDistractorMStickObjData = new MStickStimObjData("rand", mStickSpecs.getRandDistractors().get(i));
            dbUtil.writeStimObjData(stimObjIds.getRandDistractors().get(i), randDistractorSpec.toXml(), randDistractorMStickObjData.toXml());
        }
    }
}