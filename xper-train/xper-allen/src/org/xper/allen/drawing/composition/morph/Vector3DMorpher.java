package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AngularCoordinates;
import org.xper.allen.util.CoordinateConverter;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Vector3d;
import java.util.Random;

public class Vector3DMorpher {

    private double maxRotationRadians = Math.PI;

    public Vector3DMorpher() {
    }

    public Vector3DMorpher(double maxRotationRadians) {
        this.maxRotationRadians = maxRotationRadians;
    }

    public Vector3d morphVector(Vector3d oldVector, double magnitude){
        // Determine the final angle (shortest) between the oldVector and newVector
        double totalRotation = magnitude * maxRotationRadians; // 180-degree rotation when rotationFactor = 1

        // Generate Random Rotation Axis That is Orthogonal to the OldVector
        Vector3d randomRotationAxis = new Vector3d();
        while (true) {
            Random rand = new Random();
            double axisTheta = rand.nextDouble() * 2 * Math.PI;
            double axisPhi = rand.nextDouble() * Math.PI;
            randomRotationAxis = CoordinateConverter.sphericalToVector(1, new AngularCoordinates(axisTheta, axisPhi));
            if (!isParallel(oldVector, randomRotationAxis)) {
                break;
            }
        }
        randomRotationAxis.cross(randomRotationAxis, oldVector);

        // Rotate oldVector around randomRotationAxis by totalRotation
        AxisAngle4d rotationAxisInfo = new AxisAngle4d(randomRotationAxis, totalRotation);
        Transform3D rotation = new Transform3D();
        rotation.setRotation(rotationAxisInfo);
        Vector3d newVector = new Vector3d(oldVector);
        rotation.transform(newVector);

        return newVector;
    }

    private boolean isParallel(Vector3d vector1, Vector3d vector2) {
        return vector2.angle(vector1) == 0 || vector2.angle(vector1) == Math.PI;
    }
}