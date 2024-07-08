package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.awt.image.BufferedImage;

public interface NoiseMapper {
    public String mapNoise(ProceduralMatchStick mStick,
                         double amplitude,
                         int specialCompIndx,
                         AbstractRenderer renderer,
                         String path) ;
}