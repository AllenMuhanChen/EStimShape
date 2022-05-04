package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class QualitativeMorphParameterGenerator {
	private boolean manualMode = false;
	private QualitativeMorphParams qmp;
	private double maxImageDimensionDegrees;
	public QualitativeMorphParameterGenerator(double maxImageDimensionDegrees) {
		this.setMaxImageDimensionDegrees(maxImageDimensionDegrees);
		this.setQmp(new QualitativeMorphParams());
	}
	public void chooseMorphs(int numCategories) {
		getQmp().objectCenteredPositionFlag = false;
		getQmp().curvatureRotationFlag = false;
		getQmp().sizeFlag = false;
		getQmp().radProfileFlag = false;
		getQmp().removalFlag = false;

		List<Integer> categories = new ArrayList<>();
		categories.add(0); categories.add(1); categories.add(2); //categories.add(3);
		Collections.shuffle(categories);
		if(stickMath_lib.rand01()<getQmp().CHANCE_TO_REMOVE) {
			getQmp().removalFlag = true;
		}
		else {
			for(int i=0; i<numCategories; i++) {
				int cat = categories.get(i);
				if(cat==0) {
					getQmp().objectCenteredPositionFlag = true;
					//				System.out.println("Object Centered@@@@@@@@@@@");
				}
				else if (cat==1) {
					getQmp().curvatureRotationFlag = true;
					//				System.out.println("Curvature Rotation!!!!!!!!!!!!");
				}
				//			else if (cat==2) {
				//				getQmp().sizeFlag = true;
				////				System.out.println("Size##########");
				//			}
				else if (cat==2) {
					getQmp().radProfileFlag = true;
					//				System.out.println("Rad Profile%%%%%%%%%%");
				}
				//			else if (cat==3) {
				//				getQmp().removalFlag = true;
				//			}
				else {
					throw new IllegalArgumentException("There should only be 4 qualitative morph types");
				}
			}
		}

		if(manualMode) {
			getQmp().objectCenteredPositionFlag = false;
			getQmp().curvatureRotationFlag = false;
			getQmp().sizeFlag = false;
			getQmp().radProfileFlag = false;
			getQmp().removalFlag = true;
			//			getQmp().curvatureRotationFlag = true;
			getQmp().radProfileFlag = false;
		}
	}
	public QualitativeMorphParams getQMP(int numCategories) {
		chooseMorphs(numCategories);

		{//Object Centered Position - Orientation and Position
			getQmp().objCenteredPosQualMorph = new ObjectCenteredPositionQualitativeMorph();
			List<Bin<Integer>> positionBins = getQmp().objCenteredPosQualMorph.positionBins;
			positionBins.add(new Bin<Integer>(1,1));
			positionBins.add(new Bin<Integer>(20,32));
			positionBins.add(new Bin<Integer>(51,51));

			getQmp().objCenteredPosQualMorph.setAngleDifferenceBounds(new Double[] {90 * Math.PI/180, 270 * Math.PI/180});
			
		}
		{//Curvature And Rotation
			getQmp().curvRotQualMorph = new CurvatureRotationQualitativeMorph();
			List<Bin<Double>> curvatureBins = getQmp().curvRotQualMorph.curvatureBins;
			curvatureBins.add(new Bin<Double>(0.5, 1.0));
			curvatureBins.add(new Bin<Double>(3.0, 6.0));
			curvatureBins.add(new Bin<Double>(100000.0, 100000.0001));
			//			double radView = 5;
			//			curvatureBins.add(new Bin<Double>(0.1*radView, 0.2*radView));
			//			curvatureBins.add(new Bin<Double>(3.0*radView, 6.0*radView));
			//			curvatureBins.add(new Bin<Double>(100000.0, 100000.0001));
		}
		{//Size: Length & Width
			getQmp().sizeQualMorph = new SizeQualitativeMorph(getMaxImageDimensionDegrees()/2);
			//These bins will be scaled depending on the particular limb's arcLen and curvature 
			List<Bin<Double>> lengthBins = getQmp().sizeQualMorph.lengthBins;
			lengthBins.add(new Bin<Double>(0.2, 0.3));
			lengthBins.add(new Bin<Double>(0.55, 0.65));
			lengthBins.add(new Bin<Double>(0.90, 1.00));
			List<Bin<Double>> thicknessBins = getQmp().sizeQualMorph.thicknessBins;
			thicknessBins.add(new Bin<Double>(0.25, 0.4));
			//		thicknessBins.add(new Bin<Double>(0.55, 0.65));
			thicknessBins.add(new Bin<Double>(0.8, 1.0));
		}
		{//radProfile
			getQmp().radProfileQualMorph = new RadProfileQualitativeMorph();
			//double dev=0.1;
			double mini = 0.5;
			double fat = 1;
			double tip = .1;
			double tipDev = 0.09999;
			List<Vector3d> radProfileBins = getQmp().radProfileQualMorph.radProfileBins;
			tip = tip - tipDev;
			radProfileBins.add(new Vector3d(fat, fat, fat));
			radProfileBins.add(new Vector3d(mini, mini, fat));
			radProfileBins.add(new Vector3d(mini, fat, mini));
			radProfileBins.add(new Vector3d(fat, mini,mini));
			radProfileBins.add(new Vector3d(mini, fat, fat));
			radProfileBins.add(new Vector3d(fat, mini, fat));
			radProfileBins.add(new Vector3d(fat, fat, mini));
			radProfileBins.add(new Vector3d(fat, mini, tip));
			radProfileBins.add(new Vector3d(fat, fat, tip));
			radProfileBins.add(new Vector3d(mini, fat, tip));
		}
		return getQmp();
	}

	private QualitativeMorphParams getQmp() {
		return qmp;
	}

	private void setQmp(QualitativeMorphParams qmp) {
		this.qmp = qmp;
	}

	private double getMaxImageDimensionDegrees() {
		return maxImageDimensionDegrees;
	}

	private void setMaxImageDimensionDegrees(double maxImageDimensionDegrees) {
		this.maxImageDimensionDegrees = maxImageDimensionDegrees;
	}
}
