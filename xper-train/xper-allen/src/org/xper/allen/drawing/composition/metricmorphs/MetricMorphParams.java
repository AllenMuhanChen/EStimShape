package org.xper.allen.drawing.composition.metricmorphs;

import java.util.ArrayList;

/**
 * Class for passing to mstick generators in order to tell a generator what aspects to morph and what the limits
 * of the random generation should be. 
 * 
 * Generate one object of this class for each "Metric Morph" pass each individual one to the separate generator methods
 * Then after the generation, the new and old values can be recovered from the fooMagnitude objects for storage. 
 * @author r2_allen
 *
 */
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
	public MetricMorphOrientation    orientationMagnitude;
	public RotationMetricMorphMagnitude rotationMagnitude;
	public LengthMetricMorphMagnitude lengthMagnitude;
	public SizeMetricMorphMagnitude sizeMagnitude;
	public CurvatureMetricMorphMagnitude curvatureMagnitude;
	public PositionMetricMorphMagnitude positionMagnitude;
	public RadProfileMetricMorphMagnitude radProfileJuncMagnitude;
	public RadProfileMetricMorphMagnitude radProfileMidMagnitude;
	public RadProfileMetricMorphMagnitude radProfileEndMagnitude;
}