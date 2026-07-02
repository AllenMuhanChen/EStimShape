package org.xper.allen.noisy;

import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import javax.imageio.ImageIO;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;

/**
 * A {@link NoisyTranslatableResizableImages} whose sample stimulus is a dynamic, per-pixel
 * mixture of two source shapes (e.g. a variant and a delta) at a chosen coherence, with the
 * existing dynamic noise overlaid on top.
 *
 * <p>Frame by frame the sample texture (slot 0) is replaced with a freshly drawn mixture, so the
 * dither re-randomises every frame; the noise overlay continues to be produced by the parent class
 * exactly as for normal trials. The actual mixing is delegated to {@link CoherenceImageCombiner} so
 * it can be unit tested without an OpenGL context.
 *
 * <p>Intended {@code NoisyNAFCPngScene} integration, replacing the normal sample path (choices are
 * loaded and drawn exactly as before):
 * <pre>
 *   trialStart: images = new CoherenceNoisyTranslatableImages(numFrames, numChoices + 1, noiseRate, numFrames);
 *   setSample:  images.loadCoherenceSample(firstPath, secondPath, coherence, color, seed);
 *               images.loadNoise(noiseMapPath, color);
 *   drawSample: images.drawCoherenceSample(true, context, sampleLocation, sampleDimensions);
 * </pre>
 *
 * @author Allen Chen
 */
public class CoherenceNoisyTranslatableImages extends NoisyTranslatableResizableImages {

    /** The sample always lives in texture slot 0, matching NoisyNAFCPngScene. */
    private static final int SAMPLE_TEXTURE_INDEX = 0;

    private final int numSampleFrames;
    private final List<byte[]> sampleFrames = new ArrayList<>();
    private int sampleWidth;
    private int sampleHeight;
    private int currentSampleFrameIndx = 0;

    /**
     * When true, 0% coherence is anchored on equal <i>visible foreground area</i> so a larger shape
     * is not over-represented; when false, 0% coherence is a plain 50/50 pixel coin. Set via
     * {@link #setNormalizeByArea} before {@link #loadCoherenceSample}.
     */
    private boolean normalizeByArea = true;

    /**
     * @param numNoiseFrames   number of pre-generated noise frames (as in the parent)
     * @param numImageTextures number of image texture slots (sample + choices), as in the parent
     * @param noiseRate        noise play rate (as in the parent)
     * @param numSampleFrames  number of distinct coherence frames to pre-generate for the sample;
     *                         these are cycled during presentation to give the dynamic dither
     */
    public CoherenceNoisyTranslatableImages(int numNoiseFrames, int numImageTextures,
                                            double noiseRate, int numSampleFrames) {
        super(numNoiseFrames, numImageTextures, noiseRate);
        this.numSampleFrames = Math.max(1, numSampleFrames);
    }

    /**
     * Pre-generate the dynamic coherence frames for the sample. Each frame is an independent
     * per-pixel mixture of the two images (see {@link CoherenceImageCombiner#combine}).
     *
     * <p>Like {@code loadTexture} for a normal sample, this must be called before {@link #loadNoise},
     * because it also establishes the sample's byte length / dimensions that the noise generator
     * relies on (it loads the first image into slot 0 as a side effect; that texture is harmlessly
     * overwritten each frame by {@link #drawCoherenceSample}).
     *
     * @param coherence  signed coherence in [-1, 1]: +1 == all first, -1 == all second, 0 == 0%
     *                   coherence. The 0% anchor is balanced by <i>visible foreground area</i>
     *                   (see {@link CoherenceImageCombiner#neutralProportionFirst}) so that a shape
     *                   with more non-background pixels is not over-represented.
     * @param noiseColor stimulus color (kept for symmetry with the noise overlay; not used here)
     * @param seed       base RNG seed; frame i uses {@code seed + i} so frames differ yet the
     *                   trial is reproducible
     */
    public void loadCoherenceSample(String firstPath, String secondPath, double coherence,
                                    Color noiseColor, long seed) {
        // Establishes slot 0, the source byte length and image dimensions via the parent loader.
        loadTexture(firstPath, SAMPLE_TEXTURE_INDEX);
        try {
            BufferedImage first = ImageIO.read(new File(firstPath));
            BufferedImage second = ImageIO.read(new File(secondPath));
            sampleWidth = first.getWidth();
            sampleHeight = first.getHeight();
            // Anchor 0% coherence on equal visible area rather than a plain 50/50 pixel coin,
            // unless normalization is disabled (then 0.5 is the original behaviour).
            double neutralProportion = normalizeByArea
                    ? CoherenceImageCombiner.neutralProportionFirst(first, second)
                    : 0.5;
            double proportionFirst = CoherenceImageCombiner.proportionForCoherence(coherence, neutralProportion);
            sampleFrames.clear();
            currentSampleFrameIndx = 0;
            for (int i = 0; i < numSampleFrames; i++) {
                BufferedImage mixed = CoherenceImageCombiner.combine(
                        first, second, proportionFirst, new SplittableRandom(seed + i));
                sampleFrames.add(argbToRgba(mixed));
            }
        } catch (IOException e) {
            throw new RuntimeException("Could not load coherence source images: "
                    + firstPath + ", " + secondPath, e);
        }
    }

    /**
     * Draw the next coherence frame into the sample slot, then defer to the parent to draw it plus
     * the (separately dynamic) noise overlay.
     */
    public void drawCoherenceSample(boolean drawNoise, Context context,
                                    Coordinates2D location, ImageDimensions dimensions) {
        if (!sampleFrames.isEmpty()) {
            uploadSampleFrame(sampleFrames.get(currentSampleFrameIndx));
            currentSampleFrameIndx = (currentSampleFrameIndx + 1) % sampleFrames.size();
        }
        draw(drawNoise, context, SAMPLE_TEXTURE_INDEX, location, dimensions);
    }

    private void uploadSampleFrame(byte[] rgba) {
        ByteBuffer pixels = (ByteBuffer) BufferUtils.createByteBuffer(rgba.length).put(rgba, 0, rgba.length).flip();
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, getTextureIds().get(SAMPLE_TEXTURE_INDEX));
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
        GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA8, sampleWidth, sampleHeight, 0,
                GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, pixels);
    }

    /** Convert a TYPE_INT_ARGB image into a tightly packed RGBA byte array for {@code glTexImage2D}. */
    private static byte[] argbToRgba(BufferedImage img) {
        int width = img.getWidth();
        int height = img.getHeight();
        byte[] out = new byte[width * height * 4];
        int idx = 0;
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int argb = img.getRGB(x, y);
                out[idx++] = (byte) ((argb >> 16) & 0xFF); // R
                out[idx++] = (byte) ((argb >> 8) & 0xFF);  // G
                out[idx++] = (byte) (argb & 0xFF);         // B
                out[idx++] = (byte) ((argb >>> 24) & 0xFF);// A
            }
        }
        return out;
    }

    public int getNumSampleFrames() {
        return numSampleFrames;
    }

    public boolean isNormalizeByArea() {
        return normalizeByArea;
    }

    public void setNormalizeByArea(boolean normalizeByArea) {
        this.normalizeByArea = normalizeByArea;
    }
}
