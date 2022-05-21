package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.Dependency;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.drawing.stick.stickMath_lib;

public class PsychometricQualitativeMorphParameterGenerator {
	public List<QualitativeMorphParams> qmps;
	private double maxImageDimensionDegrees;

	public PsychometricQualitativeMorphParameterGenerator(double maxImageDimensionDegrees) {
		this.setMaxImageDimensionDegrees(maxImageDimensionDegrees);
	}

	public List<QualitativeMorphParams> getQMP(int numStim) {
		this.qmps = new ArrayList<QualitativeMorphParams>();
		for(int i=0; i<numStim; i++) {
			qmps.add(i, new QualitativeMorphParams());
			qmps.get(i).setCHANCE_TO_REMOVE(0);

			{//Object Centered Position - Orientation and Position
				qmps.get(i).objCenteredPosQualMorph = new ObjectCenteredPositionQualitativeMorph();
				qmps.get(i).objCenteredPosQualMorph.PERCENT_CHANGE_POSITION = 0;
				List<Bin<Integer>> positionBins = qmps.get(i).objCenteredPosQualMorph.positionBins;
				positionBins.add(new Bin<Integer>(1,1));
				positionBins.add(new Bin<Integer>(20,32));
				positionBins.add(new Bin<Integer>(51,51));

				qmps.get(i).objCenteredPosQualMorph.setAngleDifferenceBounds(new Double[] {90 * Math.PI/180, 270 * Math.PI/180});

			}
			{//Curvature And Rotation
				qmps.get(i).curvRotQualMorph = new CurvatureRotationQualitativeMorph();
				List<Bin<Double>> curvatureBins = qmps.get(i).curvRotQualMorph.curvatureBins;
				curvatureBins.add(new Bin<Double>(0.5, 1.0));
				curvatureBins.add(new Bin<Double>(3.0, 6.0));
				curvatureBins.add(new Bin<Double>(100000.0, 100000.0001));
				//			double radView = 5;
				//			curvatureBins.add(new Bin<Double>(0.1*radView, 0.2*radView));
				//			curvatureBins.add(new Bin<Double>(3.0*radView, 6.0*radView));
				//			curvatureBins.add(new Bin<Double>(100000.0, 100000.0001));
			}
			{//Size: Length & Width
				qmps.get(i).sizeQualMorph = new SizeQualitativeMorph(getMaxImageDimensionDegrees()/2);
				//These bins will be scaled depending on the particular limb's arcLen and curvature 
				List<Bin<Double>> lengthBins = qmps.get(i).sizeQualMorph.lengthBins;
				lengthBins.add(new Bin<Double>(0.2, 0.3));
				lengthBins.add(new Bin<Double>(0.55, 0.65));
				lengthBins.add(new Bin<Double>(0.90, 1.00));
				List<Bin<Double>> thicknessBins = qmps.get(i).sizeQualMorph.thicknessBins;
				thicknessBins.add(new Bin<Double>(0.25, 0.4));
				//		thicknessBins.add(new Bin<Double>(0.55, 0.65));
				thicknessBins.add(new Bin<Double>(0.8, 1.0));
			}
			{//radProfile
				qmps.get(i).radProfileQualMorph = new RadProfileQualitativeMorph();
				//double dev=0.1;
				double mini = 0.5;
				double fat = 1;
				double tip = .1;
				double tipDev = 0.09999;
				List<Vector3d> radProfileBins = qmps.get(i).radProfileQualMorph.radProfileBins;
				//			tip = tip - tipDev;
				tip = 0.0001;
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
		}

		chooseMorphs(qmps);
		return qmps;
	}


	/**
	 * Chooses Morphs based on noiseType: PRE_JUNC OR POST_JUNC
	 * PRE_JUNC: Orientation & (Limb Removal? - needs more development to develop NoiseMaps)
	 * POST_JUNC: RadProfile, Curvature & Rotation
	 * @param numCategories
	 */
	protected void chooseMorphs(List<QualitativeMorphParams> qmps) {

		for(QualitativeMorphParams qmp:qmps) {
			qmp.objectCenteredPositionFlag = false;
			qmp.curvatureRotationFlag = false;
			qmp.sizeFlag = false;
			qmp.radProfileFlag = false;
			qmp.removalFlag = false;
		}
		List<Integer> categories = new ArrayList<>();
		List<Integer> remainingCategories = new ArrayList<>();

		int numMorphTypes = 7;
		int numCategories = 7;

		for(int i=0; i<numMorphTypes; i++) {
			categories.add(i);
		}

		Collections.shuffle(categories);
		remainingCategories.addAll(categories);

		for(int q=0; q<qmps.size(); q++) {
			QualitativeMorphParams qmp = qmps.get(q);

			if (q<numCategories) {

				int cat = remainingCategories.get(0);

				if(cat==0) {
					qmp.objectCenteredPositionFlag = true;

				}
				else if (cat==1) {
					qmp.curvatureRotationFlag = true;
				}

				else if (cat==2) {
					qmp.radProfileFlag = true;
				}

				else if (cat==3) {
					qmp.objectCenteredPositionFlag = true;
					qmp.curvatureRotationFlag = true;
				}
				else if (cat==4) {
					qmp.objectCenteredPositionFlag = true;
					qmp.radProfileFlag = true;

				}
				else if (cat==5) {
					qmp.curvatureRotationFlag = true;
					qmp.radProfileFlag = true;
				}
				else if (cat==6) {
					qmp.objectCenteredPositionFlag = true;
					qmp.curvatureRotationFlag = true;
					qmp.radProfileFlag = true;
				}
				else {
					throw new IllegalArgumentException("There should only be 7 qualitative morph types");
				}
				remainingCategories.remove(0);
				System.out.println("AC983240293: CHOSEN MORPHS: ");
				System.out.println("objCenteredPos: " + qmp.objectCenteredPositionFlag);
				System.out.println("curvatureRotation: " + qmp.curvatureRotationFlag);
				System.out.println("radProfile: " + qmp.radProfileFlag);
			}

			// q>numCategories
			else {
				Collections.shuffle(categories);

				int cat = categories.get(0);
				if(cat==0) {
					qmp.objectCenteredPositionFlag = true;

				}
				else if (cat==1) {
					qmp.curvatureRotationFlag = true;
				}

				else if (cat==2) {
					qmp.radProfileFlag = true;
				}

				else if (cat==3) {
					qmp.objectCenteredPositionFlag = true;
					qmp.curvatureRotationFlag = true;
				}
				else if (cat==4) {
					qmp.objectCenteredPositionFlag = true;
					qmp.radProfileFlag = true;

				}
				else if (cat==5) {
					qmp.curvatureRotationFlag = true;
					qmp.radProfileFlag = true;
				}
				else if (cat==6) {
					qmp.objectCenteredPositionFlag = true;
					qmp.curvatureRotationFlag = true;
					qmp.radProfileFlag = true;
				}
				else {
					throw new IllegalArgumentException("There should only be 7 qualitative morph types");
				}
				Collections.shuffle(categories);
			}
		}

		//		if(isManualMode()) {
		//			getQmp().objectCenteredPositionFlag = false;
		//			getQmp().curvatureRotationFlag = false;
		//			getQmp().sizeFlag = false;
		//			getQmp().radProfileFlag = false;
		//			getQmp().removalFlag = false;
		//			getQmp().radProfileFlag = false;
		//		}
	}

	private double getMaxImageDimensionDegrees() {
		return maxImageDimensionDegrees;
	}

	private void setMaxImageDimensionDegrees(double maxImageDimensionDegrees) {
		this.maxImageDimensionDegrees = maxImageDimensionDegrees;
	}




}
