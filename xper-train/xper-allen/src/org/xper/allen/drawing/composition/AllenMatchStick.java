package org.xper.allen.drawing.composition;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.EndPt_struct;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.MAxisArc;
import org.xper.drawing.stick.MStickObj4Smooth;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.stick.TubeComp;
import org.xper.drawing.stick.stickMath_lib;
import org.xper.utils.RGBColor;

import com.thoughtworks.xstream.XStream;

/**
 * MatchStick class with ability to make deep clones and manipulations of shapes
 * 
 * @author r2_allen
 *
 */
public class AllenMatchStick extends MatchStick {

	protected final double PROB_addToEndorJunc = 0.5; // 50% add to end or
	// junction pt, 50% to the
	// branch
	protected final double PROB_addToEnd_notJunc = 0.5; // when "addtoEndorJunc",
	// 50% add to end, 50%
	// add to junc
	protected final double PROB_addTiptoBranch = 0.5; 	// when "add new component to the branch is true"
	protected final double[] finalRotation = new double[3];
	protected double minScaleForMAxisShape;

	protected final double[] PARAM_nCompDist = {0, 1, 0, 0, 0.0, 0.0, 0.0, 0.0 };
	protected final double TangentSaveZone = Math.PI/64;

	int specialEnd=0;
	int specialEndComp=0;
	public AllenMatchStick() {
		super.finalRotation = this.finalRotation;
	}

	@Override
	public void draw() {
		init();
		/**
		 * AC: This thread sleep is NECESSARY. Without it, there are serious
		 * graphical glitches with the first saved image drawn. My guess is that
		 * there is some multithreaded stuff in init() (openGL?) that didn't have
		 * time to finish before drawSkeleton() is called. 
		 */
		try {
			Thread.sleep(100);
		} catch (InterruptedException e) {
			e.printStackTrace();
		}
		drawSkeleton();
	}

	public void drawSkeleton() {
		int i;
		boolean showComponents = false;
		if (showComponents)
			for (i=1; i<=nComponent; i++) {
				float[][] colorCode= {  
						{1.0f, 1.0f, 1.0f},
						{1.0f, 0.0f, 0.0f},
						{0.0f, 1.0f, 0.0f},
						{0.0f, 0.0f, 1.0f},
						{0.0f, 1.0f, 1.0f},
						{1.0f, 0.0f, 1.0f},
						{1.0f, 1.0f, 0.0f},
						{0.4f, 0.1f, 0.6f} 
				};


				comp[i].drawSurfPt(colorCode[i-1],scaleForMAxisShape);
			}
		else
			getObj1().drawVect();
	}


	public void centerShapeAtPoint(int decidedCenterTube, Coordinates2D coords) {
		Point3d newLocation = new Point3d();
		newLocation.x = coords.getX();
		newLocation.y = coords.getY();
		newLocation.z = 0;

		centerShapeAtPoint(decidedCenterTube, newLocation);
	}

	/**
	 * A function that will put the center of comp1 to a specific point.
	 */
	public void centerShapeAtPoint(int decidedCenterTube, Point3d point) {
		boolean showDebug = false;
		int i;
		int compToCenter = decidedCenterTube;
		if (compToCenter == -1) // no preference
			compToCenter = findBestTubeToCenter();

		this.nowCenterTube = compToCenter;
		// Point3d nowComp1Center = new
		// Point3d(comp[compToCenter].mAxisInfo.mPts[comp[compToCenter].mAxisInfo.branchPt]);
		// Dec 26th, change .branchPt to .MiddlePT (i.e. always at middle)
		int midPtIndex = 26;
		Point3d nowComp1Center = new Point3d(comp[compToCenter].mAxisInfo.mPts[midPtIndex]);
		Vector3d shiftVec = new Vector3d();
		shiftVec.sub(point, nowComp1Center);
		// System.out.println("comp to center "+ compToCenter);
		// System.out.println(nowComp1Center);
		if (point.distance(nowComp1Center) > 0.001) {
			if (showDebug)
				System.out.println("shift to make it center at origin!");
			Point3d finalPos = new Point3d();

			for (i = 1; i <= nComponent; i++) {
				finalPos.add(comp[i].mAxisInfo.transRotHis_finalPos, shiftVec);
				this.comp[i].translateComp(finalPos);
			}
			// also, all JuncPt and EndPt
			for (i = 1; i <= nJuncPt; i++) {
				JuncPt[i].pos.add(shiftVec);
			}
			for (i = 1; i <= nEndPt; i++) {
				endPt[i].pos.add(shiftVec);
			}
			// I'll call this check seperately
			// if ( this.validMStickSize() == false)
			// return false;
		}
		// return true;

	}

	public boolean genReplacedLeafMatchStick(int leafToMorphIndx, AllenMatchStick amsToMorph, boolean maintainTangent) {
		int i = 0;
		while (i<2) {
			this.cleanData();
			// 0. Copy
			copyFrom(amsToMorph);

			// 1. DO THE MORPHING
			int j = 0;
			boolean success = false;
			while (j<10){
				success = replaceComponent(leafToMorphIndx, maintainTangent);
				if(success){
					break;
				} else{
					j++;
				}
			}
			// this.MutateSUB_reAssignJunctionRadius(); //Keeping this off keeps
			// junctions similar to previous

			centerShapeAtOrigin(-1);
			if(success){
				boolean res;
				try{
					res = smoothizeMStick();
				} catch(Exception e){
					res = false;
				}
				if (res == true) // success to smooth
					return true; // else we need to gen another shape
				else{
				}
			}
			i++;
		}
		return false;

	}

