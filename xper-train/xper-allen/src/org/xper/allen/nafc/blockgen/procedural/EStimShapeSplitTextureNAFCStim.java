package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.drawing.RGBColor;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;

/**
 * A variant/delta NAFC trial in which the hypothesized limb is rendered in a contrasting texture
 * (see {@link SplitTextureConfig}). This is its own {@link org.xper.allen.nafc.NAFCStim} class —
 * distinct from {@link EStimShapeVariantsDeltaNAFCStim} — so it is identifiable by {@code stimType}
 * in the database for analysis.
 *
 * <p>It reuses all of {@link EStimShapeVariantsDeltaNAFCStim}'s trial assembly (variant vs. delta
 * sample/choice selection) and only changes the rendering:
 * <ul>
 *   <li>The sample and match render with the same treatment; whether that is the split (part-2D)
 *       or plain (uniform body) render is decided by {@link SplitTextureConfig#splitRenderIsSample}.</li>
 *   <li>A same-geometry "texture-foil" distractor (the match shape with the opposite treatment)
 *       occupies one reserved procedural slot.</li>
 *   <li>All other distractors render plainly in the body texture.</li>
 * </ul>
 *
 * <p>When a portion is rendered in 2D, it uses the shape's underlying average RGB (computed on the
 * fly from its 3D render) so the flat 2D fill matches the luminance of the shaded version — the
 * same convention the GA pipeline uses for 2D stimuli.
 */
public class EStimShapeSplitTextureNAFCStim extends EStimShapeVariantsDeltaNAFCStim {

    private final SplitTextureConfig splitTextureConfig;

    public EStimShapeSplitTextureNAFCStim(EStimShapeExperimentTrialGenerator generator,
                                          ProceduralStimParameters parameters, Long variantId, boolean isDelta,
                                          boolean isEStimEnabled, Long eStimSpecId, SplitTextureConfig splitTextureConfig) {
        super(generator, parameters, variantId, isDelta, isEStimEnabled, eStimSpecId);
        this.splitTextureConfig = splitTextureConfig;
    }

    public EStimShapeSplitTextureNAFCStim(EStimShapeExperimentTrialGenerator generator,
                                          ProceduralStimParameters parameters, Long variantId, Long sampleDeltaId,
                                          boolean isEStimEnabled, Long eStimSpecId, SplitTextureConfig splitTextureConfig) {
        super(generator, parameters, variantId, sampleDeltaId, isEStimEnabled, eStimSpecId);
        this.splitTextureConfig = splitTextureConfig;
    }

    @Override
    protected int numReservedProceduralSlots() {
        return 1; // the texture foil
    }

    @Override
    protected void injectReservedProceduralDistractors() {
        // Generation should have produced exactly one fewer regular procedural distractor to leave
        // room for the foil. If not, the choice budget (numChoices/numRandDistractors/includeRemovedChoice)
        // left no slot for it — fail loudly rather than desync the parallel id/label/coord lists.
        int expectedRegular = numProceduralDistractors - numReservedProceduralSlots();
        int actualRegular = mSticks.getProceduralDistractors().size();
        if (actualRegular != expectedRegular) {
            throw new IllegalStateException("Split-texture trial has no room for the texture-foil distractor: "
                    + "expected " + expectedRegular + " regular procedural distractor(s) before the foil but found "
                    + actualRegular + " (numProceduralDistractors=" + numProceduralDistractors + "). "
                    + "Increase numChoices, reduce numRandDistractors, or disable includeRemovedChoice.");
        }
        // The foil is the same geometry/spec as the match, rendered with the opposite treatment.
        mSticks.addProceduralDistractor(mSticks.getMatch());
        mStickSpecs.addProceduralDistractor(mStickSpecs.getMatch());
    }

