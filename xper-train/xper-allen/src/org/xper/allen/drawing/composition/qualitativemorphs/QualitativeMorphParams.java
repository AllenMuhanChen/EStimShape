package org.xper.allen.drawing.composition.qualitativemorphs;


public class QualitativeMorphParams{
	public boolean objectCenteredPositionFlag; //orientation & position
	public boolean curvatureAndRotationFlag; //only makes sense to morph rotation if curvature is high
	public boolean lengthFlag;
	public boolean sizeFlag;
	public boolean radProfileFlag;
	public ObjectCenteredPositionQualitativeMorph objCenteredPosQualMorph;
}