	/**
	 * replace one of the component with a total new tube
	 * 
	 * But controlling the angle the new tube can be - Allen Chen
	 */
	protected boolean replaceComponent(int id, boolean maintainTangent) {
		int i, j, k;
		int TotalTrialTime = 0;
		int inner_totalTrialTime = 0; // for inner while loop
		boolean showDebug = false;
		// final double TangentSaveZone = Math.PI / 4.0;
		boolean[] JuncPtFlg = new boolean[nJuncPt + 1]; // = true when this
		// JuncPt is related to
		// the (id) component
		int[] targetUNdx = new int[nJuncPt + 1]; // to save the target uNdx in
		// particular Junc pt
		if (showDebug)
			System.out.println("In replace component (AllenMatchStick), will replace comp " + id);
		// we'll find this function need to share some sub_function with
		// fineTuneComponent
		// 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
		int alignedPt;
		alignedPt = MutationSUB_determineHinge(id);
		Point3d alignedPos = new Point3d();
		alignedPos.set(comp[id].mAxisInfo.mPts[alignedPt]);

		int[] compLabel = new int[nComponent + 1];
		int TangentTryTimes = 1;
		compLabel = MutationSUB_compRelation2Target(id);

		// debug, show compLabel
		// System.out.println("compLabel: ");
		// for (i=1; i<= nComponent; i++)
		// System.out.println("comp " + i + " with label" + compLabel[i]);
		// System.out.println("Hinge Pt is " + alignedPt);

		// 2. start picking new MAxisArc
		for (i = 1; i <= nJuncPt; i++)
			for (j = 1; j <= JuncPt[i].nComp; j++) {
				if (JuncPt[i].comp[j] == id) {
					JuncPtFlg[i] = true;
					targetUNdx[i] = JuncPt[i].uNdx[j];
				}
			}

		MAxisArc nowArc;
		MatchStick old_MStick = new MatchStick();
		old_MStick.copyFrom(this);
		while (true) {
			while (true) {
				while (true) {

					// store back to old condition
					this.copyFrom(old_MStick);
					// random get a new MAxisArc
					nowArc = new MAxisArc();
					nowArc.genArcRand();

					Vector3d finalTangent = new Vector3d();

					if (maintainTangent) {
						finalTangent = old_MStick.getTubeComp(id).mAxisInfo.transRotHis_finalTangent;
					} else {
						finalTangent = stickMath_lib.randomUnitVec();
					}

					double devAngle = stickMath_lib.randDouble(0, Math.PI * 2);
					nowArc.transRotMAxis(alignedPt, alignedPos, alignedPt, finalTangent, devAngle);
					boolean tangentFlg = true;
					Vector3d nowTangent = new Vector3d();
					for (i = 1; i <= nJuncPt; i++)
						if (JuncPtFlg[i] == true) {
							int uNdx = targetUNdx[i];
							boolean midBranchFlg = false;
							if (uNdx == 1)
								finalTangent.set(nowArc.mTangent[uNdx]);
							else if (uNdx == 51) {
								finalTangent.set(nowArc.mTangent[uNdx]);
								finalTangent.negate();
							} else // middle branch Pt
							{
								midBranchFlg = true;
								finalTangent.set(nowArc.mTangent[uNdx]);
							}
							// check the angle
							for (j = 1; j <= JuncPt[i].nTangent; j++)
								if (JuncPt[i].tangentOwner[j] != id) // don't
									// need
									// to
									// check
									// with
									// the
									// replaced
									// self
								{
									nowTangent = JuncPt[i].tangent[j]; // soft
									// copy
									// is
									// fine
									// here
									if (nowTangent.angle(finalTangent) <= TangentSaveZone) // angle
										// btw
										// the
										// two
										// tangent
										// vector
										tangentFlg = false;
									if (midBranchFlg == true) {
										finalTangent.negate();
										if (nowTangent.angle(finalTangent) <= TangentSaveZone) //
											tangentFlg = false;
									}
								}

						} // for loop, check through related JuncPt for
					// tangentSaveZone

					if (tangentFlg == true){ // still valid after all tangent
						// check
						break;
					}
					TangentTryTimes++; //AC
					if (TangentTryTimes > 100){
						return false;
					}
				} // third while, will quit after tangent Save Zone check passed

				// update the information of the related JuncPt
				Vector3d finalTangent = new Vector3d();
				for (i = 1; i <= nJuncPt; i++)
					if (JuncPtFlg[i] == true) {
						int nowUNdx = targetUNdx[i];
						finalTangent.set(nowArc.mTangent[nowUNdx]);
						if (targetUNdx[i] == 51)
							finalTangent.negate();
						Point3d newPos = nowArc.mPts[nowUNdx];
						Point3d shiftVec = new Point3d();
						shiftVec.sub(newPos, JuncPt[i].pos);

						if (nowUNdx != alignedPt) // not the aligned one, we
							// need to translate
						{
							for (j = 1; j <= JuncPt[i].nComp; j++)
								if (JuncPt[i].comp[j] != id) {
									int nowCompNdx = JuncPt[i].comp[j];
									for (k = 1; k <= nComponent; k++)
										if (compLabel[k] == nowCompNdx) // the
											// one
											// should
											// move
											// with
											// nowCompNdx
										{
											int nowComp = k;
											Point3d finalPos = new Point3d();
											finalPos.add(comp[nowComp].mAxisInfo.transRotHis_finalPos, shiftVec);
											if (showDebug)
												System.out.println(
														"we have translate comp " + nowComp + "by " + shiftVec);
											this.comp[nowComp].translateComp(finalPos);
											// translate the component
										}
								}
						}

						JuncPt[i].pos = newPos;
						// update the tangent information
						boolean secondFlg = false; // determine if the first or
						// second tanget
						for (j = 1; j <= JuncPt[i].nTangent; j++) {
							if (JuncPt[i].tangentOwner[j] == id && secondFlg == false) {
								JuncPt[i].tangent[j].set(finalTangent);
								secondFlg = true;
							} else if (JuncPt[i].tangentOwner[j] == id && secondFlg == true) {
								finalTangent.negate();
								JuncPt[i].tangent[j].set(finalTangent);
							}
						}
					}
				// now, we can check skeleton closeness

				// set the component to its new role
				boolean branchUsed = this.comp[id].branchUsed;
				int connectType = this.comp[id].connectType;
				this.comp[id] = new TubeComp();
				this.comp[id].initSet(nowArc, branchUsed, connectType);
				boolean closeHit = this.checkSkeletonNearby(nComponent);
				if (closeHit == false) // a safe skeleton
					break;

				inner_totalTrialTime++;
				if (inner_totalTrialTime > 25)
					return false;

			} // second while

			// update the info in end pt and JuncPt
			for (i = 1; i <= nEndPt; i++) {
				Point3d newPos = new Point3d(comp[endPt[i].comp].mAxisInfo.mPts[endPt[i].uNdx]);
				endPt[i].pos.set(newPos);
			}
			for (i = 1; i <= nJuncPt; i++) {
				Point3d newPos = new Point3d(comp[JuncPt[i].comp[1]].mAxisInfo.mPts[JuncPt[i].uNdx[1]]);
				JuncPt[i].pos.set(newPos);
			}
			// now, we apply radius, and then check skin closeness
			int radiusAssignChance = 5;
			int now_radChance = 1;
			boolean success_process = false;
			for (now_radChance = 1; now_radChance <= radiusAssignChance; now_radChance++) {
				// rad assign to new comp
				success_process = true;
				// show the radius value
				// System.out.println("rad assign: ");
				// comp[id].showRadiusInfo();
				double[][] fakeRadInfo = { { -10.0, -10.0 }, { -10.0, -10.0 }, { -10.0, -10.0 } };
				this.MutationSUB_radAssign2NewComp(id, fakeRadInfo);
				// comp[id].showRadiusInfo();
				if (comp[id].RadApplied_Factory() == false) {
					success_process = false;
					continue; // not a good radius, try another
				}

				if (this.finalTubeCollisionCheck() == true) {
					if (showDebug)
						System.out.println("\n IN replace tube: FAIL the final Tube collsion Check ....\n");
					success_process = false;
				}

				if (this.validMStickSize() == false) {
					if (showDebug)
						System.out.println("\n IN replace tube: FAIL the MStick size check ....\n");
					success_process = false;
				}


				if (success_process)
					break;
			}

			TotalTrialTime++;
			if (TotalTrialTime > 5)
				return false;

			if (success_process) // not be here, because of 5 times try
				break;

		} // outtest while

		if (showDebug)
			System.out.println("successfully replace a tube");
		return true;
	}
	/*
	protected void cleanData()
	{
		nComponent = 0;
		nEndPt = 0;
		nJuncPt = 0;
		comp = new TubeComp[9];
		endPt = new EndPt_struct[50];
		JuncPt = new JuncPt_struct[50];
		LeafBranch = new boolean[10];
	}
	 */

	public boolean genQualitativeMorphedLeafMatchStick(int leafToMorphIndx, AllenMatchStick amsToMorph) {
		int i = 0;
		boolean[] profileFlg = new boolean[3];
		profileFlg[0] = true; profileFlg[1] = true; profileFlg[2] = true;

		QualitativeMorphParams qmp = new QualitativeMorphParams();
		qmp.endChance = 1;
		qmp.middleChance = 1;
		double endMagnitude = 1; qmp.endMagnitude = endMagnitude;
		double middleMagnitude = 1; qmp.middleMagnitude = middleMagnitude;


		while (i<2) {
			cleanData();
			// 0. Copy
			copyFrom(amsToMorph);

			// 1. DO THE MORPHING
			int j = 0;
			boolean success = false;
			while (j<10){
				success = morphLeafRadiusProfile(leafToMorphIndx, profileFlg, qmp)
						& postProcessMatchStick();
				if(success){
					break;
				} else{
					j++;
				}
			}
			// this.MutateSUB_reAssignJunctionRadius(); //Keeping this off keeps
			// junctions similar to previous

			centerShapeAtOrigin(-1);
			if(success){
				boolean res;
				try{
					res = smoothizeMStick();
				} catch(Exception e){
					res = false;
				}
				if (res == true) // success to smooth
					return true; // else we need to gen another shape
				else{
				}
			}
			i++;
		}
		return false;

	}

