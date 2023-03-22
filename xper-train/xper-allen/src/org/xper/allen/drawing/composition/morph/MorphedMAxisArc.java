package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusProfile;
import org.xper.drawing.stick.MAxisArc;

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

        // Morph Parameters
        Double newCurvature = morphParams.getCurvature(oldCurvature);
        Double newLength = morphParams.getLength(oldLength);
        Vector3d newTangent = morphParams.getOrientation(oldTangent);
        Double newRotation = morphParams.getRotation(oldRotation);

        // Create actual arc
        genArc(1.0/newCurvature, newLength);
        Point3d finalPos = new Point3d(arcToMorph.getmPts()[alignedPt]);
        transRotMAxis(alignedPt, finalPos, rotationCenter, newTangent, newRotation);
    }
}