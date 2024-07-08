package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import java.awt.image.BufferedImage;

public interface NoiseMapper {
    BufferedImage mapNoise(ProceduralMatchStick mStick,
                           double amplitude,
                           int specialCompIndx, AbstractRenderer renderer);
}