	/**
    	Morph the radius profile of the tube with specified id. 
    		Morphs to radius profile should be capped at a minimum and maximum amount of change
			@param profileFlg - whether we want the Junc, End and Middle to be morphed, respectively
	 */
	protected boolean morphLeafRadiusProfile(int id, boolean[] profileFlg, QualitativeMorphParams qmp)
	{
		boolean showDebug = false;
		double rMin, rMax;
		double nowRad, u_value, tempX;
		int i, j;
		boolean[] JuncPtFlg = new boolean[nJuncPt+1];

		// 0. Determine what radius points need to be morphed and what values to morph them to. 
		double nowEndRad;
		double oldEndRad;
		double nowMidRad;
		double oldMidRad;
		//0.1 determine oldRad of endpoint. 
		int endPtIndx = 0; //indices of end points that belong to limb with "id"
		for ( i = 1 ;  i <= nEndPt ; i++) {
			if ( endPt[i].comp == id && profileFlg[1]) // only do the radius assign for endPt with component we need
			{
				endPtIndx = i;
			}

		}
		oldEndRad = endPt[endPtIndx].rad;
		//0.2 determine oldRad of middlept. 
		int middlePtIndx = 0;
		for ( i = 1 ; i <= nComponent ; i++) {
			if(i ==id && profileFlg[2]) // this component need a intermediate value
			{
				middlePtIndx = i;

			}

		}
		oldMidRad = comp[middlePtIndx].radInfo[1][1];
		//0.3 randomly determine newRads
		//rMin = 0.00001; // as small as you like
		int nowComp = endPt[endPtIndx].comp;
		//rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
		//rMax = Math.max(comp[middlePtIndx].mAxisInfo.rad, comp[nowComp].mAxisInfo.rad);
		NowRads nowRads;
		nowRads = genQualitativeMorphRadii(nowComp, oldEndRad, oldMidRad, qmp.endMagnitude);

		// 1. assign at JuncPt
		for (i=1; i<= nJuncPt; i++)
			for (j=1; j<= JuncPt[i].nComp; j++)
			{
				if ( JuncPt[i].comp[j] == id & profileFlg[0])
				{
					JuncPtFlg[i] = true;
				}
			}

		for (i=1; i<=nJuncPt; i++)
		{
			if (JuncPtFlg[i] & profileFlg[0]) { 
				for (j=1; j<= JuncPt[i].nComp; j++) {
					nowRad = JuncPt[i].rad;
					u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
					if ( Math.abs( u_value - 0.0) < 0.0001)
					{
						comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
						comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
					}
					else if ( Math.abs(u_value - 1.0) < 0.0001)
					{
						comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
						comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
					}
					else // middle u value
					{
						comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
						comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
					}

				}
			} // ?JuncPtFlg 
		} // loop nJuncPt

		// 2. assign at endPt
		//int nowComp = endPt[endPtIndx].comp;
		u_value = ((double)endPt[endPtIndx].uNdx -1.0 ) / (51.0 -1.0);

		//rMin = mStick.comp(nowComp).arcLen / 10.0;

		// select a random value that is a certain % change either smaller or larger from its old value
		nowRad = nowRads.nowEndRad;


		endPt[i].rad = nowRad;

		if ( Math.abs( u_value - 0.0) < 0.0001)
		{
			comp[nowComp].radInfo[0][0] = 0.0;
			comp[nowComp].radInfo[0][1] = nowRad;
		}
		else if (Math.abs(u_value - 1.0) < 0.0001)
		{
			comp[nowComp].radInfo[2][0] = 1.0;
			comp[nowComp].radInfo[2][1] = nowRad;
		}
		else // middle u value
			System.out.println( "error in endPt radius assignment");


		// 3. other middle Pt
		int branchPt = comp[i].mAxisInfo.branchPt;
		u_value = ((double)branchPt-1.0) / (51.0 -1.0);

		rMin = comp[i].mAxisInfo.arcLen / 10.0;
		rMax = Math.max(comp[middlePtIndx].mAxisInfo.arcLen / 3.0, 0.5 * comp[middlePtIndx].mAxisInfo.rad);
		nowRad = nowRads.nowMidRad;
		comp[middlePtIndx].radInfo[1][0] = u_value;
		comp[middlePtIndx].radInfo[1][1] = nowRad;

		return true;
	}

