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
	public double CHANCE_TO_REMOVE = 0.25;
	
}