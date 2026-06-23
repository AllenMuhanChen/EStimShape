package org.xper.allen.drawing.composition.noisy;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.experiment.NoiseException;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;

import javax.vecmath.Point3d;
import java.util.List;

/**
 * A {@link NAFCNoiseMapper} that does NOT compute or optimize a noise circle. It is handed a fixed
 * {@link NoiseCircle} (inherited from whichever shape "owns" the circle for a trial group) and only:
 *   - applies that circle to a shape (sets noiseOrigin + noiseRadiusMm so rendering uses it), and
 *   - in checkInNoise, VALIDATES that the shape fits the fixed circle (to-hide comp inside, rest
 *     outside), throwing a NoiseException if it does not so the caller's existing retry loop can
 *     regenerate or fail.
 *
 * This is what enforces that every member of a trial group (sample, matches, distractors, deltas)
 * shares one identical circle, which removes noise position/size as a cue the animal could exploit.
 *
 * Width/height/background for rendering are configured the same way as on GaussianNoiseMapper
 * (setWidth/setHeight/setBackground).
 */
public class InheritedNoiseCircleMapper extends GaussianNoiseMapper {

    private final NoiseCircle circle;

    public InheritedNoiseCircleMapper(NoiseCircle circle) {
        this.circle = circle;
    }

    public NoiseCircle getCircle() {
        return circle;
    }

    /** Pin the shape to the inherited circle so both validation and rendering use it. */
    private void applyCircle(ProceduralMatchStick mStick) {
        mStick.noiseRadiusMm = circle.getRadiusMm();
        mStick.setNoiseOrigin(circle.getOrigin());
    }

    @Override
    public void checkInNoise(ProceduralMatchStick mStick, List<Integer> mustBeInNoiseCompIds, double percentRequiredOutsideNoise) throws NoiseException {
        applyCircle(mStick);
        Point3d origin = circle.getOrigin();
        double radius = circle.getRadiusMm();

        double inside = fractionInside(mStick, mustBeInNoiseCompIds, origin, radius);
        double outside = fractionOutside(mStick, mustBeInNoiseCompIds, origin, radius);

        if (isDebugMode()) {
            System.out.println("[INHERITED NOISE] (suppressed) inside=" + inside + " outside=" + outside + " " + circle);
            return;
        }
        if (inside < getPercentRequiredInside()) {
            throw new NoiseException("Shape does not fit inherited noise circle: " + inside
                    + " of the to-hide component is inside (need " + getPercentRequiredInside() + "), " + circle);
        }
        if (outside < percentRequiredOutsideNoise) {
            throw new NoiseException("Inherited noise circle covers too much of the shape: " + outside
                    + " of the rest is outside (need " + percentRequiredOutsideNoise + "), " + circle);
        }
    }

    @Override
    public String mapNoise(ProceduralMatchStick mStick, double amplitude, List<Integer> specialCompIndx,
                           AbstractRenderer renderer, String path) {
        applyCircle(mStick);
        return super.mapNoise(mStick, amplitude, specialCompIndx, renderer, path);
    }
}