	public NowRads genQualitativeMorphRadii(int nowComp, double oldRadEnd, double oldRadMid, double magnitude) {
		double newEndPt;
		double newMiddlePt;
		double rMinEnd = 0.00001; // as small as you like
		//based on arclength and curvature
		double rMaxEnd = Math.min(comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
		double exclusionLengthEnd = magnitude * (1/2) * (rMaxEnd - rMinEnd);
		double rMinMid = comp[nowComp].mAxisInfo.arcLen / 10;
		double rMaxMid = Math.min(comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
		double exclusionLengthMid = magnitude * (1/2) * (rMaxMid - rMinMid);

		double differenceThreshold = 1000; //How much larger the 

		while(true) {
			double oldRatio = oldRadEnd/oldRadMid;
			//EndPt
			while(true) {
				newEndPt = stickMath_lib.randDouble(rMinEnd, rMaxEnd);
				if( newEndPt < oldRadEnd - exclusionLengthEnd/2 || newEndPt > oldRadEnd + exclusionLengthEnd/2) {
					break;
				}
			}
			//MiddlePt
			while(true) {
				newMiddlePt = stickMath_lib.randDouble(rMinMid, rMaxMid);
				if( newMiddlePt < oldRadMid - exclusionLengthMid/2 || newMiddlePt > oldRadMid + exclusionLengthMid/2) {
					break;
				}
			}

			double newRatio = newEndPt/newMiddlePt;

			if((Math.max(newRatio,oldRatio) / Math.min(newRatio,oldRatio)) > differenceThreshold){
				break;
			}

		}
		NowRads nowRads = new NowRads();
		nowRads.nowEndRad = newEndPt;
		nowRads.nowMidRad = newMiddlePt;
		return nowRads; 
	}

	public class NowRads {
		public double nowEndRad;
		public double nowMidRad;
		public double nowJuncRad;
	}

	/**
	 * Apply radius, do tube collision check, center at origin, and smoothize. 
	 * @return
	 */
	public boolean postProcessMatchStick() {
		boolean showDebug = false;
		// 4. Apply the radius value onto each component
		for (int i=1; i<=nComponent; i++)
		{
			if( comp[i].RadApplied_Factory() == false) // a fail application
			{
				return false;
			}
		}


		// 5. check if the final shape is not working ( collide after skin application)


		if ( finalTubeCollisionCheck() == true)
		{
			if ( showDebug)
				System.out.println("\n FAIL the final Tube collsion Check ....\n");
			return false;
		}


		// Dec 24th 2008
		// re-center the shape before do the validMStickSize check!
		this.centerShapeAtOrigin(-1);
		// this.normalizeMStickSize();

		//   System.out.println("after centering");
		if ( this.validMStickSize() ==  false)
		{
			if ( showDebug)
				System.out.println("\n FAIL the MStick size check ....\n");
			return false;
		}
		return true;
	}



	public boolean genMetricMorphedLeafMatchStick(int leafToMorphIndx, AllenMatchStick amsToMorph, MetricMorphParams mmp) {
		int i = 0;
		while (i<2) {
			this.cleanData();
			// 0. Copy
			copyFrom(amsToMorph);
			// 1. DO THE MORPHING
			int j = 0;
			boolean success = false;
			while (j<10){
				success = metricMorphComponent(leafToMorphIndx, mmp);
				//success = metricMorph.morphLength();
				if(success){
					break;
				} else{
					j++;
				}
			}
			// this.MutateSUB_reAssignJunctionRadius(); //Keeping this off keeps
			// junctions similar to previous
			//MutateSUB_reAssignJunctionRadius();
			//centerShapeAtOrigin(-1);
			if(success){
				boolean res;
				try{
					res = smoothizeMStick();
				} catch(Exception e){
					res = false;
				}
				if (res == true) // success to smooth
					return true; // else we need to gen another shape
				else{
				}
			}
			i++;
		}
		return false;

	}

	/**
    Derived from fineTuneComponent()

    AC: Modifications to keep finetunes to metric changes only. 
    	orientation of limb
    	length of limb
    	radius of limb (not changing radius profile)
	 */
	protected boolean metricMorphComponent(int id, MetricMorphParams mmp)
	{
		int i, j, k;
		int inner_totalTrialTime = 0;
		int TotalTrialTime = 0; // the # have tried, if too many, just terminate
		final double volatileRate = 1;
		boolean showDebug = false;
		//final double TangentSaveZone = Math.PI / 4.0;
		boolean[] JuncPtFlg = new boolean[nJuncPt+1]; // = true when this JuncPt is related to the (id) component
		int[] targetUNdx = new int[nJuncPt+1]; // to save the target uNdx in particular Junc pt
		double[][] old_radInfo = new double[3][2];

		// 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
		int alignedPt;
		alignedPt = MutationSUB_determineHinge(id);

		int[] compLabel = new int[nComponent+1];
		int tangentTrialTimes = 0;
		compLabel = MutationSUB_compRelation2Target(id);

		//0. start picking new MAxisArc & POSITION MORPH
		int specialJunc = 0;
		for (i=1; i<= nJuncPt; i++)
			for (j=1; j<= JuncPt[i].nComp; j++)
			{
				if ( JuncPt[i].comp[j] == id)
				{

					JuncPtFlg[i] = true;

					if(mmp.positionFlag) { //TODO: WORKING ON THIS RIGHT NOW
						//We need to find the Junc_index for the comp that the morphigng limb is attached to
						int baseJuncNdx=0;

						for(int l=1; l<=JuncPt[i].nComp; l++) {
							if(JuncPt[i].comp[l] == baseComp) {
								baseJuncNdx = l;
								System.out.println("AC:8874732" + "I FOUND THE BASEINDEX");
							}
						}


						int oriPosition = JuncPt[i].uNdx[baseJuncNdx];
						mmp.positionMagnitude.oldValue = oriPosition;
						int nowPosition = mmp.positionMagnitude.calculateMagnitude();
						//TODO: DEBUGGING THIS RGIIHT NOW
						//This junction point is an end point
						if(JuncPt[i].uNdx[j] == 51 || JuncPt[i].uNdx[j] == 1) {
							//JuncPt[i].showInfo();
							//add this point as an end point, because it will no longer be a junction
							nEndPt++;
							endPt[nEndPt] = new EndPt_struct(id, JuncPt[i].uNdx[j],
									JuncPt[i].pos, JuncPt[i].tangent[j], JuncPt[i].rad );

							
							//We need to change the uNdx of the limb the morphed limb is attached to
							JuncPt[i].uNdx[baseJuncNdx] = nowPosition;
							//Move our current junction point to a new location
							//TEST//
							
							Point3d[] points = new Point3d[51];
							points[0] = new Point3d(0,0,0);
							for (int n = 1; n<51; n++) {
								points[n] = comp[baseComp].mAxisInfo.mPts[n];
								System.out.println(points[n].distance(points[n-1]));
							}
							////////
							
							JuncPt[i].pos = new Point3d(comp[baseComp].mAxisInfo.mPts[nowPosition]);
					
							//comp[baseComp].mAxisInfo.branchPt = nowPosition;
							mmp.positionMagnitude.newPos = JuncPt[i].pos;
						}
						//This is a middle point

						else {
							//We can just change its position
							JuncPt[i].uNdx[j] = nowPosition;
							JuncPt[i].pos = new Point3d(comp[baseComp].mAxisInfo.mPts[nowPosition]);
							mmp.positionMagnitude.newPos = JuncPt[i].pos;
						}
						targetUNdx[i] = JuncPt[i].uNdx[j];
					}else {
						targetUNdx[i] = JuncPt[i].uNdx[j];
					}
				}

			}
		for (i=0; i<3; i++)
			for (j=0; j<2; j++)
				old_radInfo[i][j] = comp[id].radInfo[i][j];



		AllenMAxisArc nowArc;
		AllenMatchStick old_MStick = new AllenMatchStick();
		old_MStick.copyFrom(this);

		while (true)
		{
			while(true)
			{
				//GENERATE A NEW ARC WITH NEW TANGENT (that is checked by TangentSaveZone)
				while(true)
				{
					// RESET
					tangentTrialTimes++;
					copyFrom(old_MStick);
					// random get a new MAxisArc
					nowArc = new AllenMAxisArc();
					//MAJOR STEP ONE
					nowArc.genMetricSimilarArc(this.comp[id].mAxisInfo, alignedPt, mmp);
					// use this function to generate a similar arc

					//for loop, check through related JuncPt for tangentSaveZone
					Vector3d finalTangent = new Vector3d();
					boolean tangentFlg = true;
					Vector3d nowTangent = new Vector3d();
					for (i=1; i<=nJuncPt; i++)
						if ( JuncPtFlg[i] == true)
						{
							int uNdx = targetUNdx[i];
							boolean midBranchFlg = false;
							if (uNdx == 1)
								finalTangent.set(nowArc.mTangent[uNdx]);
							else if (uNdx == 51)
							{
								finalTangent.set(nowArc.mTangent[uNdx]);
								finalTangent.negate();
							}
							else // middle branch Pt
							{
								midBranchFlg = true;
								finalTangent.set( nowArc.mTangent[uNdx]);
							}
							// check the angle
							for (j=1; j<= JuncPt[i].nTangent; j++)
								if ( JuncPt[i].tangentOwner[j] != id) // don't need to check with the replaced self
								{
									nowTangent = JuncPt[i].tangent[j]; // soft copy is fine here
									if ( nowTangent.angle(finalTangent) <= TangentSaveZone ) // angle btw the two tangent vector
										tangentFlg = false;
									if ( midBranchFlg == true)
									{
										finalTangent.negate();
										if ( nowTangent.angle(finalTangent) <= TangentSaveZone ) //
											tangentFlg = false;
									}
								}

						}

					// still valid after all tangent check
					if (tangentFlg == true) 
						break;
					else
					{

						if ( showDebug)
							System.out.println("didn't pass check tagent Zone in fine tune");
					}
					if (tangentTrialTimes > 100)
						return false;
				} // third while, will quit after tangent Save Zone check passed


				//JUNCPT UPDATE!!!
				//update the information of the related JuncPt
				Vector3d finalTangent = new Vector3d();
				for (i=1; i<= nJuncPt; i++)
					if (JuncPtFlg[i] == true)
					{
						int nowUNdx = targetUNdx[i];
						finalTangent.set(nowArc.mTangent[nowUNdx]);
						if (targetUNdx[i] == 51)
							finalTangent.negate();
						Point3d newPos = nowArc.mPts[ nowUNdx];
						Point3d shiftVec = new Point3d();
						shiftVec.sub(newPos, JuncPt[i].pos);

						if ( nowUNdx != alignedPt) // not the aligned one, we need to translate
						{
							for (j=1; j<= JuncPt[i].nComp; j++)
								if ( JuncPt[i].comp[j] != id)
								{
									int nowCompNdx = JuncPt[i].comp[j];
									for (k=1; k<= nComponent; k++)
										if (compLabel[k] == nowCompNdx) // the one should move with nowCompNdx
										{
											int nowComp = k;
											Point3d finalPos =new Point3d();
											finalPos.add( comp[nowComp].mAxisInfo.transRotHis_finalPos, shiftVec);
											if ( showDebug)
												System.out.println("we have translate comp " + nowComp + "by " + shiftVec);
											this.comp[nowComp].translateComp( finalPos);
											// translate the component
										}
								}
						}
					//TODO: MANUAL ASSIGN HERE!?
						JuncPt[i].pos = newPos;

						//update the tangent information
						boolean secondFlg = false; // determine if the first or second tanget
						for ( j = 1; j <= JuncPt[i].nTangent; j++)
						{
							if (JuncPt[i].tangentOwner[j] == id && secondFlg == false)
							{
								JuncPt[i].tangent[j].set(finalTangent);
								secondFlg = true;
							}
							else if ( JuncPt[i].tangentOwner[j] == id && secondFlg == true)
							{
								finalTangent.negate();
								JuncPt[i].tangent[j].set(finalTangent);
							}
						}
					}
				// now, we can check skeleton closeness

				//set the component to its new role
				boolean branchUsed = this.comp[id].branchUsed;
				int connectType = this.comp[id].connectType;
				this.comp[id] = new TubeComp();
				this.comp[id].initSet( nowArc, branchUsed, connectType);
				if (showDebug)
					System.out.println("In fine tune: tube to modify # " +id +" now check skeleton");
				boolean closeHit = this.checkSkeletonNearby(nComponent);
				if (closeHit == false) // a safe skeleton
				{
					break;
				}
				else
				{
					if ( showDebug)
						System.out.println("skeleton check fail");
					// a debug check
					//              this.copyFrom(old_MStick);
					//              boolean newTest = this.checkSkeletonNearby(nComponent);
					//              System.out.println("skeleton check result after recovery: " + newTest);
				}
				inner_totalTrialTime++;
				if ( inner_totalTrialTime > 25)
					return false;

			} //SECOND WHILE

			// update the info in end pt and JuncPt
			for (i=1; i<=nEndPt; i++)
			{
				Point3d newPos = new Point3d(  comp[ endPt[i].comp].mAxisInfo.mPts[ endPt[i].uNdx]);
				endPt[i].pos.set(newPos);
			}
			for (i=1; i<=nJuncPt; i++)
			{
				Point3d newPos = new Point3d( comp[JuncPt[i].comp[1]].mAxisInfo.mPts[ JuncPt[i].uNdx[1]]);
				JuncPt[i].pos.set(newPos);
			}
			//MAJOR STEP TWO
			// now, we apply radius, and then check skin closeness
			int radiusAssignChance = 5;
			int now_radChance = 1;
			boolean success_process = false;
			for (now_radChance = 1; now_radChance <= radiusAssignChance; now_radChance++)
			{
				// rad assign to new comp
				success_process = true;
				//show the radius value
				//System.out.println("rad assign: ");
				//comp[id].showRadiusInfo();
				this.MutationSUB_radAssign2NewComp_Metric(id, old_radInfo, mmp);
				//comp[id].showRadiusInfo();
				if ( comp[id].RadApplied_Factory() == false)
				{
					success_process = false;
					continue; // not a good radius, try another
				}

				if ( this.finalTubeCollisionCheck() == true)
				{
					if ( showDebug)
						System.out.println("\n IN replace tube: FAIL the final Tube collsion Check ....\n\n");
					success_process = false;
				}
				if ( this.validMStickSize() ==  false)
				{
					if ( showDebug)
						System.out.println("\n IN replace tube: FAIL the MStick size check ....\n\n");
					success_process = false;
				}


				if ( success_process)
					break;
			}
			TotalTrialTime++;
			if ( TotalTrialTime >5)
				return false;
			if ( success_process) // not be here, because of 5 times try
				break;

		} //outer test while

		if ( showDebug)
			System.out.println("successfully fine tune a tube");
		return true;
	}

	public boolean genMatchStickFromLeaf(int leafIndx, AllenMatchStick amsOfLeaf) {
		double[] nCompDist = PARAM_nCompDist;
		int nComp = stickMath_lib.pickFromProbDist(nCompDist);

		// debug
		// nComp = 4;

		// The way we write like this can guarantee that we try to
		// generate a shape with "specific" # of components
		int i=0; //Number of times tried to generate a comp and smoothize it
		boolean compSuccess = false;
		while (i<2) {
			int j=0; //Number of times tried to generate a comp. 
			this.cleanData();
			while (j<10) {
				boolean onlyAddToJunc = true;
				if (genMatchStickFromLeaf_comp(leafIndx, nComp, amsOfLeaf, onlyAddToJunc) == true){
					compSuccess = true;
					break;
				}
				else {
					j++;
				}
				// else
				// System.out.println(" Attempt to gen shape fail. try again");
			}

			// this.finalRotation = new double[3];
			// for (int i=0; i<3; i++)
			// finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			// debug

			// finalRotation[0] = 90.0;
			// finalRotation[1] = 0.0;
			// finalRotation[2] = 0;

			// this.finalRotateAllPoints(finalRotation[0], finalRotation[1],
			// finalRotation[2]);
			centerShapeAtOrigin(-1);
			if(compSuccess){
				boolean res;
				try {
					res = this.smoothizeMStick();
				} catch(Exception e){
					res = false;
				}
				if (res == true){ // success to smooth
					return true;
				}
				else{
				}

			}// else we need to gen another shape
			// else
			// System.out.println(" Fail to smooth combine the shape. try
			// again.");
			i++;
		}
		return false;

	}

	/**
        subFunction of: (replaceComponent, fineTuneComponent) <BR>
     Will determine the radius of the modified component
     If there is value in [][] oriValue, it is the radius value of the original component

	AC: Metric: modified to not change radProfile (both ends & Junc) except for general scaling
	 */
	protected void MutationSUB_radAssign2NewComp_Metric( int targetComp, double[][] oriValue, MetricMorphParams mmp)
	{
		boolean showDebug = false;
		int i, j;
		double rMin, rMax;
		double nowRad= -100.0, u_value;
		double radiusScale = 1;
		if(mmp.sizeFlag){
			mmp.sizeMagnitude.oldValue = radiusScale;
			radiusScale = mmp.sizeMagnitude.calculateMagnitude();
		}

		/*
		{
			i = targetComp;
			comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
		}
		 */



		//set old value at JuncPt
		for (i=1; i<=nJuncPt; i++)
		{
			for (j=1; j<= JuncPt[i].nComp; j++)
				if ( JuncPt[i].comp[j] == targetComp)
				{
					nowRad = JuncPt[i].rad * radiusScale;
					if(mmp.radProfileJuncFlag) {
						mmp.radProfileJuncMagnitude.oldValue = nowRad;
						mmp.radProfileJuncMagnitude.min = comp[targetComp].mAxisInfo.arcLen / 10.0;
						mmp.radProfileJuncMagnitude.max = Math.min( comp[targetComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[targetComp].mAxisInfo.rad);
						nowRad = mmp.radProfileJuncMagnitude.calculateMagnitude();
					}

					u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
					if ( Math.abs( u_value - 0.0) < 0.0001)
					{
						comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
						comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
					}
					else if ( Math.abs(u_value - 1.0) < 0.0001)
					{
						comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
						comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
					}
					else // middle u value
					{
						comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
						comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
					}
				}
		}

		//set new value at end Pt 
		for (i=1; i<= nEndPt; i++)
			if (endPt[i].comp == targetComp)
			{
				//update the information of this endPt, besides radius assignment
				Point3d newPos = new Point3d( comp[targetComp].mAxisInfo.mPts[ endPt[i].uNdx]);
				Vector3d newTangent = new Vector3d( comp[targetComp].mAxisInfo.mTangent[ endPt[i].uNdx]);
				if ( endPt[i].uNdx == 51)
					newTangent.negate();
				endPt[i].pos.set(newPos);
				endPt[i].tangent.set(newTangent);

				//set radius
				u_value = ((double)endPt[i].uNdx-1.0) / (51.0-1.0);
				int nowComp = targetComp;
				//rMin = 0.00001; // as small as you like
				//rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
				//double[] rangeFractions = {0, 0.1}; //AC: modulate new rad profile lims. 
				// retrive the oriValue
				double oriRad;
				if ( endPt[i].uNdx == 1)
					oriRad = oriValue[0][1];
				else  //endPt[i].uNdx == 51
					oriRad = oriValue[2][1];

				nowRad = oriRad * radiusScale;
				if(mmp.radProfileEndFlag) {
					mmp.radProfileEndMagnitude.oldValue = nowRad;
					mmp.radProfileEndMagnitude.min = 0.00001;
					mmp.radProfileEndMagnitude.max = Math.min( comp[targetComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[targetComp].mAxisInfo.rad);
					nowRad = mmp.radProfileEndMagnitude.calculateMagnitude();
				}

				endPt[i].rad = nowRad;

				if ( Math.abs( u_value - 0.0) < 0.0001)
				{
					comp[nowComp].radInfo[0][0] = 0.0;
					comp[nowComp].radInfo[0][1] = nowRad;
				}
				else if (Math.abs(u_value - 1.0) < 0.0001)
				{
					comp[nowComp].radInfo[2][0] = 1.0;
					comp[nowComp].radInfo[2][1] = nowRad;
				}
				else // middle u value
					System.out.println( "error in endPt radius assignment");
			}

		//set intermediate pt if not assigned yet
		i = targetComp;
		double oriRad = oriValue[1][1]; // the middle radius value
		nowRad = oriRad * radiusScale;
		int branchPt = comp[i].mAxisInfo.branchPt;
		u_value = ((double)branchPt-1.0) / (51.0 -1.0);
		if ( mmp.radProfileMidFlag) // this component need a intermediate value
		{
			mmp.radProfileMidMagnitude.oldValue = nowRad;
			mmp.radProfileMidMagnitude.min = comp[targetComp].mAxisInfo.arcLen / 10.0;
			mmp.radProfileMidMagnitude.max = Math.min( comp[targetComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[targetComp].mAxisInfo.rad);
			nowRad = mmp.radProfileMidMagnitude.calculateMagnitude();
		}
		comp[i].radInfo[1][0] = u_value;
		comp[i].radInfo[1][1] = nowRad;
	}

	public List<Integer> leafIndxToEndPts(int leafIndex, AllenMatchStick ams) {
		ArrayList<Integer> output = new ArrayList<Integer>();
		for (int j = 1; j <= ams.nEndPt; j++) {
			if (ams.getEndPtStruct(j).comp == leafIndex)
				;
			output.add(j);
		}
		return output;
	}

	public List<Integer> leafIndxToJuncPts(int leafIndex, AllenMatchStick ams) {
		ArrayList<Integer> output = new ArrayList<Integer>();
		for (int j = 1; j <= ams.nJuncPt; j++) {
			if (Arrays.asList(ams.getJuncPtStruct(j).comp).contains(leafIndex));
			output.add(j);
		}
		return output;
	}
	//TODO:  WORKING HERE NOW
	/**
	 * special end: endPt of a leaf that should never be in a E2E, E2J, E2B etc.. 
	 * specialEndComp: comp of the leaf that this end belongs to. 
	 */

	public boolean genMatchStickFromLeaf_comp(int leafIndx, int nComp, AllenMatchStick amsOfLeaf, boolean onlyAddToJunc){
		boolean showDebug = true;
		//nComp = 2;
		onlyAddToJunc = true;
		nComponent = nComp;
		int i;
		for (i=1; i<=nComponent; i++){
			comp[i] = new TubeComp();
		}

		//STARTING LEAF
		comp[1].copyFrom(amsOfLeaf.getTubeComp(leafIndx));

		double PROB_addBaseToEndNotBranch = 0;
		int add_trial = 0;
		int nowComp = 2;
		//double randNdx;
		boolean addSuccess;
		while (true)
		{
			//DEFINING END AND JUNCTION
			if(onlyAddToJunc){
				ArrayList<Integer> juncList= (ArrayList<Integer>) leafIndxToJuncPts(leafIndx, amsOfLeaf);
				ArrayList<Integer> endList= (ArrayList<Integer>) leafIndxToEndPts(leafIndx, amsOfLeaf);

				//DEFINE JUCTION TO BE A SPECIAL END FROM LEAF
				JuncPt_struct in_junc = amsOfLeaf.getJuncPtStruct(juncList.get(0));
				specialEnd = 1;
				specialEndComp = 1;
				endPt[specialEnd] = new EndPt_struct(specialEndComp, in_junc.uNdx[1], in_junc.pos, in_junc.tangent[1], in_junc.rad);


				//DEFINE END POINT TO BE SAME END POINT AS IN LEAF
				EndPt_struct in_end = amsOfLeaf.getEndPtStruct(endList.get(0));
				int enComp = 1;
				int euNdx = in_end.uNdx;
				Point3d epos = in_end.pos;
				Vector3d etangent = in_end.tangent;
				double erad = in_end.rad;
				endPt[2] = new EndPt_struct(enComp, euNdx, epos, etangent, erad);

				nJuncPt = 0;
				nEndPt = 2;
			}
			else{
				endPt[1] = new EndPt_struct(1, 1, comp[1].mAxisInfo.mPts[1], comp[1].mAxisInfo.mTangent[1] , 100.0);
				endPt[2] = new EndPt_struct(1, 51, comp[1].mAxisInfo.mPts[51], comp[1].mAxisInfo.mTangent[51], 100.0);
				nEndPt = 2;
			}

			////////////////////////////////////////////
			//ADD THE SECOND LIMB- FOLLOWS SPECIAL RULES
			////////////////////////////////////////////
			//Add E2J
			if(stickMath_lib.rand01()<PROB_addBaseToEndNotBranch) {
				addSuccess = Add_BaseMStick(nowComp, 1);
			}
			//Add B2J
			else {
				addSuccess = Add_BaseMStick(nowComp, 2);
			}
			if (addSuccess == true) { // otherwise, we'll run this while loop again, and re-generate this component
				nowComp=3;
				break;
			}
			add_trial++;
			if ( add_trial > 100)
				return false;
		}
		///////////////////////////////////////////////////////////////////////////
		//ADD ANY OTHER LIMBS TO ANYWHERE EXCEPT SPECIAL END (END OF PARENT LEAF)//
		/////////////////////////////////////////////////////////////////////////// 
		add_trial = 0;
		double randNdx;
		addSuccess = false;
		while (true && nowComp <= nComp)
		{
			if ( showDebug)
				System.out.println("adding new MAxis on, now # " +  nowComp);
			randNdx = stickMath_lib.rand01();
			if (nComp==2){
				//addSuccess = Add_MStick(nowComp, 2);
			}

			else if (randNdx < PROB_addToEndorJunc)
			{
				if (nJuncPt == 0 || stickMath_lib.rand01() < PROB_addToEnd_notJunc)
					addSuccess = Add_MStick(nowComp, 1);
				else
					addSuccess = Add_MStick(nowComp, 2);
			}
			else
			{
				if (stickMath_lib.rand01() < PROB_addTiptoBranch)
					addSuccess = Add_MStick(nowComp, 3);
				else
					addSuccess = Add_MStick(nowComp, 4);
			}
			if (addSuccess == true) // otherwise, we'll run this while loop again, and re-generate this component
				nowComp ++;
			if (nowComp == nComp+1)
				break;
			add_trial++;
			if ( add_trial > 100)
				return false;
		}

		//up to here, the eligible skeleton should be ready
		// 3. Assign the radius value
		RadiusAssign(1); // KEEP FIRST ELEMENT SAME RADIUS
		// 4. Apply the radius value onto each component
		for (i=1; i<=nComponent; i++)
		{
			if( this.comp[i].RadApplied_Factory() == false) // a fail application
			{
				if(showDebug)
					System.out.println("Failed RadApplied");
				return false;
			}
		}

		if ( this.finalTubeCollisionCheck() == true)
		{
			if ( showDebug)
				System.out.println("\n FAIL the final Tube collsion Check ....\n");
			return false;
		}

		// 5. check if the final shape is not working ( collide after skin application)
		this.centerShapeAtOrigin(-1);

		if ( this.validMStickSize() ==  false)
		{
			if ( showDebug)
				System.out.println("\n FAIL the MStick size check ....\n");
			return false;
		}



		return true;


	}

	int baseComp = 0;
	protected boolean Add_BaseMStick(int nowComp, int type) {
		boolean showDebug = false;
		//Base System: a single leaf is pre-defined to have one end and one juncion. The base is formed by adding to this junction
		//point, either E2J or B2J. 
		//Add a new component to an existing MStick (there should only be one MStick)
		//1. type==1: E2J (Add end to end onto the end that used to be a junction)
		//2. type==2: B2J (Add a branch pt on a new MStick onto the end that used to be a junction)

		//shared variable Delcaration
		//final double TangentSaveZone = Math.PI / 4.0;
		int i;
		int trialCount = 1; // an indicator that if something try too many time, then just give up

		// random get a new MAxisArc
		MAxisArc nowArc = new MAxisArc();
		nowArc.genArcRand();

		// type 1 base add
		if(type == 1) {

			// 1. pick an endPt

			int nowPtNdx;
			trialCount = 1;

			nowPtNdx = 2;
			if(nowPtNdx==specialEnd) {
				System.out.println("ERROR! We should not be adding to the special end");
				return false;
			}

			// 2. trnasRot the nowArc to the correction configuration
			int alignedPt = 1;
			Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
			Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( oriTangent.angle(finalTangent) > TangentSaveZone ) // angle btw the two tangent vector
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


			// 3. update the EndPT to JuncPt
			nJuncPt++;
			int[] compList = { endPt[nowPtNdx].comp, nowComp};
			int[] uNdxList = { endPt[nowPtNdx].uNdx, 1};
			Vector3d[] tangentList = { oriTangent, finalTangent};
			JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, endPt[nowPtNdx].rad);
			comp[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

			// 2.5 call the function to check if this new arc is valid
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				JuncPt[nJuncPt] = null;
				nJuncPt--;
				return false;
			}
			// 4. generate new endPt
			endPt[nowPtNdx].setValue(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
			// 5. Update the baseComp
			baseComp = nowComp;
		}
		//2. type 2 base add
		else if(type == 2) {
			// 1. pick an EndPt
			trialCount = 1;
			int nowPtNdx;
			trialCount = 1;
			while (true)
			{
				nowPtNdx = stickMath_lib.randInt(1, this.nEndPt);
				if (nowPtNdx != specialEnd)
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. transRot newComp
			int nowUNdx = nowArc.branchPt;
			int alignedPt = nowUNdx;
			Vector3d rev_tangent = new Vector3d();
			Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
			Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();

				rev_tangent.negate(finalTangent);
				if ( oriTangent.angle(finalTangent) > TangentSaveZone &&
						oriTangent.angle(rev_tangent) > TangentSaveZone    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check Nearby Situtation
			// 3. update JuncPt & endPt info
			nJuncPt++;
			int[] compList = { endPt[nowPtNdx].comp, nowComp};
			int[] uNdxList = { endPt[nowPtNdx].uNdx, nowUNdx};
			Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
			int[] ownerList = {endPt[nowPtNdx].comp, nowComp, nowComp};
			double rad;
			rad = endPt[nowPtNdx].rad;
			this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

			// 2.5 call the function to check if this new arc is valid
			comp[nowComp].initSet(nowArc, true, 4);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				JuncPt[nJuncPt] = null;
				nJuncPt--;
				return false;
			}
			// 4. generate 2 new endPt
			this.endPt[nowPtNdx].setValue(nowComp, 1, nowArc.mPts[1], nowArc.mTangent[1], 100.0);
			nEndPt++;
			this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
			//5. Update the baseComp
			baseComp = nowComp;
		}

		if ( showDebug)
			System.out.println("end of add tube func successfully");
		return true;
		// call the check function to see if the newly added component violate the skeleton nearby safety zone.
	}

	/**
    Assign the radius value to the Match Stick.
    The radius value will be randomly chosen in reasonable range
	 */
	protected void RadiusAssign(int nPreserve)
	{
		double rMin, rMax;
		double nowRad, u_value, tempX;
		int i, j;
		// 0. initialize to negative value
		for (i= nPreserve+1; i<=nComponent; i++)
		{
			comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
		}
		// 1. assign at JuncPt
		for (i=1; i<=nJuncPt; i++)
		{
			if ( JuncPt[i].rad == 100.0) // a whole new JuncPt
			{
				rMin = -10.0; rMax = 100000.0;
				int nRelated_comp = JuncPt[i].nComp;
				for (j = 1 ; j <= nRelated_comp; j++)
				{
					rMin = Math.max( rMin, comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 10.0);
					tempX = Math.min( 0.5 *comp[JuncPt[i].comp[j]].mAxisInfo.rad,
							comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 3.0);
					rMax = Math.min( rMax, tempX);
				}

				if (rMax < rMin)
					System.out.println(" In radius assign, ERROR: rMax < rMin");

				// select a value btw rMin and rMax
				nowRad = stickMath_lib.randDouble( rMin, rMax);
				// assign the value to each component
				JuncPt[i].rad = nowRad;

				for (j = 1 ; j <= nRelated_comp ; j++)
				{
					u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
					if ( Math.abs( u_value - 0.0) < 0.0001)
					{
						comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
						comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
					}
					else if ( Math.abs(u_value - 1.0) < 0.0001)
					{
						comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
						comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
					}
					else // middle u value
					{
						comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
						comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
					}

				}
			}
			else // JuncPt.rad != 100.0, means this JuncPt is an existing one
			{
				for (j=1; j<= JuncPt[i].nComp; j++)
					if ( JuncPt[i].comp[j] > nPreserve) // the component which need to assign radius
					{
						nowRad = JuncPt[i].rad;
						u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
						if ( Math.abs( u_value - 0.0) < 0.0001)
						{
							try{
								comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
								comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
							}catch(Exception e){

							}
						}
						else if ( Math.abs(u_value - 1.0) < 0.0001)
						{
							comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
							comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
						}
						else // middle u value
						{
							comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
							comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
						}
					}

			}
		} // loop nJuncPt

		// 2. assign at endPt
		for ( i = 1 ;  i <= nEndPt ; i++)
			if ( endPt[i].comp > nPreserve ) // only do the radius assign for endPt with component we need
			{

				int nowComp = endPt[i].comp;
				u_value = ((double)endPt[i].uNdx -1.0 ) / (51.0 -1.0);

				//rMin = mStick.comp(nowComp).arcLen / 10.0;
				rMin = 0.00001; // as small as you like
				rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);

				// select a value btw rMin and rMax
				nowRad = stickMath_lib.randDouble( rMin, rMax);

				endPt[i].rad = nowRad;

				if ( Math.abs( u_value - 0.0) < 0.0001)
				{
					comp[nowComp].radInfo[0][0] = 0.0;
					comp[nowComp].radInfo[0][1] = nowRad;
				}
				else if (Math.abs(u_value - 1.0) < 0.0001)
				{
					comp[nowComp].radInfo[2][0] = 1.0;
					comp[nowComp].radInfo[2][1] = nowRad;
				}
				else // middle u value
					System.out.println( "error in endPt radius assignment");

			}

		// 3. other middle Pt
		for ( i = nPreserve+1 ; i <= nComponent ; i++)
			if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
			{
				int branchPt = comp[i].mAxisInfo.branchPt;
				u_value = ((double)branchPt-1.0) / (51.0 -1.0);

				rMin = comp[i].mAxisInfo.arcLen / 10.0;
				rMax = Math.min(comp[i].mAxisInfo.arcLen / 3.0, 0.5 * comp[i].mAxisInfo.rad);
				nowRad = stickMath_lib.randDouble( rMin, rMax);
				comp[i].radInfo[1][0] = u_value;
				comp[i].radInfo[1][1] = nowRad;
			}
	}

	// and one body, removes from that body but ignores the given limb.
	public void genRemovedLeafMatchStick() {

		while (true) {
			// 1. PICK OUT A LEAF TO DELETE
			boolean[] removeList = new boolean[comp.length];
			removeList[chooseRandLeaf()] = true;

			// 2. DO THE REMOVING
			removeComponent(removeList);

			// 3.
			// finalRotation = new double[3];
			// for (int i=0; i<3; i++)
			// finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			// debug

			// finalRotation[0] = 90.0;
			// finalRotation[1] = 0.0;
			// finalRotation[2] = 0;

			// this.finalRotateAllPoints(finalRotation[0], finalRotation[1],
			// finalRotation[2]);

			// this.centerShapeAtOrigin(-1);

			boolean res = smoothizeMStick();
			if (res == true) // success to smooth
				break; // else we need to gen another shape
			// else
			System.out.println("      Fail to smooth combine the shape. try again.");

		}

	}

	public void genMatchStickRand() {
		int nComp;
		// double nCompDist = { 0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		// double[] nCompDist = { 0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.00};
		// double[] nCompDist = {0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		double[] nCompDist = this.PARAM_nCompDist;
		nComp = stickMath_lib.pickFromProbDist(nCompDist);
		// nComp = 2;

		// debug
		// nComp = 4;

		// The way we write like this can guarantee that we try to
		// generate a shape with "specific" # of components

		while (true) {

			while (true) {
				if (genMatchStick_comp(nComp) == true)
					break;
				// else
				// System.out.println(" Attempt to gen shape fail. try again");
			}

			// finalRotation = new double[3];
			// for (int i=0; i<3; i++)
			// finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			// debug

			// finalRotation[0] = 90.0;
			// finalRotation[1] = 0.0;
			// finalRotation[2] = 0;

			// this.finalRotateAllPoints(finalRotation[0], finalRotation[1],
			// finalRotation[2]);

			this.centerShapeAtOrigin(-1);

			boolean res = smoothizeMStick();
			if (res == true) // success to smooth
				break; // else we need to gen another shape
			// else
			// System.out.println(" Fail to smooth combine the shape. try
			// again.");

		}


	}

	/**
    genMatchStick with nComp components
	 */
	public boolean genMatchStick_comp(int nComp)
	{
		boolean showDebug = false;
		//        System.out.println("  Start random MAxis Shape gen...");
		if ( showDebug)
			System.out.println("Generate new random mStick, with " + nComp + " components");
		int i;
		nComponent= nComp;
		//comp = new TubeComp[nComp+1];

		for (i=1; i<=nComp; i++)
			comp[i] = new TubeComp();
		// 1. create first component at the center of the space.
		createFirstComp();
		// 2. sequentially adding new components

		int nowComp = 2;
		double randNdx;
		boolean addSuccess;
		while (true)
		{
			if ( showDebug)
				System.out.println("adding new MAxis on, now # " +  nowComp);
			randNdx = stickMath_lib.rand01();
			if (randNdx < PROB_addToEndorJunc)
			{
				if (nJuncPt == 0 || stickMath_lib.rand01() < PROB_addToEnd_notJunc)
					addSuccess = Add_MStick(nowComp, 1);
				else
					addSuccess = Add_MStick(nowComp, 2);
			}
			else
			{
				if (stickMath_lib.rand01() < PROB_addTiptoBranch)
					addSuccess = Add_MStick(nowComp, 3);
				else
					addSuccess = Add_MStick(nowComp, 4);
			}
			if (addSuccess == true) // otherwise, we'll run this while loop again, and re-generate this component
				nowComp ++;
			if (nowComp == nComp+1)
				break;
		}

		//up to here, the eligible skeleton should be ready
		// 3. Assign the radius value
		RadiusAssign(0); // no component to preserve radius
		// 4. Apply the radius value onto each component
		for (i=1; i<=nComponent; i++)
		{
			if( comp[i].RadApplied_Factory() == false) // a fail application
			{
				return false;
			}
		}


		// 5. check if the final shape is not working ( collide after skin application)


		if ( finalTubeCollisionCheck() == true)
		{
			if ( showDebug)
				System.out.println("\n FAIL the final Tube collsion Check ....\n");
			return false;
		}


		// Dec 24th 2008
		// re-center the shape before do the validMStickSize check!
		this.centerShapeAtOrigin(-1);
		// this.normalizeMStickSize();

		//   System.out.println("after centering");
		if ( this.validMStickSize() ==  false)
		{
			if ( showDebug)
				System.out.println("\n FAIL the MStick size check ....\n");
			return false;
		}
		return true;
	}




	public int chooseRandLeaf() {
		decideLeafBranch();
		List<Integer> choosableList = new LinkedList<Integer>();
		for (int i = 0; i < nComponent; i++) {
			if (LeafBranch[i] == true) {
				choosableList.add(i);
			}
		}
		Collections.shuffle(choosableList);
		return choosableList.get(0);
	}

	/**
	 * function check if the MStick is inside a BOX or not <BR>
	 * ( to prevent a shape extend too much outside one dimension)
	 * 
	 * ADDED BY Allen Chen: checks if too small as well.
	 * Change detection to see if any of the vec points are outside the box rather than
	 * using radius method. 
	 */
	protected boolean validMStickSize() {
		double maxRadius = scaleForMAxisShape; // degree
		double screenDist = 500;
		double minRadius = minScaleForMAxisShape;
		double maxBoundInMm = screenDist * Math.tan(maxRadius * Math.PI / 180 / 2);
		double minBoundInMm = screenDist * Math.tan(minRadius * Math.PI / 180 / 2);
		int i, j;

		//Point3d ori = new Point3d(0.0, 0.0, 0.0);
		//double dis;
		//double maxDis = 0;
		double maxX=0;
		double maxY=0;
		for (i = 1; i <= nComponent; i++) {
			for (j = 1; j <= comp[i].nVect; j++) {
				double xLocation = scaleForMAxisShape * comp[i].vect_info[j].x;
				double yLocation = scaleForMAxisShape * comp[i].vect_info[j].y;
				//dis = comp[i].vect_info[j].distance(ori);

				if(xLocation > maxBoundInMm || comp[i].vect_info[j].x < -maxBoundInMm){
					System.out.println("AC:71923: TOO BIG");
					return false;
				}
				if(yLocation > maxBoundInMm || comp[i].vect_info[j].y < -maxBoundInMm){
					System.out.println("AC:71923: TOO BIG");
					return false;
				}
				if(Math.abs(xLocation)>maxX)
					maxX = Math.abs(xLocation);
				if(Math.abs(xLocation)>maxY)
					maxY = Math.abs(yLocation);
			}
		}
		if (maxX < minBoundInMm || maxY < minBoundInMm) {
			//System.out.println("AC:71923: " + maxX);
			//System.out.println("AC:71923: " + maxY);
			//return false;
		}


		return true;
	}


	public void setScale(double minScale, double maxScale) {
		minScaleForMAxisShape = minScale;
		scaleForMAxisShape = maxScale;
	}

	/**
    Adding a new MAxisArc to a MatchStick
    @param nowComp the index of the new added mAxis
    @param type type from 1~4, indicate the type of addition, eg. E2E, E2J, E2B, B2E
    ALLEN CHEN : Do not do ANY addition to the SpecialEnd

	 */
	protected boolean Add_MStick(int nowComp, int type)
	{
		// Add new component to a existing partial MStick
		// 4 types of addition are possible , specified by type
		// 1. type == 1: E2E connection
		// 2. type == 2: E2J connection
		// 3. type == 3: E2B connection
		// 4. type == 4: B2E conneciton

		//shared variable Delcaration
		boolean showDebug = false;
		//final double TangentSaveZone = Math.PI / 4.0;
		int i;
		int trialCount = 1; // an indicator that if something try too many time, then just give up
		if (showDebug)
		{
			System.out.println("In AddMStick: nowComp " + nowComp + " type: " + type);
			System.out.println("now nEndPt " + nEndPt + " , and nJuncPt " + nJuncPt);
		}
		// random get a new MAxisArc
		MAxisArc nowArc = new MAxisArc();
		nowArc.genArcRand();



		//debug
		// if (nowComp != 2)
		//  type = 2;
		// else
		//  type = 4;
		if (type == 1) // Adding the new Comp end-to-end
		{
			// 1. pick an endPt

			int nowPtNdx;
			trialCount = 1;
			while (true)
			{
				nowPtNdx = stickMath_lib.randInt(1, this.nEndPt);
				if (endPt[nowPtNdx].rad > 0.2 && nowPtNdx!= specialEnd)
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. trnasRot the nowArc to the correction configuration
			int alignedPt = 1;
			Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
			Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( oriTangent.angle(finalTangent) > TangentSaveZone ) // angle btw the two tangent vector
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


			// 3. update the EndPT to JuncPt
			nJuncPt++;
			int[] compList = { endPt[nowPtNdx].comp, nowComp};
			int[] uNdxList = { endPt[nowPtNdx].uNdx, 1};
			Vector3d[] tangentList = { oriTangent, finalTangent};
			JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, endPt[nowPtNdx].rad);
			comp[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

			// 2.5 call the function to check if this new arc is valid
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				JuncPt[nJuncPt] = null;
				nJuncPt--;
				return false;
			}
			// 4. generate new endPt
			endPt[nowPtNdx].setValue(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
			// 5. save this new Comp

		}
		else if (type == 2) // end to Junction connection
		{
			//1. pick a Junction Pt

			if (this.nJuncPt == 0)
			{
				System.out.println("ERROR, should not choose type 2 addition when nJuncPt = 0");
				return false;
			}
			int nowPtNdx = stickMath_lib.randInt(1, nJuncPt);
			//2. transRot the newComp
			int alignedPt = 1;
			Point3d finalPos = new Point3d(JuncPt[nowPtNdx].pos);
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{

				finalTangent = stickMath_lib.randomUnitVec();
				boolean flag = true;
				for (i=1; i<= JuncPt[nowPtNdx].nTangent; i++)
				{
					if ( finalTangent.angle(JuncPt[nowPtNdx].tangent[i]) <= TangentSaveZone){
						flag = false;
					}

				}
				if (flag == true) // i.e. all the tangent at this junction is ok for this new tangent
					break;
				if ( trialCount++ == 150) {
					return false;
				}


			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


			//3. update the JuncPt & endPt info and add the new Comp
			JuncPt_struct old_JuncInfo = new JuncPt_struct();
			old_JuncInfo.copyFrom(JuncPt[nowPtNdx]);
			JuncPt[nowPtNdx].addComp(nowComp, 1, nowArc.mTangent[1]);
			comp[nowComp].initSet(nowArc, false, 2);
			// 2.5 call the function to check if this new arc is valid
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				JuncPt[nowPtNdx].copyFrom(old_JuncInfo);
				return false;
			}
			nEndPt++;
			endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);

		}
		else if (type == 3) //end-to-branch connection
		{

			// 1. select a existing comp, with free branch
			int pickedComp;
			int nTries=0;
			while(true)
			{
				pickedComp = stickMath_lib.randInt(1, nowComp-1); // one of the existing component
				if ( comp[pickedComp].branchUsed == false)
					break;
				if (showDebug)
					System.out.println("pick tube with branch unused");
				nTries++;
				if(nTries>100)
					return false;
			}
			// 2. transrot the newComp
			int alignedPt = 1;
			int nowUNdx = comp[pickedComp].mAxisInfo.branchPt;
			Point3d finalPos = new Point3d( comp[pickedComp].mAxisInfo.mPts[nowUNdx]);
			Vector3d oriTangent1 = new Vector3d( comp[pickedComp].mAxisInfo.mTangent[nowUNdx]);
			Vector3d oriTangent2 = new Vector3d();
			Vector3d finalTangent = new Vector3d();
			oriTangent2.negate(oriTangent1);
			//System.out.println(oriTangent1);
			//System.out.println(oriTangent2);
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( finalTangent.angle(oriTangent1) > TangentSaveZone &&
						finalTangent.angle(oriTangent2) > TangentSaveZone    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check if newComp valid
			// 3. update the JuncPt & endPt info
			nJuncPt++;
			int[] compList = { pickedComp, nowComp};
			int[] uNdxList = { nowUNdx, 1};
			Vector3d[] tangentList = { oriTangent1, oriTangent2, finalTangent};
			int[] ownerList = { pickedComp, pickedComp, nowComp};
			double rad = 100.0;
			rad = comp[pickedComp].radInfo[1][1]; // if it is existing tube, then there will be a value
			//otherwise, it should be initial value of 100.0
			this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);
			//JuncPt[nJuncPt].showInfo();
			// 2.5 call the function to check if this new arc is valid
			comp[nowComp].initSet(nowArc, false, 3);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				JuncPt[nJuncPt] = null;
				nJuncPt--;
				return false;
			}
			nEndPt++;
			this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
			comp[pickedComp].branchUsed = true;


		}
		else if (type == 4) // add branch to the existing EndPt
		{
			// 1. pick an EndPt
			trialCount = 1;
			int nowPtNdx;
			trialCount = 1;
			while (true)
			{
				nowPtNdx = stickMath_lib.randInt(1, this.nEndPt);
				if (endPt[nowPtNdx].rad > 0.2 && nowPtNdx != specialEnd)
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. transRot newComp
			int nowUNdx = nowArc.branchPt;
			int alignedPt = nowUNdx;
			Vector3d rev_tangent = new Vector3d();
			Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
			Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();

				rev_tangent.negate(finalTangent);
				if ( oriTangent.angle(finalTangent) > TangentSaveZone &&
						oriTangent.angle(rev_tangent) > TangentSaveZone    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check Nearby Situtation
			// 3. update JuncPt & endPt info
			nJuncPt++;
			int[] compList = { endPt[nowPtNdx].comp, nowComp};
			int[] uNdxList = { endPt[nowPtNdx].uNdx, nowUNdx};
			Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
			int[] ownerList = {endPt[nowPtNdx].comp, nowComp, nowComp};
			double rad;
			rad = endPt[nowPtNdx].rad;
			this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

			// 2.5 call the function to check if this new arc is valid
			comp[nowComp].initSet(nowArc, true, 4);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				JuncPt[nJuncPt] = null;
				nJuncPt--;
				return false;
			}
			// 4. generate 2 new endPt
			this.endPt[nowPtNdx].setValue(nowComp, 1, nowArc.mPts[1], nowArc.mTangent[1], 100.0);
			nEndPt++;
			this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);

		}

		if ( showDebug)
			System.out.println("end of add tube func successfully");
		return true;
		// call the check function to see if the newly added component violate the skeleton nearby safety zone.
	}

	/**
    copy the whole structure
    New params to copy (Allen):
    specialEnd
    specialEndComp
	 */
	public void copyFrom(AllenMatchStick in)
	{
		int i;

		nComponent = in.nComponent;

		//AC ADDITIONS//
		specialEnd = in.specialEnd;
		specialEndComp = in.specialEndComp;
		baseComp = in.baseComp;
		///////////////

		for (i=1; i<=nComponent; i++) {
			comp[i] = new TubeComp();
			comp[i].copyFrom(in.comp[i]);
		}
		this.nEndPt = in.nEndPt;
		for (i=1; i<=nEndPt; i++) {
			endPt[i] = new EndPt_struct();
			endPt[i].copyFrom(in.endPt[i]);
		}
		this.nJuncPt = in.nJuncPt;
		for (i=1; i<=nJuncPt; i++) {
			JuncPt[i] = new JuncPt_struct();
			JuncPt[i].copyFrom(in.JuncPt[i]);
		}
		this.setObj1(in.getObj1()); 

		for (i=1; i<=nComponent; i++)
			LeafBranch[i] = in.LeafBranch[i];
	}
}
