package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.List;

import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorph;

public class CurvatureRotationQualitativeMorph extends QualitativeMorph{
	private boolean curvatureFlag;
	private boolean rotationFlag;
	
	private double oldCurvature;
	private double oldRotation;
	
	private double newCurvature;
	private double newRotation;
	
	public List<Bin<Double>> curvatureBins;

	public boolean isCurvatureFlag() {
		return curvatureFlag;
	}

	public boolean isRotationFlag() {
		return rotationFlag;
	}

	public double getNewCurvature() {
		return newCurvature;
	}

	public double getNewRotation() {
		return newRotation;
	}

	public void setOldCurvature(double oldCurvature) {
		this.oldCurvature = oldCurvature;
	}

	public void setOldRotation(double oldRotation) {
		this.oldRotation = oldRotation;
	}
}
