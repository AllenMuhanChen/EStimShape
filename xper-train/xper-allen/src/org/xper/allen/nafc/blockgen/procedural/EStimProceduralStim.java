package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.util.AllenDbUtil;

import javax.vecmath.Point3d;
import java.util.LinkedList;
import java.util.List;

public class EStimProceduralStim extends ProceduralStim{
    private final ReceptiveFieldSource rfSource;

    public EStimProceduralStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, int noiseComponentIndex) {
        super(generator, parameters, baseMatchStick, morphComponentIndex);
        this.rfSource = generator.getRfSource();
    }

    @Override
    public void writeStim() {
        writeStimObjDataSpecs();
        assignTaskId();
        writeStimSpec();
        writeEStimSpec();
    }

    @Override
    public void preWrite(){
        super.preWrite();
        generateSampleCompMap();
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            try {
                EStimShapeProceduralMatchStick sample = generateSample();

                noiseComponentIndex = sample.getDrivingComponent();

                generateMatch(sample);

                generateProceduralDistractors(sample);

                generateRandDistractors();

                break;
            } catch (ProceduralMatchStick.MorphRepetitionException e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
            }
        }
    }

    @Override
    protected EStimShapeProceduralMatchStick generateSample() {

        //Generate Sample
        EStimShapeProceduralMatchStick sample = new EStimShapeProceduralMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                ((EStimExperimentTrialGenerator) generator).getRF()
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimExperimentTrialGenerator) generator).getRfSource()), parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, morphComponentIndex, 0);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
        return sample;

    }

    private void generateSampleCompMap() {
        List<String> labels = new LinkedList<>();
        generator.getPngMaker().createAndSaveCompMap(mSticks.getSample(), stimObjIds.getSample(), labels, generator.getGeneratorPngPath());
    }

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        //Generate Match
        ProceduralMatchStick match = new ProceduralMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.moveCenterOfMassTo(new Point3d(0,0,0));


        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match, stimObjIds.getMatch()));
    }

    protected void writeEStimSpec() {
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeEStimObjData(getStimId(), "EStimEnabled", "");
    }

    @Override
    protected void writeStimSpec(){
        // Only reward for choosing the correct, or procedural distractor, not a random distractor.
        int numProceduralDistractors = this.parameters.numChoices - this.parameters.numRandDistractors - 1;
        int[] rewardList = new int[numProceduralDistractors + 1];
        rewardList[0] = 0; //match
        for (int i = 1; i <= numProceduralDistractors; i++) { //procedural distractors
            rewardList[i] = i;
        }

        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds, RewardPolicy.LIST, rewardList);

        stimSpecWriter.writeStimSpec();
    }
}