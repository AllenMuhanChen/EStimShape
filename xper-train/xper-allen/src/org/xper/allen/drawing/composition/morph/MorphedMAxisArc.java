package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

public class MorphedMAxisArc extends AllenMAxisArc {

    public MorphedMAxisArc(AllenMAxisArc arc) {
        super();
        copyFrom(arc);
    }

    public MorphedMAxisArc() {
        super();
    }

    public void genMorphedArc(MorphedMAxisArc arcToMorph, int alignedPt, ComponentMorphParameters morphParams) {
        int rotationCenter = arcToMorph.getTransRotHis_rotCenter();

        // Find Old Values
        double oldCurvature = arcToMorph.getCurvature();
        double oldLength = arcToMorph.getArcLen();
        Vector3d oldTangent = new Vector3d(arcToMorph.getmTangent()[rotationCenter]);
        double oldRotation = arcToMorph.getTransRotHis_devAngle();

        Double newCurvature = morphParams.morphCurvature(oldCurvature);
        Double newRotation = morphParams.morphRotation(oldRotation);
//        // Morph Parameters
//        Double newRotation;
//        Double newCurvature = morphParams.morphCurvature(oldCurvature);
//        if (CurvatureMorpher.isCurvatureLow(oldCurvature)) {
//            newRotation = morphParams.morphRotation(oldRotation);
//        } else {
//            morphParams.redistributeRotationMagntiude();
//            newRotation = morphParams.morphRotation(oldRotation);
//        }
        Double newLength = morphParams.morphLength(oldLength);
        Vector3d newTangent = morphParams.morphOrientation(oldTangent);

        // Create actual arc
        genArc(1.0/newCurvature, newLength);
        setBranchPt(arcToMorph.getBranchPt());
        Point3d finalPos = new Point3d(arcToMorph.getmPts()[alignedPt]);
        transRotMAxis(alignedPt, finalPos, rotationCenter, newTangent, newRotation);
    }
}