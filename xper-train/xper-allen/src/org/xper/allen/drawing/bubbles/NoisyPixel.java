package org.xper.allen.drawing.bubbles;

public class NoisyPixel {
    public final int x;
    public final int y;
    public final double noiseChance;

    public NoisyPixel(int x, int y, double noiseChance) {
        this.x = x;
        this.y = y;
        this.noiseChance = noiseChance;
    }
}