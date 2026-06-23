package org.xper.allen.drawing.composition.noisy;

import javax.vecmath.Point3d;

/**
 * Immutable noise-circle in a matchstick's (scaled) object/world frame: a center origin plus a
 * radius in mm. This is the unit that a whole trial group shares — one shape "owns"/computes it and
 * the rest inherit and validate against it (see InheritedNoiseCircleMapper).
 *
 * The origin matches the coordinate frame of the component vect_info (i.e. already scaled by
 * scaleForMAxisShape about the mass center), which is the same frame GaussianNoiseMapper stores in
 * ProceduralMatchStick.noiseOrigin.
 */
public class NoiseCircle {
    private final Point3d origin;
    private final double radiusMm;

    public NoiseCircle(Point3d origin, double radiusMm) {
        this.origin = new Point3d(origin);
        this.radiusMm = radiusMm;
    }

    /** Defensive copy so callers cannot mutate the stored origin. */
    public Point3d getOrigin() {
        return new Point3d(origin);
    }

    public double getRadiusMm() {
        return radiusMm;
    }

    @Override
    public String toString() {
        return "NoiseCircle{origin=" + origin + ", radiusMm=" + radiusMm + "}";
    }
}
