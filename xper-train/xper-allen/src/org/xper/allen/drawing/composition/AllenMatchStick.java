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
public class AllenMatchStick extends MatchStick implements Serializable {

	protected final double PROB_addToEndorJunc = 0.5; // 60% add to end or
	// junction pt, 40% to the
	// branch
	protected final double PROB_addToEnd_notJunc = 0; // when "addtoEndorJunc",
	// 50% add to end, 50%
	// add to junc
	protected final double[] finalRotation = new double[3];
	protected double minScaleForMAxisShape;

	protected final double[] PARAM_nCompDist = {0, 0.33, 0.67, 1, 0.0, 0.0, 0.0, 0.0 };
	protected final double TangentSaveZone = Math.PI/64;

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

	public boolean genMetricMorphedLeafMatchStick(int leafToMorphIndx, AllenMatchStick amsToMorph) {
		MetricMorphParams mmp = new MetricMorphParams();
		mmp.orientationChance = 1;
		mmp.lengthChance = 1;
		mmp.radiusChance = 1;
		
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

	public class MetricMorphParams{
		double orientationChance; //chance to change orientation
		double lengthChance;
		double radiusChance;
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

		// we'll find this function need to share some sub_function with fineTuneComponent
		// 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
		int alignedPt;
		alignedPt = MutationSUB_determineHinge( id);

		int[] compLabel = new int[nComponent+1];
		int tangentTrialTimes = 0;
		compLabel = MutationSUB_compRelation2Target(id);

		//2. start picking new MAxisArc
		for (i=1; i<= nJuncPt; i++)
			for (j=1; j<= JuncPt[i].nComp; j++)
			{
				if ( JuncPt[i].comp[j] == id)
				{
					JuncPtFlg[i] = true;
					targetUNdx[i] = JuncPt[i].uNdx[j];
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
					nowArc.genMetricSimilarArc( this.comp[id].mAxisInfo, alignedPt, mmp.lengthChance, mmp.orientationChance);
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
				boolean closeHit = this.checkSkeletonNearby( nComponent);
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
				this.MutationSUB_radAssign2NewComp_Metric(id, old_radInfo, mmp.radiusChance);
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

		} //outtest while

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
				boolean onlyAddToJunc = false;
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
	protected void MutationSUB_radAssign2NewComp_Metric( int targetComp, double[][] oriValue, double radiusChance)
	{
		boolean showDebug = false;
		int i, j;
		double rMin, rMax;
		double nowRad= -100.0, u_value;
		double radiusScale;
		if(stickMath_lib.rand01() < radiusChance){
			radiusScale = stickMath_lib.randDouble(0.7, 1.3);
		}
		else{
			radiusScale = 1;
		}
		
		{
			i = targetComp;
			comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
		}

		//set old value at JuncPt
		for (i=1; i<=nJuncPt; i++)
		{
			for (j=1; j<= JuncPt[i].nComp; j++)
				if ( JuncPt[i].comp[j] == targetComp)
				{
					nowRad = JuncPt[i].rad * radiusScale;

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

		//set new value at end Pt --> AC Set to OLD VALUE!
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
				rMin = 0.00001; // as small as you like
				rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
				double[] rangeFractions = {0, 0.1}; //AC: modulate new rad profile lims. 
				// retrive the oriValue
				double oriRad = -10.0;
				if ( endPt[i].uNdx == 1)
					oriRad = oriValue[0][1];
				else if ( endPt[i].uNdx == 51)
					oriRad = oriValue[2][1];
				// select a value btw rMin and rMax
				double range = rMax - rMin;
				if ( oriRad < 0.0) {
					System.out.println("AC 103948: Generated random nowRad");
					nowRad = stickMath_lib.randDouble( rMin, rMax);
				}
				else // in the case where we have old value
				{
					nowRad = oriRad * radiusScale;
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
		if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
		{
			int branchPt = comp[i].mAxisInfo.branchPt;
			u_value = ((double)branchPt-1.0) / (51.0 -1.0);

			rMin = comp[i].mAxisInfo.arcLen / 10.0;
			rMax = Math.min(comp[i].mAxisInfo.arcLen / 3.0, 0.5 * comp[i].mAxisInfo.rad);
			// select a value btw rMin and rMax

			double oriRad = oriValue[1][1]; // the middle radius value
			double range = rMax - rMin;
			if ( oriRad < 0.0)
			{
				System.out.println("AC12380432: RANDOM RAD GENERATED");
				nowRad = stickMath_lib.randDouble( rMin, rMax);
			}
			else // in the case where we have old value
			{

				nowRad = oriRad * radiusScale;
				if ( showDebug)
				{
					System.out.println("In assign Rad, we have old value +" + oriRad);
					System.out.println("and new vlaue is " + nowRad);
				}
			}

			comp[i].radInfo[1][0] = u_value;
			comp[i].radInfo[1][1] = nowRad;
		}
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

	public boolean genMatchStickFromLeaf_comp(int leafIndx, int nComp, AllenMatchStick amsOfLeaf, boolean onlyAddToJunc){
		boolean showDebug = false;
		nComponent = nComp;
		int i;
		for (i=1; i<=nComponent; i++){
			comp[i] = new TubeComp();
		}

		//STARTING LEAF
		comp[1].copyFrom(amsOfLeaf.getTubeComp(leafIndx));
		
		//ALLEN DEBUG:
		System.out.println("AC99481: " + comp[1].radInfo[1][1]);

		//DEFINING END AND JUNCTION
		if(onlyAddToJunc){
			ArrayList<Integer> juncList= (ArrayList<Integer>) leafIndxToJuncPts(leafIndx, amsOfLeaf);
			ArrayList<Integer> endList= (ArrayList<Integer>) leafIndxToEndPts(leafIndx, amsOfLeaf);

			System.out.println("AC568529: " + amsOfLeaf.getEndPtStruct(endList.get(0)).comp);
			System.out.println("AC568529: " + amsOfLeaf.getJuncPtStruct(juncList.get(0)).comp[1]);
			
			//DEFINE JUCTION TO BE A JUNCTION FROM LEAF
			JuncPt_struct in_junc = amsOfLeaf.getJuncPtStruct(juncList.get(0));
			int jnComp = 1;
			int[] jCompList = {1};
			int[] juNdx_list = {in_junc.uNdx[1]};
			Point3d jpos = in_junc.pos;
			int jnTangent = 1;
			Vector3d[] jtangent_list = {in_junc.tangent[1]};
			int[] jtangentOwner_list = {1};
			double jrad = in_junc.rad;
			JuncPt[1] = new JuncPt_struct(jnComp, jCompList, juNdx_list, jpos, jnTangent, jtangent_list, jtangentOwner_list, jrad);

			//DEFINE END POINT TO BE SAME END POINT AS IN LEAF
			EndPt_struct in_end = amsOfLeaf.getEndPtStruct(endList.get(0));
			int enComp = 1;
			int euNdx = in_end.uNdx;
			Point3d epos = in_end.pos;
			Vector3d etangent = in_end.tangent;
			double erad = in_end.rad;
			endPt[1] = new EndPt_struct(enComp, euNdx, epos, etangent, erad);

			nJuncPt = 1;
			nEndPt = 1;
		}
		else{
			endPt[1] = new EndPt_struct(1, 1, comp[1].mAxisInfo.mPts[1], comp[1].mAxisInfo.mTangent[1] , 100.0);
			endPt[2] = new EndPt_struct(1, 51, comp[1].mAxisInfo.mPts[51], comp[1].mAxisInfo.mTangent[51], 100.0);
			nEndPt = 2;
		}

		//this.JuncPt = new JuncPt_struct()
		/////////////////////////////
		int add_trial = 0;
		int nowComp = 2;
		double randNdx;
		boolean addSuccess;
		while (true)
		{
			if ( showDebug)
				System.out.println("adding new MAxis on, now # " +  nowComp);
			randNdx = stickMath_lib.rand01();
			if (nComp==2){
				addSuccess = Add_MStick(nowComp, 2);
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

	// TODO: Convert this into a method that takes an arguement one limb/tube
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

			// TODO: Sometimes after removing the limb the resulting print is
			// all black. NEed to figure out what's wrong.
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


	// TODO: Figure out why this is not working...
	public void genMatchStickOfLeaf(int leaf, AllenMatchStick amsOfLeaf) {
		int nComp = 1;
		this.cleanData();

		this.nComponent = nComp;
		comp[1] = new TubeComp();

		while (true) {
			// STARTING LEAF
			comp[1].copyFrom(amsOfLeaf.getTubeComp(leaf));
			this.endPt[1] = new EndPt_struct(1, 1, comp[1].mAxisInfo.mPts[1], comp[1].mAxisInfo.mTangent[1], 100.0);
			this.endPt[2] = new EndPt_struct(1, 51, comp[1].mAxisInfo.mPts[51], comp[1].mAxisInfo.mTangent[51], 100.0);
			this.nEndPt = 2;
			this.nJuncPt = 0;

			// this.RadiusAssign(2); // KEEP FIRST ELEMENT SAME RADIUS
			while (comp[1].RadApplied_Factory() == false)
				;

			// this.finalRotation = new double[3];

			// for (int i=0; i<3; i++)
			// finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			// debug

			// finalRotation[0] = 90.0;
			// finalRotation[1] = 0.0;
			// finalRotation[2] = 0;

			// this.finalRotateAllPoints(finalRotation[0], finalRotation[1],
			// finalRotation[2]);

			// this.centerShapeAtOrigin(-1);

			boolean res = this.smoothizeMStick();
			if (res == true) // success to smooth
				break; // else we need to gen another shape
			// else
			// System.out.println(" Fail to smooth combine the shape. try
			// again.");
		}
	}

	public int chooseRandLeaf() {
		this.decideLeafBranch();
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
			return false;
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
    ALLEN CHEN : copy and pasting this here so it has access to the super class's tangentSaveZone

	 */
	protected boolean Add_MStick(int nowComp, int type)
	{ 
		super.TangentSaveZone = this.TangentSaveZone;
		return super.Add_MStick(nowComp, type);
	}

}
