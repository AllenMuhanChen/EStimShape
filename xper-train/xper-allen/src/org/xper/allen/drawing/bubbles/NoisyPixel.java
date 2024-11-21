package org.xper.allen.drawing.bubbles;

import java.util.Objects;

public class NoisyPixel {
    public final int x;
    public final int y;
    public final double noiseChance;

    public NoisyPixel(int x, int y, double noiseChance) {
        this.x = x;
        this.y = y;
        this.noiseChance = noiseChance;
    }

    public PixelLocation getPixelLocation(){
        return new PixelLocation(x, y);
    }

    public double getNoiseChance(){
        return noiseChance;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof NoisyPixel)) return false;
        NoisyPixel that = (NoisyPixel) o;
        return x == that.x && y == that.y && Double.compare(getNoiseChance(), that.getNoiseChance()) == 0;
    }

    @Override
    public int hashCode() {
        return Objects.hash(x, y, getNoiseChance());
    }
}