package org.xper.allen.drawing.composition.metricmorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class MetricMorphParameterGenerator {
	private boolean manualMode = false;
	MetricMorphParams mmp;
	
	public MetricMorphParameterGenerator() {
		this.mmp = new MetricMorphParams();
	}
	
	public MetricMorphParams getMMP(double sampleScaleUpperLim, double numberCategories) {
		//orientation (along along mAxis)
		mmp.orientationMagnitude = new MetricMorphOrientation();
		mmp.orientationMagnitude.setAngleChangeLowerBound(20*Math.PI/180);
		mmp.orientationMagnitude.setAngleChangeUpperBound(30*Math.PI/180);
		//rotation (rotation along tangent axis)
		mmp.rotationMagnitude = new RotationMetricMorphMagnitude();
		mmp.rotationMagnitude.percentChangeLowerBound = 0.025;
		mmp.rotationMagnitude.percentChangeUpperBound = 0.05;
		//length (arcLength of mAxis Arc)
		mmp.lengthMagnitude = new LengthMetricMorphMagnitude(sampleScaleUpperLim/2);
		mmp.lengthMagnitude.percentChangeLowerBound = 0.10;
		mmp.lengthMagnitude.percentChangeUpperBound = 0.15;
		//size (uniform scale of radProfile)
		mmp.sizeMagnitude = new SizeMetricMorphMagnitude();
		mmp.sizeMagnitude.percentChangeLowerBound = 0.22;
		mmp.sizeMagnitude.percentChangeUpperBound = 0.24;
		//curvature
		mmp.curvatureMagnitude = new CurvatureMetricMorphMagnitude(sampleScaleUpperLim);
		mmp.curvatureMagnitude.setPercentChangeLowerBound(0.5);
//		//position
//		mmp.positionMagnitude = new PositionMetricMorphMagnitude();
//		mmp.positionMagnitude.percentChangeLowerBound = 0.05;
//		mmp.positionMagnitude.percentChangeUpperBound = 0.1;
		//radProfile - Junc
		mmp.radProfileJuncMagnitude = new RadProfileMetricMorphMagnitude();
		mmp.radProfileJuncMagnitude.percentChangeLowerBound = 0.05;
		mmp.radProfileJuncMagnitude.percentChangeUpperBound = 0.1;
		//radProfile - Mid
		mmp.radProfileMidMagnitude = new RadProfileMetricMorphMagnitude();
		mmp.radProfileMidMagnitude.percentChangeLowerBound = 0.05;
		mmp.radProfileMidMagnitude.percentChangeUpperBound = 0.1;
		//radProfile - End
		mmp.radProfileEndMagnitude = new RadProfileMetricMorphMagnitude();
		mmp.radProfileEndMagnitude.percentChangeLowerBound = 0.05;
		mmp.radProfileEndMagnitude.percentChangeUpperBound = 0.1;
		//
		
		mmp.orientationFlag = false;
		mmp.rotationFlag = false;
		mmp.lengthFlag = false;
		mmp.sizeFlag = false;
		mmp.curvatureFlag = false;
		mmp.positionFlag = false;
		mmp.radProfileJuncFlag = false;
		mmp.radProfileMidFlag = false;
		mmp.radProfileEndFlag = false;
		
		int numCats = 4;
		List<Integer> categories = new ArrayList<>();
		for(int i=0; i<numCats; i++) {
			categories.add(i);
		}
		Collections.shuffle(categories);
		for(int i=0; i<numberCategories; i++) {
			int cat = categories.get(i);
			if (cat==0) mmp.orientationFlag=true;
			if (cat==1) mmp.rotationFlag=true;
			if (cat==2) mmp.lengthFlag=true;
			if (cat==4) mmp.curvatureFlag=true;
//			if (cat==3) mmp.sizeFlag=true;
//			if (cat==5) mmp.positionFlag=true;
//			if (cat==5) mmp.radProfileJuncFlag=true;
//			if (cat==6) mmp.radProfileMidFlag=true;
//			if (cat==7) mmp.radProfileEndFlag=true;
		}
		
		if(manualMode) {
			System.out.println("WARNING: MANUAL MODE ON IN METRIC MORPH PARAMS!!");
			mmp.orientationFlag   = true;
			mmp.rotationFlag      = false;
			mmp.lengthFlag        = false;
			mmp.sizeFlag          = false;
			mmp.curvatureFlag     = false;
			mmp.positionFlag 	  = false;
//			mmp.radProfileJuncFlag= true;
//			mmp.radProfileMidFlag = true;
//			mmp.radProfileEndFlag = true;
			
			
		}
		
		return mmp;
	}
}
