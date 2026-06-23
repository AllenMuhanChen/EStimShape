package org.xper.allen.nafc.blockgen.procedural;

/**
 * Block-level configuration for "split texture" NAFC trials, where the hypothesized
 * (tested) limb of a shape is rendered in a different texture than the rest of the body.
 *
 * <p>The discrimination is always the hypothesized limb's texture. Two textures are involved:
 * the shape's own authored texture {@code O} (SHADE or SPECULAR, read per-stim) and a
 * {@link #contrastTexture} {@code K} (default {@code "2D"}). Which one is the body vs. the
 * limb cue is controlled by {@link #inverted}:
 * <ul>
 *   <li>normal: body = {@code O}, hypothesized limb = {@code K}</li>
 *   <li>inverted: body = {@code K}, hypothesized limb = {@code O}</li>
 * </ul>
 *
 * <p>A "split" render draws the body in {@link #bodyTexture(String)} and the hypothesized
 * limb in {@link #splitLimbTexture(String)}; a "plain" render is uniform
 * {@link #bodyTexture(String)}. {@link #splitRenderIsSample} decides which of the
 * same-geometry pair carries the split cue: when {@code true} the sample &amp; match are
 * split and the same-shape texture-foil distractor is plain; when {@code false} it is
 * reversed. Other (different-geometry) distractors are always rendered plain.
 */
public class SplitTextureConfig {

    public static final String DEFAULT_CONTRAST_TEXTURE = "2D";

    private final String contrastTexture;
    private final boolean inverted;
    private final boolean splitRenderIsSample;

    public SplitTextureConfig(String contrastTexture, boolean inverted, boolean splitRenderIsSample) {
        this.contrastTexture = (contrastTexture == null || contrastTexture.isEmpty())
                ? DEFAULT_CONTRAST_TEXTURE : contrastTexture;
        this.inverted = inverted;
        this.splitRenderIsSample = splitRenderIsSample;
    }

    /** The body (background) texture given the shape's own authored texture {@code O}. */
    public String bodyTexture(String originalTexture) {
        return inverted ? contrastTexture : originalTexture;
    }

    /** The texture the hypothesized limb takes in a split render, given {@code O}. */
    public String splitLimbTexture(String originalTexture) {
        return inverted ? originalTexture : contrastTexture;
    }

    /** Sample and match always share a treatment; both are split iff this is true. */
    public boolean sampleIsSplit() {
        return splitRenderIsSample;
    }

    public boolean matchIsSplit() {
        return splitRenderIsSample;
    }

    /** The same-geometry texture-foil distractor carries the opposite treatment of the match. */
    public boolean foilIsSplit() {
        return !splitRenderIsSample;
    }

    public String getContrastTexture() {
        return contrastTexture;
    }

    public boolean isInverted() {
        return inverted;
    }

    public boolean isSplitRenderIsSample() {
        return splitRenderIsSample;
    }

    @Override
    public String toString() {
        return "SplitTextureConfig{contrast=" + contrastTexture
                + ", inverted=" + inverted
                + ", splitRenderIsSample=" + splitRenderIsSample + "}";
    }
}