    @Override
    protected void appendReservedProceduralLabels() {
        labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("textureFoil")));
    }

    @Override
    protected void drawSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        String samplePath = renderSplit(pngMaker, mSticks.getSample(), stimObjIds.getSample(),
                labels.getSample(), generatorPngPath, splitTextureConfig.sampleIsSplit());
        System.out.println("Sample Path: " + samplePath);
        experimentPngPaths.setSample(generator.convertPngPathToExperiment(samplePath));
    }

    @Override
    protected void drawMatch(AllenPNGMaker pngMaker, String generatorPngPath) {
        String matchPath = renderSplit(pngMaker, mSticks.getMatch(), stimObjIds.getMatch(),
                labels.getMatch(), generatorPngPath, splitTextureConfig.matchIsSplit());
        experimentPngPaths.setMatch(generator.convertPngPathToExperiment(matchPath));
        System.out.println("Match Path: " + matchPath);
    }

    @Override
    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        int foilIndex = numProceduralDistractors - 1; // the reserved foil slot is last
        for (int i = 0; i < numProceduralDistractors; i++) {
            boolean split = (i == foilIndex) && splitTextureConfig.foilIsSplit();
            String path = renderSplit(pngMaker, mSticks.getProceduralDistractors().get(i),
                    stimObjIds.getProceduralDistractors().get(i), labels.getProceduralDistractors().get(i),
                    generatorPngPath, split);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(path));
            System.out.println("Procedural Distractor Path: " + path);
        }
    }

    @Override
    protected void drawRandDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        for (int i = 0; i < numRandDistractors; i++) {
            String path = renderSplit(pngMaker, mSticks.getRandDistractors().get(i),
                    stimObjIds.getRandDistractors().get(i), labels.getRandDistractors().get(i),
                    generatorPngPath, false);
            experimentPngPaths.addRandDistractor(generator.convertPngPathToExperiment(path));
            System.out.println("Rand Distractor Path: " + path);
        }
    }

    /**
     * Renders one shape: a {@code split} render draws the body in the body texture and the
     * hypothesized limb in the contrast texture; a plain render is uniform body texture. Any
     * portion drawn in 2D uses the shape's underlying average RGB so its flat fill is luminance
     * matched.
     */
    protected String renderSplit(AllenPNGMaker pngMaker, ProceduralMatchStick mStick, Long stimObjId,
                                 List<String> labels, String generatorPngPath, boolean split) {
        String body = splitTextureConfig.bodyTexture(getTexture());
        if (split) {
            String limb = splitTextureConfig.splitLimbTexture(getTexture());
            RGBColor baseColor = is2D(body) ? underlyingAverageRGB(pngMaker, mStick) : null;
            RGBColor partColor = is2D(limb) ? underlyingAverageRGB(pngMaker, mStick) : null;
            return pngMaker.createAndSavePartTexturePNG(mStick, stimObjId, labels, generatorPngPath,
                    body, limb, new HashSet<>(morphComponentIndcs), baseColor, partColor);
        }
        // Plain render, uniform body texture.
        RGBColor bodyColor = is2D(body) ? underlyingAverageRGB(pngMaker, mStick) : null;
        String previousTexture = mStick.getTextureType();
        RGBColor previousColor = mStick.getStimColor();
        mStick.setTextureType(body);
        if (bodyColor != null) {
            mStick.setStimColor(bodyColor);
        }
        String path = pngMaker.createAndSavePNG(mStick, stimObjId, labels, generatorPngPath);
        mStick.setTextureType(previousTexture);
        mStick.setStimColor(previousColor);
        return path;
    }

    private static boolean is2D(String texture) {
        return "2D".equals(texture);
    }

    /**
     * The shape's luminance-matched flat color: the average RGB of its 3D (underlying-texture)
     * render. Falls back to the shape's current color if no underlying texture is set.
     */
    private RGBColor underlyingAverageRGB(AllenPNGMaker pngMaker, ProceduralMatchStick mStick) {
        if (mStick.getUnderlyingTexture() == null) {
            return mStick.getStimColor();
        }
        return pngMaker.getWindow().calculateAverageRGB(mStick);
    }

    public SplitTextureConfig getSplitTextureConfig() {
        return splitTextureConfig;
    }
}
