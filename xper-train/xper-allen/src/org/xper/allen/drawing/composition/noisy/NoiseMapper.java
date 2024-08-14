package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.awt.image.BufferedImage;
import java.util.List;

public interface NoiseMapper {
    public String mapNoise(ProceduralMatchStick mStick,
                         double amplitude,
                         int specialCompIndx,
                         AbstractRenderer renderer,
                         String path) ;

    public String mapNoise(ProceduralMatchStick mStick,
                    double amplitude,
                    List<Integer> specialCompIndx,
                    AbstractRenderer renderer,
                    String path);

    public void checkInNoise(ProceduralMatchStick mStick,
                             List<Integer> compsToNoise,
                             double percentRequiredOutsideNoise);
}