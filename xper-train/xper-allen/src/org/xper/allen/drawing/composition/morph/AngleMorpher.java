package org.xper.allen.drawing.composition.morph;

import java.util.Random;

public class AngleMorpher {
    public Double morphAngle(Double oldRotation, Double rotationMagnitude) {
        double angleToRotate = rotationMagnitude * Math.PI;
        Random rand = new Random();

        if (rand.nextBoolean()) {
            return oldRotation + angleToRotate;
        } else {
            return oldRotation - angleToRotate;
        }
    }
}