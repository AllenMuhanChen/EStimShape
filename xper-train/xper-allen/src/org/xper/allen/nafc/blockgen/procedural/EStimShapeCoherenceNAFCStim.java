package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.rfplot.drawing.png.ImageDimensions;

import java.awt.Color;
import java.util.Arrays;

/**
 * Coherence trial: at runtime the sample is presented as a per-pixel mixture of the variant and one
 * of its included deltas (the "second sample"), under a shared noise map.
 *
 * <p>It is built as a variant-role variant/delta trial (so the choice set is identical to
 * {@link EStimShapeVariantsDeltaNAFCStim}'s variant trial: match = variant, distractors = the
 * included deltas). On top of that it renders the mixed delta as an extra {@code StimObjData} and
 * tags the {@code NAFCStimSpecSpec} with {@code secondSampleObjData} + {@code coherence}, which the
 * runtime ({@code CoherenceNAFCExperimentTask} / {@code NoisyNAFCPngScene}) uses to mix them.
 *
 * <p>The {@code stimType} written for this trial is this class's simple name, which must equal
 * {@code CoherenceNAFCExperimentTask.STIM_TYPE} for the runtime to recognise it.
 *
 * @author Allen Chen
 */
public class EStimShapeCoherenceNAFCStim extends EStimShapeVariantsDeltaNAFCStim {

    /** Signed coherence in [-1, 1]; 0 = balanced (0% coherence). */
    protected final double coherence;
    /** GA spec id of the delta mixed into the sample (one of the variant's included deltas). */
    protected final Long secondSampleStimSpecId;

    /** DB StimObjData id, mStick, spec and rendered png path for the delta second sample. */
    protected Long secondSampleStimObjId;
    protected ProceduralMatchStick secondSampleMStick;
    protected AllenMStickSpec secondSampleMStickSpec;
    protected String secondSampleExperimentPngPath;

    public EStimShapeCoherenceNAFCStim(EStimShapeExperimentTrialGenerator generator,
                                       ProceduralStimParameters parameters, Long variantId,
                                       boolean isEStimEnabled, Long eStimSpecId, double coherence) {
        // Variant-role trial: sample is the variant, choices are the variant + its included deltas.
        super(generator, parameters, variantId, false, isEStimEnabled, eStimSpecId);
        this.coherence = coherence;
        // Mix with the hypothesized delta (index 0 of the included deltas), which is also a choice.
        this.secondSampleStimSpecId = distractorMStickStimSpecIds.get(0);
    }

    @Override
    protected void assignStimObjIds() {
        super.assignStimObjIds();
        // Allocate the second-sample id just past the contiguous block super reserved.
        long maxId = Math.max(stimObjIds.getSample(), stimObjIds.getMatch());
        for (Long id : stimObjIds.getAllDistractors()) {
            maxId = Math.max(maxId, id);
        }
        secondSampleStimObjId = maxId + 1;
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        ProceduralMatchStick sample = super.generateSample(); // variant sample (sets mSticks.sample)
        generateSecondSample();                               // delta, aligned to the variant
        return sample;
    }

    /**
     * Generate the delta second sample at the same size / RF / noise positioning as the variant
     * sample (mirrors {@link EStimShapeVariantsNAFCStim#generateSample()}) so the two render aligned
     * and can be mixed pixel-for-pixel at runtime.
     */
    protected void generateSecondSample() {
        AllenMStickSpec baseStickSpec = new AllenMStickSpec();
        PruningMatchStick base = new PruningMatchStick(noiseMapper);
        base.setProperties(sampleSize, texture, is2D(), 1.0);
        base.setStimColor(color);
        base.genMatchStickFromFile(gaSpecPath + "/" + secondSampleStimSpecId + "_spec.xml");
        baseStickSpec.setMStickInfo(base, false);

        PruningMatchStick second = new PruningMatchStick(noiseMapper);
        second.setProperties(sampleSize, texture, is2D(), 1.0);
        second.setStimColor(color);
        second.setRf(rfSource.getReceptiveField());
        second.genMatchStickFromShapeSpec(baseStickSpec, new double[]{0, 0, 0});
        noiseMapper.checkInNoise(second, noiseComponentIndcs, 0.25);

        secondSampleMStick = second;
        secondSampleMStickSpec = mStickToSpec(second);
    }

    @Override
    protected void drawPNGs() {
        // Mirror EStimShapeProceduralStim.drawPNGs, adding the second-sample render inside the sample window.
        String generatorPngPath = generator.getGeneratorPngPath();

        samplePngMaker.createDrawerWindow();
        drawSample(samplePngMaker, generatorPngPath);
        drawSecondSample(samplePngMaker, generatorPngPath);
        generateNoiseMap();
        generateSampleCompMap();
        samplePngMaker.close();

        choicePNGMaker.createDrawerWindow();
        drawMatch(choicePNGMaker, generatorPngPath);
        drawProceduralDistractors(choicePNGMaker, generatorPngPath);
        drawRandDistractors(choicePNGMaker, generatorPngPath);
        choicePNGMaker.close();
    }

    protected void drawSecondSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        String path = pngMaker.createAndSavePNG(
                secondSampleMStick, secondSampleStimObjId,
                Arrays.asList("second_sample"), generatorPngPath);
        secondSampleExperimentPngPath = generator.convertPngPathToExperiment(path);
    }

    @Override
    protected void writeStimObjDataSpecs() {
        super.writeStimObjDataSpecs(); // variant sample + choices

        // Second sample (delta): same on-screen geometry and shared noise map as the variant sample,
        // placed at the sample coordinate so the runtime overlays/mixes them pixel-for-pixel.
        double imageSizeSample = maxSampleSize;
        ImageDimensions dims = new ImageDimensions(imageSizeSample, imageSizeSample);
        double xCenter = coords.getSample().getX();
        double yCenter = coords.getSample().getY();
        Color awtColor = new Color((int) (color.getRed() * 255), (int) (color.getGreen() * 255), (int) (color.getBlue() * 255));

        NoisyPngSpec secondSpec = new NoisyPngSpec(
                xCenter, yCenter, dims,
                secondSampleExperimentPngPath,
                experimentNoiseMapPath,
                awtColor,
                parameters.noiseRate,
                parameters.noiseChance);
        MStickStimObjData secondData = new MStickStimObjData("second_sample", secondSampleMStickSpec);
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeStimObjData(secondSampleStimObjId, secondSpec.toXml(), secondData.toXml());
    }

    @Override
    protected void writeStimSpec() {
        RewardBehavior result = specifyRewardBehavior();
        NAFCStimSpecWriter writer = NAFCStimSpecWriter.createForEStim(
                this.getClass().getSimpleName(),
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds,
                eStimObjData,
                result.rewardPolicy, result.rewardList,
                parameters.getSampleDuration());
        writer.setCoherenceData(secondSampleStimObjId, coherence);
        writer.writeStimSpec();
    }

    @Override
    public RewardBehavior specifyRewardBehavior() {
        // Reward both shapes that compose the sample: the variant (match, index 0) and the mixed
        // delta. The mixed delta sits at the first delta choice slot, after the optional removed slot.
        int mixedDeltaChoiceIndex = 1 + (includeRemovedChoice ? 1 : 0);
        return RewardBehaviors.rewardChoices(0, mixedDeltaChoiceIndex);
    }
}
