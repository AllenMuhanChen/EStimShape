package org.xper.allen.drawing.composition.qualitativemorphs;


public class QualitativeMorphParams{
	public boolean objectCenteredPositionFlag; //orientation & position
	public boolean curvatureRotationFlag; //only makes sense to morph rotation if curvature is high
	public boolean sizeFlag;
	public boolean radProfileFlag;
	public boolean removalFlag;
	public ObjectCenteredPositionQualitativeMorph objCenteredPosQualMorph;
	public CurvatureRotationQualitativeMorph curvRotQualMorph;
	public SizeQualitativeMorph sizeQualMorph;
	public RadProfileQualitativeMorph radProfileQualMorph;
	
	
	private double CHANCE_TO_REMOVE = 0;
	public double getCHANCE_TO_REMOVE() {
		return CHANCE_TO_REMOVE;
	}
	public void setCHANCE_TO_REMOVE(double cHANCE_TO_REMOVE) {
		CHANCE_TO_REMOVE = cHANCE_TO_REMOVE;
	}
	
}