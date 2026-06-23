package org.xper.allen.drawing.composition;

import java.awt.image.BufferedImage;
import java.util.Map;
import java.util.Set;

/**
 * Combines two full renders of the <em>same</em> match stick (identical pose) into a single
 * image in which a chosen subset of components is shown in a "secondary" texture and every
 * other component in a "primary" texture. This is how we build a part-shade / part-2D shape:
 * render the whole shape once all-SHADE, once all-2D, then keep the 2D pixels only for the
 * limbs we want.
 *
 * <p>Inputs:
 * <ul>
 *   <li>{@code primary} – the whole shape rendered in the base texture (e.g. SHADE).</li>
 *   <li>{@code secondary} – the whole shape rendered in the overlay texture (e.g. 2D).</li>
 *   <li>{@code compMap} – the component-ID map: the whole shape with each component drawn in
 *       a unique flat color (see {@link CompMapColors}). This identifies which limb owns
 *       each pixel.</li>
 * </ul>
 *
 * <p>For each pixel we find the component whose comp-map color is nearest. If that component
 * is in {@code secondaryComponents} (and the match is confident, i.e. within
 * {@code matchThreshold}), the pixel is taken from {@code secondary}; otherwise from
 * {@code primary}. Defaulting to {@code primary} means anti-aliased silhouette and
 * limb-boundary pixels — where the comp-map color is a blend of two palette colors or of a
 * palette color and the background — fall back to the base texture rather than punching
 * holes. Because {@code primary} already contains the correct background and the full
 * anti-aliased silhouette, no separate background handling is needed.
 *
 * <p>Since {@code primary} and {@code secondary} share geometry, pose and depth-resolved
 * occlusion, the composite is seamless and occlusion-correct without any depth math here.
 *
 * <p>This class is pure (no OpenGL, only {@link BufferedImage}) and is therefore directly
 * unit-testable.
 */
public class LimbTextureCompositor {

    /**
     * Default maximum Euclidean RGB distance (channels 0..255) for a comp-map pixel to be
     * treated as a confident match to a palette color. The palette
     * ({@link CompMapColors#COLOR_CODE}) is well separated — the closest distinct solid
     * colors are 255 apart — so a midpoint blend sits ~128–180 from either color. A
     * threshold of 100 accepts solid interior pixels and rejects boundary blends.
     */
    public static final double DEFAULT_MATCH_THRESHOLD = 100.0;

    private final double matchThreshold;

    public LimbTextureCompositor() {
        this(DEFAULT_MATCH_THRESHOLD);
    }

    public LimbTextureCompositor(double matchThreshold) {
        this.matchThreshold = matchThreshold;
    }

    /**
     * Composites {@code primary} and {@code secondary} using {@code compMap} to decide, per
     * pixel, which source to draw from.
     *
     * @param primary             whole shape in the base texture
     * @param secondary           whole shape in the overlay texture
     * @param compMap             component-ID map (each component a unique flat color)
     * @param componentColors     1-indexed component number -&gt; its comp-map [r,g,b] (0..1),
     *                            typically {@link CompMapColors#paletteFor(int)}
     * @param secondaryComponents 1-indexed component numbers to draw from {@code secondary}
     * @return a new ARGB image the same size as the inputs
     */
    public BufferedImage compose(BufferedImage primary,
                                 BufferedImage secondary,
                                 BufferedImage compMap,
                                 Map<Integer, float[]> componentColors,
                                 Set<Integer> secondaryComponents) {
        requireSameSize(primary, secondary, "primary", "secondary");
        requireSameSize(primary, compMap, "primary", "compMap");

        int width = primary.getWidth();
        int height = primary.getHeight();

        // Flatten the palette into parallel arrays for a tight inner loop.
        int n = componentColors.size();
        int[] paletteComponent = new int[n];
        int[][] paletteRgb = new int[n][3];
        int idx = 0;
        for (Map.Entry<Integer, float[]> e : componentColors.entrySet()) {
            paletteComponent[idx] = e.getKey();
            float[] c = e.getValue();
            paletteRgb[idx][0] = to255(c[0]);
            paletteRgb[idx][1] = to255(c[1]);
            paletteRgb[idx][2] = to255(c[2]);
            idx++;
        }

        double thresholdSquared = matchThreshold * matchThreshold;

        BufferedImage out = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int owner = nearestComponentWithinThreshold(
                        compMap.getRGB(x, y), paletteComponent, paletteRgb, thresholdSquared);
                boolean useSecondary = owner != -1 && secondaryComponents.contains(owner);
                out.setRGB(x, y, (useSecondary ? secondary : primary).getRGB(x, y));
            }
        }
        return out;
    }

    /**
     * Returns the 1-indexed component number whose palette color is nearest to {@code argb},
     * or {@code -1} if the nearest is farther than the match threshold (anti-aliased blend,
     * background, etc.).
     */
    private int nearestComponentWithinThreshold(int argb, int[] paletteComponent,
                                                int[][] paletteRgb, double thresholdSquared) {
        int r = (argb >> 16) & 0xFF;
        int g = (argb >> 8) & 0xFF;
        int b = argb & 0xFF;

        int bestComponent = -1;
        double bestDistSquared = Double.MAX_VALUE;
        for (int i = 0; i < paletteComponent.length; i++) {
            int dr = r - paletteRgb[i][0];
            int dg = g - paletteRgb[i][1];
            int db = b - paletteRgb[i][2];
            double distSquared = dr * dr + dg * dg + db * db;
            if (distSquared < bestDistSquared) {
                bestDistSquared = distSquared;
                bestComponent = paletteComponent[i];
            }
        }
        return bestDistSquared <= thresholdSquared ? bestComponent : -1;
    }

    private static int to255(float channel) {
        int v = Math.round(channel * 255f);
        if (v < 0) return 0;
        if (v > 255) return 255;
        return v;
    }

    private static void requireSameSize(BufferedImage a, BufferedImage b, String nameA, String nameB) {
        if (a.getWidth() != b.getWidth() || a.getHeight() != b.getHeight()) {
            throw new IllegalArgumentException(String.format(
                    "%s (%dx%d) and %s (%dx%d) must have the same dimensions",
                    nameA, a.getWidth(), a.getHeight(), nameB, b.getWidth(), b.getHeight()));
        }
    }
}
