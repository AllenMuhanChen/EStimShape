package org.xper.allen.drawing.ga;

public interface Thumbnailable {
    void drawThumbnail(double imageWidthMm, double imageHeightMm);

    /**
     * Like {@link #drawThumbnail}, but renders the component map (each component
     * in its distinct color) instead of the shaded skeleton, using the exact
     * same RF-centered zoom. The result is pixel-aligned with the thumbnail so
     * analysis code can overlay component identity onto the thumbnail.
     */
    void drawCompMapThumbnail(double imageWidthMm, double imageHeightMm);
}