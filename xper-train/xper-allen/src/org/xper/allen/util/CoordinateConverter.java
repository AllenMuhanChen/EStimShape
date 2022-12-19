package org.xper.allen.util;

import org.xper.allen.drawing.composition.AngularCoordinates;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.lang.Math;
import java.util.ArrayList;
import java.util.List;

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

    public static Vector3d sphericalToVector(SphericalCoordinates sc){
        double x = sc.r * Math.sin(sc.phi) * Math.cos(sc.theta);
        double y = sc.r * Math.sin(sc.phi) * Math.sin(sc.theta);
        double z = sc.r * Math.cos(sc.phi);

        return new Vector3d(x,y,z);
    }

    public static Point3d sphericalToPoint(SphericalCoordinates sc){
        double x = sc.r * Math.sin(sc.phi) * Math.cos(sc.theta);
        double y = sc.r * Math.sin(sc.phi) * Math.sin(sc.theta);
        double z = sc.r * Math.cos(sc.phi);

        return new Point3d(x,y,z);
    }


    public static List<Point3d> vectorToLine(Vector3d vector, int numPoints, Point3d start){
        List<Point3d> points = new ArrayList<>();

        // Calculate the points on the line
        for (int i = 0; i < numPoints; i++) {
            double t = (double) i / (numPoints - 1);

            Point3d end = new Point3d(start.x + vector.x, start.y + vector.y, start.z + vector.z);
            points.add(new Point3d(
                    (start.x) + t * (end.x - start.x),
                    start.y + t * (end.y - start.y),
                    start.z + t * (end.z - start.z))
            );
        }

        return points;
    }

}
