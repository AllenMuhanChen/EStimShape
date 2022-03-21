package org.xper.allen.drawing.composition.metricmorphs;

import java.util.ArrayList;

public class MetricMorphParams{
	public boolean orientationFlag; //change orientation?
	public boolean rotationFlag;
	public boolean lengthFlag;
	public boolean sizeFlag;
	public boolean curvatureFlag;
	public boolean positionFlag;
	public boolean radProfileJuncFlag;
	public boolean radProfileMidFlag;
	public boolean radProfileEndFlag;
	public MetricMorphVector    orientationMagnitude;
	public RotationMetricMorphMagnitude rotationMagnitude;
	public LengthMetricMorphMagnitude lengthMagnitude;
	public SizeMetricMorphMagnitude sizeMagnitude;
	public CurvatureMetricMorphMagnitude curvatureMagnitude;
	public PositionMetricMorphMagnitude positionMagnitude;
	public RadProfileMetricMorphMagnitude radProfileJuncMagnitude;
	public RadProfileMetricMorphMagnitude radProfileMidMagnitude;
	public RadProfileMetricMorphMagnitude radProfileEndMagnitude;
}