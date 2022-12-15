package org.xper.allen.util;

import org.xper.allen.drawing.composition.AngularCoordinates;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.lang.Math;

public class CoordinateConverter {

    public static class SphericalCoordinates {
        public double r;
        public double theta;
        public double phi;

        public SphericalCoordinates(double r, double theta, double phi) {
            this.r = r;
            this.theta = theta;
            this.phi = phi;
        }

        public SphericalCoordinates(double r, AngularCoordinates angularCoordinates){
            this.r = r;
            this.theta = angularCoordinates.theta;
            this.phi = angularCoordinates.phi;
        }

        public AngularCoordinates getAngularCoordinates(){
            return new AngularCoordinates(theta, phi);
        }
    }

    public static SphericalCoordinates cartesianToSpherical(double x, double y, double z) {
        double r = Math.sqrt(x * x + y * y + z * z);
        double theta = Math.atan2(y, x);
        double phi = Math.acos(z / r);

        return new SphericalCoordinates(r, theta, phi);
    }

    public static SphericalCoordinates cartesianToSpherical(Point3d point){
        return cartesianToSpherical(point.x, point.y, point.z);
    }

    public static SphericalCoordinates cartesianToSpherical(Vector3d vector){
        return cartesianToSpherical(vector.x, vector.y, vector.z);
    }

}
