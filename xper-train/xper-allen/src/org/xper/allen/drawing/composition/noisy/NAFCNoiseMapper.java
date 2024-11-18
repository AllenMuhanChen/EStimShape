package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.util.List;

public interface NAFCNoiseMapper {

    /**
     * Return a path to an image for a noisemap. Pixel values of red determine percentage chance of noise.
     * @param mStick
     * @param amplitude
     * @param specialCompIndx
     * @param renderer
     * @param path
     * @return
     */
    public String mapNoise(ProceduralMatchStick mStick,
                    double amplitude,
                    List<Integer> specialCompIndx,
                    AbstractRenderer renderer,
                    String path);

    public void checkInNoise(ProceduralMatchStick mStick,
                             List<Integer> compsToNoise,
                             double percentRequiredOutsideNoise);
}