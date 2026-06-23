package org.xper.allen.drawing.composition;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Single source of truth for the flat colors used to draw a match stick's
 * "component map" (one unique color per component / limb).
 *
 * <p>The same palette is used in two places that must agree:
 * <ul>
 *   <li>{@code AllenMatchStick.drawSkeleton(true)} renders each component in its color.</li>
 *   <li>{@link LimbTextureCompositor} reads that rendered map back and uses these colors
 *       to decide which component owns each pixel.</li>
 * </ul>
 * Keeping the palette here prevents the two from drifting apart.
 *
 * <p>Colors are 1-indexed by component number to match the rest of the code base
 * (e.g. {@code getComp()[i]} with {@code i} starting at 1).
 */
public class CompMapColors {

    /**
     * Flat RGB colors (each channel 0..1) indexed by {@code componentNumber - 1}.
     * These are well separated in RGB space so that solid interior pixels classify
     * cleanly and only thin anti-aliased boundary pixels fall between colors.
     */
    public static final float[][] COLOR_CODE = {
            {1.0f, 1.0f, 1.0f},
            {1.0f, 0.0f, 0.0f},
            {0.0f, 1.0f, 0.0f},
            {0.0f, 0.0f, 1.0f},
            {0.0f, 1.0f, 1.0f},
            {1.0f, 0.0f, 1.0f},
            {1.0f, 1.0f, 0.0f},
            {0.4f, 0.1f, 0.6f}
    };

    /** Maximum number of components this palette can distinguish. */
    public static final int MAX_COMPONENTS = COLOR_CODE.length;

    /**
     * Returns the comp-map color for a single component.
     *
     * @param componentNumber 1-indexed component number
     */
    public static float[] colorFor(int componentNumber) {
        if (componentNumber < 1 || componentNumber > MAX_COMPONENTS) {
            throw new IllegalArgumentException(
                    "componentNumber must be in [1, " + MAX_COMPONENTS + "] but was " + componentNumber);
        }
        return COLOR_CODE[componentNumber - 1];
    }

    /**
     * Builds the palette map (component number -&gt; RGB color) for a shape with the
     * given number of components.
     *
     * @param nComponents number of active components in the shape
     * @return ordered map from 1-indexed component number to its [r,g,b] color (0..1)
     */
    public static Map<Integer, float[]> paletteFor(int nComponents) {
        if (nComponents < 0 || nComponents > MAX_COMPONENTS) {
            throw new IllegalArgumentException(
                    "nComponents must be in [0, " + MAX_COMPONENTS + "] but was " + nComponents);
        }
        Map<Integer, float[]> palette = new LinkedHashMap<>();
        for (int i = 1; i <= nComponents; i++) {
            palette.put(i, COLOR_CODE[i - 1]);
        }
        return palette;
    }
}
