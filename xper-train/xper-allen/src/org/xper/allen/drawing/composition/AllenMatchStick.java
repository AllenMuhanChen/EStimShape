package org.xper.allen.drawing.composition;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.*;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.noisy.ConcaveHull.Point;
import org.xper.allen.drawing.composition.noisy.NoiseMapCalculation;
import org.xper.allen.drawing.composition.noisy.NoisePositions;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorph;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.*;
import org.xper.utils.RGBColor;

/**
 * MatchStick class with ability to make deep clones and manipulations of shapes
 *
 * @author r2_allen
 *
 */
public class AllenMatchStick extends MatchStick {

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		AllenMatchStick other = (AllenMatchStick) obj;
		if (!Arrays.equals(JuncPt, other.JuncPt))
			return false;
		if (!Arrays.equals(getLeafBranch(), other.getLeafBranch()))
			return false;
		if (baseComp != other.baseComp)
			return false;
		if (!Arrays.equals(comp, other.comp))
			return false;
		if (!Arrays.equals(endPt, other.endPt))
			return false;
		if (nEndPt != other.nEndPt)
			return false;
		if (nJuncPt != other.nJuncPt)
			return false;
		if (obj1 == null) {
			if (other.obj1 != null)
				return false;
		} else if (!obj1.equals(other.obj1))
			return false;
		if (specialEnd == null) {
			if (other.specialEnd != null)
				return false;
		} else if (!specialEnd.equals(other.specialEnd))
			return false;
		if (specialEndComp == null) {
			if (other.specialEndComp != null)
				return false;
		} else if (!specialEndComp.equals(other.specialEndComp))
			return false;
		return true;
	}

	public static final double MAX_LEAF_TO_BASE_AREA_RATIO = 0.66;
	public static final double MIN_LEAF_TO_BASE_AREA_RATIO = 0.2;
	private AllenTubeComp[] comp = new AllenTubeComp[9];
	private int nEndPt;
	private int nJuncPt;
	protected EndPt_struct[] endPt = new EndPt_struct[50];
	private JuncPt_struct[] JuncPt = new JuncPt_struct[50];
	private MStickObj4Smooth obj1;
	private boolean[] LeafBranch = new boolean[10];

	private final double PROB_addToEndorJunc = 1; // 50% add to end or
	// junction pt, 50% to the
	// branch
	private final double PROB_addToEnd_notJunc = 0.3; // when "addtoEndorJunc",
	// 50% add to end, 50%
	// add to junc
	private final double PROB_addTiptoBranch = 0; 	// when "add new component to the branch is true"
	protected final double[] finalRotation = new double[3];
	private double minScaleForMAxisShape;

	private final double[] PARAM_nCompDist = {0, 1, 0, 0, 0.0, 0.0, 0.0, 0.0 };
//	private final double TangentSaveZone = Math.PI/64;
	private final double TangentSaveZone = Math.PI/6.0;

	//AC ADDITIONS
	private List<Integer> specialEnd = new ArrayList<Integer>();
	private List<Integer> specialEndComp= new ArrayList<Integer>();


	// VARIABLES FOR CONTRUCTING NOISE MAPS
	private Lims noiseChanceBounds;
	private NoiseType noiseType;
	private NoisePositions noiseNormalizedPositions;


	public AllenMatchStick() {
		setFinalRotation(this.finalRotation);
	}

	public AllenMatchStick(AllenMatchStick in) {
		this.copyFrom(in);
		setFinalRotation(this.finalRotation);
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

	public void drawNoiseMap() {
		setTextureType("2D");
		init();
		try {
			Thread.sleep(100);
		} catch (InterruptedException e) {
			e.printStackTrace();
		}
		drawNoiseMapSkeleton();

	}

	public void setNoiseParameters(NoiseParameters noiseParameters) {
		this.noiseChanceBounds = noiseParameters.getNoiseChanceBounds();
		this.noiseNormalizedPositions = noiseParameters.getNormalizedPositionBounds();
	}

	public void drawNoiseMapSkeleton() {
		if(this.noiseType==NoiseType.NONE) {
			return;
		}
		NoiseMapCalculation noiseMap = new NoiseMapCalculation(this, noiseChanceBounds, noiseNormalizedPositions);
		//		for(int i=1; i<=getnComponent(); i++) {
		//			getComp()[i].setLabel(i);
		////			if(i==1)
		//			getComp()[i].drawSurfPt(getScaleForMAxisShape(), noiseMap);
		//		}
		GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);

		getComp()[2].setLabel(2);
		getComp()[2].drawSurfPt(getScaleForMAxisShape(), noiseMap);

		getComp()[1].setLabel(1);
		getComp()[1].drawSurfPt(getScaleForMAxisShape(), noiseMap);

		boolean drawHull = false;
		if(drawHull) {
			drawHull(noiseMap, getScaleForMAxisShape());
		}
	}

	private void drawHull(NoiseMapCalculation noiseMap, double scaleFactor) {
		GL11.glDisable(GL11.GL_DEPTH_TEST);
		GL11.glLineWidth(2.0f);
		//GL11.gllin
		GL11.glColor3f(0.0f, 1.0f, 1.0f);
		GL11.glBegin(GL11.GL_LINES);
		//GL11.glBegin(GL11.GL_POINTS);
		// Point3d p1 = this.mAxisInfo.transRotHis_finalPos;
		ArrayList<Point> hullPoints = noiseMap.hull;

		//		GL11.glPolygonOffset(1, 1);
		for (int i=0; i<=hullPoints.size()-2; i++)
		{
			Point p1 = hullPoints.get(i);
			Point p2 = hullPoints.get(i+1);
			GL11.glVertex3d( p1.getX()*scaleFactor, p1.getY()*scaleFactor, 0);
			GL11.glVertex3d(p2.getX()*scaleFactor, p2.getY()*scaleFactor, 0);
		}
		//			GL11.glColor3f(0.f,0.f, 1.f);
		//			for (i=1; i<=50; i++)
		//			{
		//				Point3d p1 = getmAxisInfo().getmPts()[i];
		//				Point3d p2 = getmAxisInfo().getmPts()[i+1];
		//				GL11.glVertex3d( p1.x*scaleFactor, p1.y*scaleFactor, p1.z*scaleFactor);
		//				GL11.glVertex3d(p2.x*scaleFactor, p2.y*scaleFactor, p2.z*scaleFactor);
		//			}
		GL11.glEnd();
		GL11.glEnable(GL11.GL_LIGHTING);
		return;


	}

	public void drawSkeleton() {
		int i;
		boolean showComponents = false;
		if (showComponents)
			for (i=1; i<=getnComponent(); i++) {
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


				getComp()[i].drawSurfPt(colorCode[i-1],getScaleForMAxisShape());
			}
		else
			getObj1().drawVect();
	}

	public void drawGhost(){
		GL11.glShadeModel(GL11.GL_SMOOTH);
		GL11.glEnable(GL11.GL_AUTO_NORMAL);   // Automatic normal generation when doing NURBS, if not enabled we have to provide the normals ourselves if we want to have a lighted image (which we do).
		GL11.glEnable(GL11.GL_POLYGON_SMOOTH);
		GL11.glEnable(GL11.GL_BLEND);
		GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_SRC_ALPHA);

		initLight();
		getObj1().drawVectTranslucent(0.5F);
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

		this.setNowCenterTube(compToCenter);
		// Point3d nowComp1Center = new
		// Point3d(comp[compToCenter].mAxisInfo.mPts[comp[compToCenter].mAxisInfo.branchPt]);
		// Dec 26th, change .branchPt to .MiddlePT (i.e. always at middle)
		int midPtIndex = 26;
		Point3d nowComp1Center = new Point3d(getComp()[compToCenter].getmAxisInfo().getmPts()[midPtIndex]);
		Vector3d shiftVec = new Vector3d();
		shiftVec.sub(point, nowComp1Center);
		// System.out.println("comp to center "+ compToCenter);
		// System.out.println(nowComp1Center);
		if (point.distance(nowComp1Center) > 0.001) {
			if (showDebug)
				System.out.println("shift to make it center at origin!");
			Point3d finalPos = new Point3d();

			for (i = 1; i <= getnComponent(); i++) {
				finalPos.add(getComp()[i].getmAxisInfo().getTransRotHis_finalPos(), shiftVec);
				this.getComp()[i].translateComp(finalPos);
			}
			// also, all JuncPt and EndPt
			for (i = 1; i <= getnJuncPt(); i++) {
				getJuncPt()[i].getPos().add(shiftVec);
			}
			for (i = 1; i <= getnEndPt(); i++) {
				getEndPt()[i].getPos().add(shiftVec);
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
		boolean[] JuncPtFlg = new boolean[getnJuncPt() + 1]; // = true when this
		// JuncPt is related to
		// the (id) component
		int[] targetUNdx = new int[getnJuncPt() + 1]; // to save the target uNdx in
		// particular Junc pt
		if (showDebug)
			System.out.println("In replace component (AllenMatchStick), will replace comp " + id);
		// we'll find this function need to share some sub_function with
		// fineTuneComponent
		// 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
		int alignedPt;
		alignedPt = MutationSUB_determineHinge(id);
		Point3d alignedPos = new Point3d();
		alignedPos.set(getComp()[id].getmAxisInfo().getmPts()[alignedPt]);

		int[] compLabel = new int[getnComponent() + 1];
		int TangentTryTimes = 1;
		compLabel = MutationSUB_compRelation2Target(id);

		// debug, show compLabel
		// System.out.println("compLabel: ");
		// for (i=1; i<= nComponent; i++)
		// System.out.println("comp " + i + " with label" + compLabel[i]);
		// System.out.println("Hinge Pt is " + alignedPt);

		// 2. start picking new MAxisArc
		for (i = 1; i <= getnJuncPt(); i++)
			for (j = 1; j <= getJuncPt()[i].getnComp(); j++) {
				if (getJuncPt()[i].getComp()[j] == id) {
					JuncPtFlg[i] = true;
					targetUNdx[i] = getJuncPt()[i].getuNdx()[j];
				}
			}

		AllenMAxisArc nowArc;
		MatchStick old_MStick = new MatchStick();
		old_MStick.copyFrom(this);
		while (true) {
			while (true) {
				while (true) {

					// store back to old condition
					this.copyFrom(old_MStick);
					// random get a new MAxisArc
					nowArc = newArc();
					nowArc.genArcRand();

					Vector3d finalTangent = new Vector3d();

					if (maintainTangent) {
						finalTangent = old_MStick.getTubeComp(id).getmAxisInfo().getTransRotHis_finalTangent();
					} else {
						finalTangent = stickMath_lib.randomUnitVec();
					}

					double devAngle = stickMath_lib.randDouble(0, Math.PI * 2);
					nowArc.transRotMAxis(alignedPt, alignedPos, alignedPt, finalTangent, devAngle);
					boolean tangentFlg = true;
					Vector3d nowTangent = new Vector3d();
					for (i = 1; i <= getnJuncPt(); i++)
						if (JuncPtFlg[i] == true) {
							int uNdx = targetUNdx[i];
							boolean midBranchFlg = false;
							if (uNdx == 1)
								finalTangent.set(nowArc.getmTangent()[uNdx]);
							else if (uNdx == 51) {
								finalTangent.set(nowArc.getmTangent()[uNdx]);
								finalTangent.negate();
							} else // middle branch Pt
							{
								midBranchFlg = true;
								finalTangent.set(nowArc.getmTangent()[uNdx]);
							}
							// check the angle
							for (j = 1; j <= getJuncPt()[i].getnTangent(); j++)
								if (getJuncPt()[i].getTangentOwner()[j] != id) // don't
									// need
									// to
									// check
									// with
									// the
									// replaced
									// self
								{
									nowTangent = getJuncPt()[i].getTangent()[j]; // soft
									// copy
									// is
									// fine
									// here
									if (nowTangent.angle(finalTangent) <= getTangentSaveZone()) // angle
										// btw
										// the
										// two
										// tangent
										// vector
										tangentFlg = false;
									if (midBranchFlg == true) {
										finalTangent.negate();
										if (nowTangent.angle(finalTangent) <= getTangentSaveZone()) //
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
				for (i = 1; i <= getnJuncPt(); i++)
					if (JuncPtFlg[i] == true) {
						int nowUNdx = targetUNdx[i];
						finalTangent.set(nowArc.getmTangent()[nowUNdx]);
						if (targetUNdx[i] == 51)
							finalTangent.negate();
						Point3d newPos = nowArc.getmPts()[nowUNdx];
						Point3d shiftVec = new Point3d();
						shiftVec.sub(newPos, getJuncPt()[i].getPos());

						if (nowUNdx != alignedPt) // not the aligned one, we
							// need to translate
						{
							for (j = 1; j <= getJuncPt()[i].getnComp(); j++)
								if (getJuncPt()[i].getComp()[j] != id) {
									int nowCompNdx = getJuncPt()[i].getComp()[j];
									for (k = 1; k <= getnComponent(); k++)
										if (compLabel[k] == nowCompNdx) // the
											// one
											// should
											// move
											// with
											// nowCompNdx
										{
											int nowComp = k;
											Point3d finalPos = new Point3d();
											finalPos.add(getComp()[nowComp].getmAxisInfo().getTransRotHis_finalPos(), shiftVec);
											if (showDebug)
												System.out.println(
														"we have translate comp " + nowComp + "by " + shiftVec);
											this.getComp()[nowComp].translateComp(finalPos);
											// translate the component
										}
								}
						}

						getJuncPt()[i].setPos(newPos);
						// update the tangent information
						boolean secondFlg = false; // determine if the first or
						// second tanget
						for (j = 1; j <= getJuncPt()[i].getnTangent(); j++) {
							if (getJuncPt()[i].getTangentOwner()[j] == id && secondFlg == false) {
								getJuncPt()[i].getTangent()[j].set(finalTangent);
								secondFlg = true;
							} else if (getJuncPt()[i].getTangentOwner()[j] == id && secondFlg == true) {
								finalTangent.negate();
								getJuncPt()[i].getTangent()[j].set(finalTangent);
							}
						}
					}
				// now, we can check skeleton closeness

				// set the component to its new role
				boolean branchUsed = this.getComp()[id].isBranchUsed();
				int connectType = this.getComp()[id].getConnectType();
				this.getComp()[id] = new AllenTubeComp();
				this.getComp()[id].initSet(nowArc, branchUsed, connectType);
				boolean closeHit = this.checkSkeletonNearby(getnComponent());
				if (closeHit == false) // a safe skeleton
					break;

				inner_totalTrialTime++;
				if (inner_totalTrialTime > 25)
					return false;

			} // second while

			// update the info in end pt and JuncPt
			for (i = 1; i <= getnEndPt(); i++) {
				Point3d newPos = new Point3d(getComp()[getEndPt()[i].getComp()].getmAxisInfo().getmPts()[getEndPt()[i].getuNdx()]);
				getEndPt()[i].getPos().set(newPos);
			}
			for (i = 1; i <= getnJuncPt(); i++) {
				Point3d newPos = new Point3d(getComp()[getJuncPt()[i].getComp()[1]].getmAxisInfo().getmPts()[getJuncPt()[i].getuNdx()[1]]);
				getJuncPt()[i].getPos().set(newPos);
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
				if (getComp()[id].RadApplied_Factory() == false) {
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

	@Override
	protected AllenMAxisArc newArc() {
		return new AllenMAxisArc();
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


	public boolean genQualitativeMorphedLeafMatchStick(int leafToMorphIndx, AllenMatchStick amsToMorph, QualitativeMorphParams qmp) {
		int i = 0;
		AllenMatchStick backup = new AllenMatchStick();
		backup.copyFrom(amsToMorph);
		while (i<2) {
			// 1. DO THE MORPHING
			int j = 0;
			boolean success = false;
			while (j<10){
				// 0. Copy
				cleanData();
				copyFrom(backup);
				success = qualitativeMorphComponent(leafToMorphIndx, qmp);
				if(success){
					break;
				} else{
					j++;
				}
			}
			// this.MutateSUB_reAssignJunctionRadius(); //Keeping this off keeps
			// junctions similar to previous
			positionShape();
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

	protected void positionShape() {
//		centerShapeAtOrigin(getSpecialEndComp().get(0));
		centerCenterOfMassAtOrigin();
	}

	/**
	 *   A function that will put the center of comp1 back to origin
	 */
	public void centerCenterOfMassAtOrigin()
	{
		Point3d origin = new Point3d(0.0, 0.0, 0.0);

		Point3d centerOfMass = getMassCenter();
		Vector3d shiftVec = new Vector3d();
		shiftVec.sub(origin, centerOfMass);
		if ( origin.distance(centerOfMass) > 0.001)
		{
			applyTranslation(shiftVec);
		}
	}

	public Point3d getMassCenter(){
		Point3d cMass = new Point3d();
		int totalVect = 0;
		for (int i=1; i<=getnComponent(); i++)
		{
			totalVect += getComp()[i].getnVect();
			for (int j=1; j<= getComp()[i].getnVect(); j++)
				cMass.add(getComp()[i].getVect_info()[j]);
		}
		cMass.x /= totalVect;
		cMass.y /= totalVect;
		cMass.z /= totalVect;
		return cMass;
	}

	protected boolean qualitativeMorphComponent(int id, QualitativeMorphParams qmp)
	{

		if(qmp.removalFlag) {
			boolean[] removeList = new boolean[getComp().length];
			removeList[id] = true;

			// 2. DO THE REMOVING
			removeComponent(removeList);
			return true;
		}
		int i, j, k;
		int inner_totalTrialTime = 0;
		int TotalTrialTime = 0; // the # have tried, if too many, just terminate
		boolean showDebug = false;
		//final double TangentSaveZone = Math.PI / 4.0;
		boolean[] JuncPtFlg = new boolean[getnJuncPt()+1]; // = true when this JuncPt is related to the (id) component
		int[] targetUNdx = new int[getnJuncPt()+1]; // to save the target uNdx in particular Junc pt
		double[][] old_radInfo = new double[3][2];
		double[][] old_normalizedRadInfo = new double[3][2];
		getComp()[id].normalizeRadInfo();

		//0. Organizing morph parameters from QualitativeMorphParams
		//GETTING OLD VALUES
		Vector3d oriTangent = new Vector3d();
		//POSITION & ORIENTATION
		int newPosition=0;
		boolean positionFlag=false;
		int baseJuncNdx=0;

		//EVERYTHING THAT REQUIRES INFORMATION ABOUT JUNTIONS
		int radProfileJuncIndx = -1; //radProfile
		int radProfileEndIndx = -1;
		//Go through Juncs
		for(i=1; i<=getnJuncPt();i++) {
			for(j=1; j<= getJuncPt()[i].getnComp();j++) {
				if(getJuncPt()[i].getComp()[j]==id) {

					//If we've specified a comp to be the base that this limb moves along
					if(getBaseComp()!=0) {
						for(int l=1; l<=getJuncPt()[i].getnComp(); l++) {
							if(getJuncPt()[i].getComp()[l] == getBaseComp()) {
								baseJuncNdx = l;
							}
						}
					}
					//If not, choose a random comp that's attached to the target leaf
					else {
						LinkedList<Integer> baseJuncNdxList = new LinkedList<>();
						for(int l=1; l<=getJuncPt()[i].getnComp(); l++) {
							if(getJuncPt()[i].getComp()[l]!=id) {
								baseJuncNdxList.add(l);
							}
						}
						Collections.shuffle(baseJuncNdxList);
						baseJuncNdx = baseJuncNdxList.get(0);
					}
					int oriPosition = getJuncPt()[i].getuNdx()[baseJuncNdx];
					oriTangent = getJuncPt()[i].getTangent()[id];
					qmp.objCenteredPosQualMorph.loadParams(oriPosition, oriTangent);

					//Finding which radProfile indx is the junc
					double u_value = ((double)getJuncPt()[i].getuNdx()[j]-1.0) / (51.0-1.0);
					if ( Math.abs( u_value - 0.0) < 0.0001)
					{
						radProfileJuncIndx = 0;
						radProfileEndIndx = 2;
					}
					else if ( Math.abs(u_value - 1.0) < 0.0001)
					{
						radProfileJuncIndx = 2;
						radProfileEndIndx = 0;
					}
					else // middle u value
					{
						if(stickMath_lib.rand01()<0.5) {
							radProfileJuncIndx = 0;
							radProfileEndIndx = 2;
						}
						else {
							radProfileJuncIndx = 2;
							radProfileEndIndx = 0;
						}
					}
				}
			}

			//POSITION
			if(qmp.objectCenteredPositionFlag) {
				qmp.objCenteredPosQualMorph.calculateNewPosition();
				newPosition = qmp.objCenteredPosQualMorph.getNewPosition();
				positionFlag = qmp.objCenteredPosQualMorph.isPositionFlag();

				//ORIENTATION
				//Vector3d baseTangent = this.getComp()[getBaseComp()].getmAxisInfo().getmTangent()[newPosition];
				qmp.objCenteredPosQualMorph.calculateNewTangent();
			}
		} // Object Centered Position
		//CURVATURE AND ROTATION
		if(qmp.curvatureRotationFlag) {
			qmp.curvRotQualMorph.loadParams(getComp()[id].getmAxisInfo().getRad(), getComp()[id].getmAxisInfo().getTransRotHis_devAngle());
			qmp.curvRotQualMorph.calculate(getComp()[id].getmAxisInfo().getArcLen(),getComp()[id].getmAxisInfo());
		} // Curvature Rotation


		//SIZE: LENGTH & THICKNESS
		if(qmp.sizeFlag) {
			qmp.sizeQualMorph.loadParams(getComp()[id].getmAxisInfo().getArcLen(), getComp()[id].getScale());
			qmp.sizeQualMorph.calculate(getComp()[id].getmAxisInfo());
		}

		//RADPROFILE

		if(qmp.radProfileFlag) {
			double[][] normalizedRadInfo = getComp()[id].getNormalizedRadInfo();
			double oldJunc = normalizedRadInfo[radProfileJuncIndx][1];
			double oldMid = normalizedRadInfo[1][1];
			double oldEnd = normalizedRadInfo[radProfileEndIndx][1];
			qmp.radProfileQualMorph.loadParams(oldJunc, oldMid, oldEnd);
			qmp.radProfileQualMorph.calculate();
		}


		// 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
		int alignedPt;
		alignedPt = MutationSUB_determineHinge(id);

		int[] compLabel = new int[getnComponent()+1];
		int tangentTrialTimes = 0;
		compLabel = MutationSUB_compRelation2Target(id);

		//0. start picking new MAxisArc & POSITION MORPH
		for (i=1; i<= getnJuncPt(); i++)
			for (j=1; j<= getJuncPt()[i].getnComp(); j++)
			{
				if ( getJuncPt()[i].getComp()[j] == id)
				{

					JuncPtFlg[i] = true;

					if(positionFlag) {
						//This junction point is an end point of the target leaf
						if(getJuncPt()[i].getuNdx()[j] == 51 || getJuncPt()[i].getuNdx()[j] == 1) {
							//We need to change the uNdx of the limb the morphed limb is attached to
							getJuncPt()[i].getuNdx()[baseJuncNdx] = newPosition;

							//We let the mAxis code know the new position through this qmp object
							qmp.objCenteredPosQualMorph.setNewPositionCartesian(new Point3d(getComp()[getBaseComp()].getmAxisInfo().getmPts()[newPosition]));

							//The endPt's pos is automatically updated later in the code by using the position of the mAxis.
							//ALL we needed to do is update the info about the base comp since that is not updated later, and add any new juncs or end points
						}
						//This is a middle point of the target leaf- the only this is possible is if this leaf is attached to the end of another limb through this leaf's branch point
						else {
							//We can just change its position
							getJuncPt()[i].getuNdx()[j] = newPosition;
							//JuncPt[i].pos = new Point3d(comp[baseComp].mAxisInfo.mPts[nowPosition]);
							qmp.objCenteredPosQualMorph.setNewPositionCartesian(new Point3d(getComp()[getBaseComp()].getmAxisInfo().getmPts()[newPosition]));
							//Later code will handle assigning this JuncPt's pos
						}
						targetUNdx[i] = getJuncPt()[i].getuNdx()[j];
					}else {
						targetUNdx[i] = getJuncPt()[i].getuNdx()[j];
					}
				}

			}
		for (i=0; i<3; i++)
			for (j=0; j<2; j++) {
				old_radInfo[i][j] = getComp()[id].getRadInfo()[i][j];
				old_normalizedRadInfo[i][j] = getComp()[id].getNormalizedRadInfo()[i][j];
			}



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
					nowArc.genQualitativeMorphArc(getComp()[id].getmAxisInfo(), alignedPt, qmp);

					//for loop, check through related JuncPt for tangentSaveZone
					Vector3d finalTangent = new Vector3d();
					boolean tangentFlg = true;
					Vector3d nowTangent = new Vector3d();
					for (i=1; i<=getnJuncPt(); i++)
						if (JuncPtFlg[i])
						{
							int uNdx = targetUNdx[i];
							boolean midBranchFlg = false;
							if (uNdx == 1)
								finalTangent.set(nowArc.getmTangent()[uNdx]);
							else if (uNdx == 51)
							{
								finalTangent.set(nowArc.getmTangent()[uNdx]);
								finalTangent.negate();
							}
							else // middle branch Pt
							{
								midBranchFlg = true;
								finalTangent.set( nowArc.getmTangent()[uNdx]);
							}
							// check the angle
							for (j=1; j<= getJuncPt()[i].getnTangent(); j++)
								if ( getJuncPt()[i].getTangentOwner()[j] != id) // don't need to check with the replaced self
								{
									nowTangent = getJuncPt()[i].getTangent()[j]; // soft copy is fine here
									if ( nowTangent.angle(finalTangent) <= getTangentSaveZone() ) // angle btw the two tangent vector
										tangentFlg = false;
									if (midBranchFlg)
									{
										finalTangent.negate();
										if ( nowTangent.angle(finalTangent) <= getTangentSaveZone() ) //
											tangentFlg = false;
									}
								}

						}

					// still valid after all tangent check
					if (tangentFlg)
						break;
					else
					{

						if (showDebug)
							System.out.println("didn't pass check tagent Zone in fine tune");
					}
					if (tangentTrialTimes > 100)
						return false;
				} // third while, will quit after tangent Save Zone check passed


				//JUNCPT UPDATE!!!
				//update the information of the related JuncPt
				Vector3d finalTangent = new Vector3d();
				for (i=1; i<= getnJuncPt(); i++)
					if (JuncPtFlg[i])
					{
						int nowUNdx = targetUNdx[i];
						finalTangent.set(nowArc.getmTangent()[nowUNdx]);
						if (targetUNdx[i] == 51)
							finalTangent.negate();
						Point3d newPos = nowArc.getmPts()[ nowUNdx];
						Point3d shiftVec = new Point3d();
						shiftVec.sub(newPos, getJuncPt()[i].getPos());

						if ( nowUNdx != alignedPt) // not the aligned one, we need to translate
						{
							for (j=1; j<= getJuncPt()[i].getnComp(); j++)
								if ( getJuncPt()[i].getComp()[j] != id)
								{
									int nowCompNdx = getJuncPt()[i].getComp()[j];
									for (k=1; k<= getnComponent(); k++)
										if (compLabel[k] == nowCompNdx) // the one should move with nowCompNdx
										{
											int nowComp = k;
											Point3d finalPos =new Point3d();
											finalPos.add( getComp()[nowComp].getmAxisInfo().getTransRotHis_finalPos(), shiftVec);
											if ( showDebug)
												System.out.println("we have translate comp " + nowComp + "by " + shiftVec);
											this.getComp()[nowComp].translateComp( finalPos);
											// translate the component
										}
								}
						}
						getJuncPt()[i].setPos(newPos);


						//update the tangent information
						boolean secondFlg = false; // determine if the first or second tanget
						for ( j = 1; j <= getJuncPt()[i].getnTangent(); j++)
						{
							if (getJuncPt()[i].getTangentOwner()[j] == id && secondFlg == false)
							{
								getJuncPt()[i].getTangent()[j].set(finalTangent);
								secondFlg = true;
							}
							else if ( getJuncPt()[i].getTangentOwner()[j] == id && secondFlg == true)
							{
								finalTangent.negate();
								getJuncPt()[i].getTangent()[j].set(finalTangent);
							}
						}

					}
				// now, we can check skeleton closeness

				//set the component to its new role
				boolean branchUsed = this.getComp()[id].isBranchUsed();
				int connectType = this.getComp()[id].getConnectType();
				//this.getComp()[id] = new AllenTubeComp();
				this.getComp()[id].initSet( nowArc, branchUsed, connectType);
				if (showDebug)
					System.out.println("In qualitative morph component: tube to modify # " +id +" now check skeleton");
				boolean closeHit = checkSkeletonNearby(getnComponent());
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
			for (i=1; i<=getnEndPt(); i++)
			{
				Point3d newPos = new Point3d(getComp()[ getEndPt()[i].getComp()].getmAxisInfo().getmPts()[ getEndPt()[i].getuNdx()]);
				getEndPt()[i].getPos().set(newPos);
			}
			for (i=1; i<=getnJuncPt(); i++)
			{
				Point3d newPos = new Point3d( getComp()[getJuncPt()[i].getComp()[1]].getmAxisInfo().getmPts()[ getJuncPt()[i].getuNdx()[1]]);
				getJuncPt()[i].getPos().set(newPos);
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
				//				getComp()[id].normalizeRadInfo();
				MutationSUB_radAssign2NewComp_Qualitative(id, old_normalizedRadInfo, qmp);
				//comp[id].showRadiusInfo();
				if (getComp()[id].RadApplied_Factory() == false)
				{
					success_process = false;
					continue; // not a good radius, try another
				}

				if (finalTubeCollisionCheck() == true)
				{
					if ( showDebug)
						System.out.println("\n IN replace tube: FAIL the final Tube collsion Check ....\n\n");
					success_process = false;
				}
				positionShape();
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
		//		System.out.println("AC0000: " + getComp()[id].getmAxisInfo().getmTangent()[alignedPt].toString());
		if ( showDebug)
			System.out.println("successfully fine tune a tube");
		return true;
	}


	/**
    subFunction of: (replaceComponent, fineTuneComponent) <BR>
 Will determine the radius of the modified component
 If there is value in [][] oriValue, it is the radius value of the original component
	 */
	protected void MutationSUB_radAssign2NewComp_Qualitative( int targetComp, double[][] oriNormalizedValue, QualitativeMorphParams qmp)
	{
		boolean showDebug = false;
		int i, j;
		double rMin, rMax;
		double nowRad= -100.0, u_value;
		double radiusScale = getComp()[targetComp].getScale();

		if(qmp.sizeQualMorph.isThicknessFlag()) {
			radiusScale = qmp.sizeQualMorph.getNewThickness();
		}

		double[][] nowNormalizedValue = oriNormalizedValue;

		//set old value at JuncPt
		for (i=1; i<=getnJuncPt(); i++)
		{
			for (j=1; j<= getJuncPt()[i].getnComp(); j++)
				if ( getJuncPt()[i].getComp()[j] == targetComp)
				{

					u_value = ((double)getJuncPt()[i].getuNdx()[j]-1.0) / (51.0-1.0);

					if(qmp.radProfileQualMorph.isJuncEnabled()) {
						if ( Math.abs( u_value - 0.0) < 0.0001)
						{
							if(qmp.radProfileQualMorph.isJuncFlag()) {
								nowNormalizedValue[0][1] = qmp.radProfileQualMorph.getNewJunc();
							}
							nowRad = nowNormalizedValue[0][1] * radiusScale;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][0] = 0.0;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][1] = nowRad;
						}
						else if ( Math.abs(u_value - 1.0) < 0.0001)
						{
							if(qmp.radProfileQualMorph.isJuncFlag()) {
								nowNormalizedValue[2][1] = qmp.radProfileQualMorph.getNewJunc();
							}
							nowRad = nowNormalizedValue[2][1] * radiusScale;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][0] = 1.0;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][1] = nowRad;
						}
						else // middle u value
						{
							if(qmp.radProfileQualMorph.isJuncFlag()) {
								nowNormalizedValue[1][1] = qmp.radProfileQualMorph.getNewJunc();
							}
							nowRad = nowNormalizedValue[1][1] * radiusScale;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][0] = u_value;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][1] = nowRad;
						}
					} else { //if junc is disabled, that means we automatically set the junc radius to be what it was in the new location
						//						nowRad =  getJuncPt()[i].getRad();
						double base_u_value = ((double)getJuncPt()[i].getuNdx()[getJuncPt()[i].getIndexOfComp(getBaseComp())]-1.0) / (51.0-1.0);
						if ( Math.abs( base_u_value - 0.0) < 0.0001) {
							nowRad = getComp()[getBaseComp()].getRadInfo()[0][1];
						} else if (( Math.abs(base_u_value - 1.0) < 0.0001)){
							nowRad = getComp()[getBaseComp()].getRadInfo()[2][1];
						}
						else {
							nowRad = getComp()[getBaseComp()].getRadInfo()[1][1];
						}
						if ( Math.abs( u_value - 0.0) < 0.0001)
						{
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][0] = 0.0;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][1] = nowRad;
						}
						else if ( Math.abs(u_value - 1.0) < 0.0001)
						{
							//							nowRad = getComp()[getBaseComp()].getRadInfo()[2][1];
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][0] = 1.0;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][1] = nowRad;
						}
						else // middle u value
						{
							//							nowRad = getComp()[getBaseComp()].getRadInfo()[1][1];
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][0] = u_value;
							getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][1] = nowRad;
						}
					}
				}
		}

		//set new value at end Pt
		for (i=1; i<= getnEndPt(); i++)
			if (getEndPt()[i].getComp() == targetComp)
			{
				//update the information of this endPt, besides radius assignment
				Point3d newPos = new Point3d( getComp()[targetComp].getmAxisInfo().getmPts()[ getEndPt()[i].getuNdx()]);
				Vector3d newTangent = new Vector3d( getComp()[targetComp].getmAxisInfo().getmTangent()[ getEndPt()[i].getuNdx()]);
				if ( getEndPt()[i].getuNdx() == 51)
					newTangent.negate();
				getEndPt()[i].getPos().set(newPos);
				getEndPt()[i].getTangent().set(newTangent);

				//set radius
				u_value = ((double)getEndPt()[i].getuNdx()-1.0) / (51.0-1.0);
				int nowComp = targetComp;
				//rMin = 0.00001; // as small as you like
				//rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
				//double[] rangeFractions = {0, 0.1}; //AC: modulate new rad profile lims.
				// retrive the oriValue
				double oriRad;
				if ( getEndPt()[i].getuNdx() == 1) {
					oriRad = oriNormalizedValue[0][1];
				}
				else  //endPt[i].uNdx == 51
					oriRad = oriNormalizedValue[2][1];


				if(qmp.radProfileQualMorph.isEndFlag()) {
					nowRad = qmp.radProfileQualMorph.getNewEnd() * radiusScale;
				}
				else {
					nowRad = oriRad * radiusScale;
				}
				//			if(qmp.radProfileEndFlag) {
				//				qmp.radProfileEndMagnitude.oldValue = nowRad;
				//				qmp.radProfileEndMagnitude.min = 0.00001;
				//				qmp.radProfileEndMagnitude.max = Math.min( comp[targetComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[targetComp].mAxisInfo.rad);
				//				nowRad = qmp.radProfileEndMagnitude.calculateMagnitude();
				//			}

				getEndPt()[i].setRad(nowRad);

				if ( Math.abs( u_value - 0.0) < 0.0001)
				{
					getComp()[nowComp].getRadInfo()[0][0] = 0.0;
					getComp()[nowComp].getRadInfo()[0][1] = nowRad;
				}
				else if (Math.abs(u_value - 1.0) < 0.0001)
				{
					getComp()[nowComp].getRadInfo()[2][0] = 1.0;
					getComp()[nowComp].getRadInfo()[2][1] = nowRad;
				}
				else // middle u value
					System.out.println( "error in endPt radius assignment");
			}

		//set intermediate pt if not assigned yet
		i = targetComp;
		double oriRad = oriNormalizedValue[1][1]; // the middle radius value
		if(qmp.radProfileQualMorph.isMidFlag()) {
			nowRad = qmp.radProfileQualMorph.getNewMid() * radiusScale;
		} else {
			nowRad = oriRad * radiusScale;
		}
		int branchPt = getComp()[i].getmAxisInfo().getBranchPt();
		u_value = ((double)branchPt-1.0) / (51.0 -1.0);
		//	if ( qmp.radProfileMidFlag) // this component need a intermediate value
		//	{
		//		qmp.radProfileMidMagnitude.oldValue = nowRad;
		//		qmp.radProfileMidMagnitude.min = comp[targetComp].mAxisInfo.arcLen / 10.0;
		//		qmp.radProfileMidMagnitude.max = Math.min( comp[targetComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[targetComp].mAxisInfo.rad);
		//		nowRad = qmp.radProfileMidMagnitude.calculateMagnitude();
		//	}
		getComp()[i].getRadInfo()[1][0] = u_value;
		getComp()[i].getRadInfo()[1][1] = nowRad;
	}

	/**
	 * Apply radius, do tube collision check, center at origin, and smoothize.
	 * @return
	 */
	public boolean postProcessMatchStick() {
		boolean showDebug = false;
		// 4. Apply the radius value onto each component
		for (int i=1; i<=getnComponent(); i++)
		{
			if( getComp()[i].RadApplied_Factory() == false) // a fail application
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
		this.centerShapeAtOrigin(getSpecialEndComp().get(0));
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
		AllenMatchStick backup = new AllenMatchStick();
		backup.copyFrom(amsToMorph);
		while (i<2) {
			// 1. DO THE MORPHING
			int j = 0;
			boolean success = false;
			while (j<10){
				cleanData();
				copyFrom(new AllenMatchStick());
				copyFrom(backup);
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
			positionShape();
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
		boolean showDebug = false;
		//final double TangentSaveZone = Math.PI / 4.0;
		boolean[] JuncPtFlg = new boolean[getnJuncPt()+1]; // = true when this JuncPt is related to the (id) component
		int[] targetUNdx = new int[getnJuncPt()+1]; // to save the target uNdx in particular Junc pt
		double[][] old_radInfo = new double[3][2];

		// 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
		int alignedPt;
		alignedPt = MutationSUB_determineHinge(id);

		int[] compLabel = new int[getnComponent()+1];
		int tangentTrialTimes = 0;
		compLabel = MutationSUB_compRelation2Target(id);

		//0. start picking new MAxisArc & POSITION MORPH
		for (i=1; i<= getnJuncPt(); i++)
			for (j=1; j<= getJuncPt()[i].getnComp(); j++)
			{
				if ( getJuncPt()[i].getComp()[j] == id)
				{

					JuncPtFlg[i] = true;

					if(mmp.positionFlag) {
						//We need to find the Junc_index for the comp that the morphigng limb is attached to
						int baseJuncNdx=0;
						//If we've specified a comp to be the base that this limb moves along
						if(getBaseComp()!=0) {
							for(int l=1; l<=getJuncPt()[i].getnComp(); l++) {
								if(getJuncPt()[i].getComp()[l] == getBaseComp()) {
									baseJuncNdx = l;
								}
							}
						}
						//If not, choose a random comp that's attached to the target leaf
						else {
							LinkedList<Integer> baseJuncNdxList = new LinkedList<>();
							for(int l=1; l<=getJuncPt()[i].getnComp(); l++) {
								if(getJuncPt()[i].getComp()[l]!=id) {
									baseJuncNdxList.add(l);
								}
							}
							Collections.shuffle(baseJuncNdxList);
							baseJuncNdx = baseJuncNdxList.get(0);
						}


						int oriPosition = getJuncPt()[i].getuNdx()[baseJuncNdx];
						mmp.positionMagnitude.oldValue = oriPosition;
						int nowPosition = mmp.positionMagnitude.calculateMagnitude();

						//This junction point is an end point of the target leaf
						if(getJuncPt()[i].getuNdx()[j] == 51 || getJuncPt()[i].getuNdx()[j] == 1) {
							//add this point as an end point, because it will no longer be a junction
							setnEndPt(getnEndPt() + 1);
							getEndPt()[getnEndPt()] = new EndPt_struct(id, getJuncPt()[i].getuNdx()[j],
									getJuncPt()[i].getPos(), getJuncPt()[i].getTangent()[j], getJuncPt()[i].getRad() );

							//We need to change the uNdx of the limb the morphed limb is attached to
							getJuncPt()[i].getuNdx()[baseJuncNdx] = nowPosition;
							//Move our current junction point to a new location
							//JuncPt[i].pos = new Point3d(comp[baseComp].mAxisInfo.mPts[nowPosition]);

							//We let the mAxis code know the new position through this mmp object
							mmp.positionMagnitude.newPos = new Point3d(getComp()[getBaseComp()].getmAxisInfo().getmPts()[nowPosition]);;

							//The endPt's pos is automatically updated later in the code by using the position of the mAxis.
							//ALL we needed to do is update the info about the base comp since that is not updated later, and add any new juncs or end points
						}
						//This is a middle point of the target leaf- the only this is possible is if this leaf is attached to the end of another limb through this leaf's branch point
						else {
							//We can just change its position
							getJuncPt()[i].getuNdx()[j] = nowPosition;
							//JuncPt[i].pos = new Point3d(comp[baseComp].mAxisInfo.mPts[nowPosition]);
							mmp.positionMagnitude.newPos = new Point3d(getComp()[getBaseComp()].getmAxisInfo().getmPts()[nowPosition]);
							//Later code will handle assigning this JuncPt's pos
						}
						targetUNdx[i] = getJuncPt()[i].getuNdx()[j];
					}else {
						targetUNdx[i] = getJuncPt()[i].getuNdx()[j];
					}
				}

			}
		for (i=0; i<3; i++)
			for (j=0; j<2; j++) {
				old_radInfo[i][j] = getComp()[id].getRadInfo()[i][j];
			}



		AllenMAxisArc nowArc;
		AllenMatchStick old_MStick = new AllenMatchStick();
		old_MStick.copyFrom(this);

		// Radius Changes
		while (true)
		{
			// anything that changes the skeleton
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
					nowArc.genMetricSimilarArc(this.getComp()[id].getmAxisInfo(), alignedPt, mmp);
					// use this function to generate a similar arc

					//for loop, check through related JuncPt for tangentSaveZone
					Vector3d finalTangent = new Vector3d();
					boolean tangentFlg = true;
					Vector3d nowTangent = new Vector3d();
					for (i=1; i<=getnJuncPt(); i++)
						if ( JuncPtFlg[i] == true)
						{
							int uNdx = targetUNdx[i];
							boolean midBranchFlg = false;
							if (uNdx == 1)
								finalTangent.set(nowArc.getmTangent()[uNdx]);
							else if (uNdx == 51)
							{
								finalTangent.set(nowArc.getmTangent()[uNdx]);
								finalTangent.negate();
							}
							else // middle branch Pt
							{
								midBranchFlg = true;
								finalTangent.set( nowArc.getmTangent()[uNdx]);
							}
							// check the angle
							for (j=1; j<= getJuncPt()[i].getnTangent(); j++)
								if ( getJuncPt()[i].getTangentOwner()[j] != id) // don't need to check with the replaced self
								{
									nowTangent = getJuncPt()[i].getTangent()[j]; // soft copy is fine here
									if ( nowTangent.angle(finalTangent) <= getTangentSaveZone() ) // angle btw the two tangent vector
										tangentFlg = false;
									if ( midBranchFlg == true)
									{
										finalTangent.negate();
										if ( nowTangent.angle(finalTangent) <= getTangentSaveZone() ) //
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
				for (i=1; i<= getnJuncPt(); i++)
					if (JuncPtFlg[i] == true)
					{
						int nowUNdx = targetUNdx[i];
						finalTangent.set(nowArc.getmTangent()[nowUNdx]);
						if (targetUNdx[i] == 51)
							finalTangent.negate();
						Point3d newPos = nowArc.getmPts()[ nowUNdx];
						Point3d shiftVec = new Point3d();
						shiftVec.sub(newPos, getJuncPt()[i].getPos());

						if ( nowUNdx != alignedPt) // not the aligned one, we need to translate
						{
							for (j=1; j<= getJuncPt()[i].getnComp(); j++)
								if ( getJuncPt()[i].getComp()[j] != id)
								{
									int nowCompNdx = getJuncPt()[i].getComp()[j];
									for (k=1; k<= getnComponent(); k++)
										if (compLabel[k] == nowCompNdx) // the one should move with nowCompNdx
										{
											int nowComp = k;
											Point3d finalPos =new Point3d();
											finalPos.add( getComp()[nowComp].getmAxisInfo().getTransRotHis_finalPos(), shiftVec);
											if ( showDebug)
												System.out.println("we have translate comp " + nowComp + "by " + shiftVec);
											this.getComp()[nowComp].translateComp( finalPos);
											// translate the component
										}
								}
						}
						getJuncPt()[i].setPos(newPos);

						//update the tangent information
						boolean secondFlg = false; // determine if the first or second tanget
						for ( j = 1; j <= getJuncPt()[i].getnTangent(); j++)
						{
							if (getJuncPt()[i].getTangentOwner()[j] == id && secondFlg == false)
							{
								getJuncPt()[i].getTangent()[j].set(finalTangent);
								secondFlg = true;
							}
							else if ( getJuncPt()[i].getTangentOwner()[j] == id && secondFlg == true)
							{
								finalTangent.negate();
								getJuncPt()[i].getTangent()[j].set(finalTangent);
							}
						}

					}
				// now, we can check skeleton closeness

				//set the component to its new role
				boolean branchUsed = this.getComp()[id].isBranchUsed();
				int connectType = this.getComp()[id].getConnectType();
				this.getComp()[id] = new AllenTubeComp();
				this.getComp()[id].initSet( nowArc, branchUsed, connectType);
				if (showDebug)
					System.out.println("In fine tune: tube to modify # " +id +" now check skeleton");
				boolean closeHit = this.checkSkeletonNearby(getnComponent());
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
			for (i=1; i<=getnEndPt(); i++)
			{
				Point3d newPos = new Point3d(  getComp()[ getEndPt()[i].getComp()].getmAxisInfo().getmPts()[ getEndPt()[i].getuNdx()]);
				getEndPt()[i].getPos().set(newPos);
			}
			for (i=1; i<=getnJuncPt(); i++)
			{
				Point3d newPos = new Point3d( getComp()[getJuncPt()[i].getComp()[1]].getmAxisInfo().getmPts()[ getJuncPt()[i].getuNdx()[1]]);
				getJuncPt()[i].getPos().set(newPos);
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
				if ( getComp()[id].RadApplied_Factory() == false)
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
		double[] nCompDist = getPARAM_nCompDist();
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
				if (genMatchStickFromLeaf_comp(leafIndx, nComp, amsOfLeaf) == true){
					compSuccess = true;
					break;
				}
				else {
					j++;
//					System.out.println("Attempt "+j + " to generate comp");
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

			//TRY SMOOTHING THE SHAPE

			positionShape();
			boolean smoothSuccess = false;
			if(compSuccess){

				try {
					smoothSuccess = this.smoothizeMStick();
				} catch(Exception e){
					smoothSuccess = false;
				}
			}

			//VET THE RELATIVE SIZE BETWEEN LEAF AND BASE (IN TERMS OF BOUNDING BOX)
			boolean sizeVetSuccess = false;
			if (smoothSuccess == true){ // success to smooth
				sizeVetSuccess = vetLeafBaseSize(leafIndx);
				if(sizeVetSuccess) {
					return true;
				}
			}

			// else we need to gen another shape
			i++;
		}
		return false;
	}
	private boolean vetLeafBaseSize(int leafIndx) {
		int leafNVect = getComp()[leafIndx].getnVect();
		Point3d[] leafVect_info = getComp()[leafIndx].getVect_info();
		Point3d[] leafBox = getBoundingBox(leafNVect, leafVect_info);
		double leafArea = findAreaOfBox(leafBox);

		int baseNVect = getComp()[getBaseComp()].getnVect(); //TODO: could extend this beyond base, and add accessories
		Point3d[] baseVect_info = getComp()[getBaseComp()].getVect_info();
		Point3d[] baseBox = getBoundingBox(baseNVect, baseVect_info);
		double baseArea = findAreaOfBox(baseBox);


		if(leafArea < baseArea*MAX_LEAF_TO_BASE_AREA_RATIO && leafArea > baseArea*MIN_LEAF_TO_BASE_AREA_RATIO) {
			return true;
		}else {
			return false;
		}
	}

	public static double findAreaOfBox(Point3d[] box) {
		LinkedList<Double> x = new LinkedList<>();
		LinkedList<Double> y = new LinkedList<>();
		for(int k=0; k<box.length; k++) {
			x.add(box[k].getX());
			y.add(box[k].getY());
		}
		double length = Collections.max(x) - Collections.min(x);
		double width = Collections.max(y) - Collections.min(y);
		double leafArea = length*width;
		return leafArea;
	}
	private Point3d[] getBoundingBox(int nVect, Point3d[] vect_info) {
		Point3d[] box = new Point3d[2];
		box[0] = new Point3d(5000,5000,5000);
		box[1] = new Point3d(-5000,-5000,-5000);

		for (int i=1; i<= nVect; i++) {
			Point3d p1 = vect_info[i];

			box[1].x = Math.max(box[1].x, p1.x);
			box[1].y = Math.max(box[1].y, p1.y);
			box[1].z = Math.max(box[1].z, p1.z);

			box[0].x = Math.min(box[0].x, p1.x);
			box[0].y = Math.min(box[0].y, p1.y);
			box[0].z = Math.min(box[0].z, p1.z);
		}
		return box;
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
		for (i=1; i<=getnJuncPt(); i++)
		{
			for (j=1; j<= getJuncPt()[i].getnComp(); j++)
				if ( getJuncPt()[i].getComp()[j] == targetComp)
				{
					nowRad = getJuncPt()[i].getRad() * radiusScale;
					if(mmp.radProfileJuncFlag) {
						mmp.radProfileJuncMagnitude.oldValue = nowRad;
						mmp.radProfileJuncMagnitude.min = getComp()[targetComp].getmAxisInfo().getArcLen() / 10.0;
						mmp.radProfileJuncMagnitude.max = Math.min( getComp()[targetComp].getmAxisInfo().getArcLen() / 3.0, 0.5 * getComp()[targetComp].getmAxisInfo().getRad());
						nowRad = mmp.radProfileJuncMagnitude.calculateMagnitude();
					}

					u_value = ((double)getJuncPt()[i].getuNdx()[j]-1.0) / (51.0-1.0);
					if ( Math.abs( u_value - 0.0) < 0.0001)
					{
						getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][0] = 0.0;
						getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[0][1] = nowRad;
					}
					else if ( Math.abs(u_value - 1.0) < 0.0001)
					{
						getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][0] = 1.0;
						getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[2][1] = nowRad;
					}
					else // middle u value
					{
						getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][0] = u_value;
						getComp()[getJuncPt()[i].getComp()[j]].getRadInfo()[1][1] = nowRad;
					}
				}
		}

		//set new value at end Pt
		for (i=1; i<= getnEndPt(); i++)
			if (getEndPt()[i].getComp() == targetComp)
			{
				//update the information of this endPt, besides radius assignment
				Point3d newPos = new Point3d( getComp()[targetComp].getmAxisInfo().getmPts()[ getEndPt()[i].getuNdx()]);
				Vector3d newTangent = new Vector3d( getComp()[targetComp].getmAxisInfo().getmTangent()[ getEndPt()[i].getuNdx()]);
				if ( getEndPt()[i].getuNdx() == 51)
					newTangent.negate();
				getEndPt()[i].getPos().set(newPos);
				getEndPt()[i].getTangent().set(newTangent);

				//set radius
				u_value = ((double)getEndPt()[i].getuNdx()-1.0) / (51.0-1.0);
				int nowComp = targetComp;
				//rMin = 0.00001; // as small as you like
				//rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);
				//double[] rangeFractions = {0, 0.1}; //AC: modulate new rad profile lims.
				// retrive the oriValue
				double oriRad;
				if ( getEndPt()[i].getuNdx() == 1)
					oriRad = oriValue[0][1];
				else  //endPt[i].uNdx == 51
					oriRad = oriValue[2][1];

				nowRad = oriRad * radiusScale;
				if(mmp.radProfileEndFlag) {
					mmp.radProfileEndMagnitude.oldValue = nowRad;
					mmp.radProfileEndMagnitude.min = 0.00001;
					mmp.radProfileEndMagnitude.max = Math.min( getComp()[targetComp].getmAxisInfo().getArcLen() / 3.0, 0.5 * getComp()[targetComp].getmAxisInfo().getRad());
					nowRad = mmp.radProfileEndMagnitude.calculateMagnitude();
				}

				getEndPt()[i].setRad(nowRad);

				if ( Math.abs( u_value - 0.0) < 0.0001)
				{
					getComp()[nowComp].getRadInfo()[0][0] = 0.0;
					getComp()[nowComp].getRadInfo()[0][1] = nowRad;
				}
				else if (Math.abs(u_value - 1.0) < 0.0001)
				{
					getComp()[nowComp].getRadInfo()[2][0] = 1.0;
					getComp()[nowComp].getRadInfo()[2][1] = nowRad;
				}
				else // middle u value
					System.out.println( "error in endPt radius assignment");
			}

		//set intermediate pt if not assigned yet
		i = targetComp;
		double oriRad = oriValue[1][1]; // the middle radius value
		nowRad = oriRad * radiusScale;
		int branchPt = getComp()[i].getmAxisInfo().getBranchPt();
		u_value = ((double)branchPt-1.0) / (51.0 -1.0);
		if ( mmp.radProfileMidFlag) // this component need a intermediate value
		{
			mmp.radProfileMidMagnitude.oldValue = nowRad;
			mmp.radProfileMidMagnitude.min = getComp()[targetComp].getmAxisInfo().getArcLen() / 10.0;
			mmp.radProfileMidMagnitude.max = Math.min( getComp()[targetComp].getmAxisInfo().getArcLen() / 3.0, 0.5 * getComp()[targetComp].getmAxisInfo().getRad());
			nowRad = mmp.radProfileMidMagnitude.calculateMagnitude();
		}
		getComp()[i].getRadInfo()[1][0] = u_value;
		getComp()[i].getRadInfo()[1][1] = nowRad;
	}

	public List<Integer> leafIndxToEndPts(int leafIndex, AllenMatchStick ams) {
		ArrayList<Integer> output = new ArrayList<Integer>();
		for (int j = 1; j <= ams.getnEndPt(); j++) {
			if (ams.getEndPtStruct(j).getComp() == leafIndex)
				output.add(j);
		}
		return output;
	}

	public List<Integer> leafIndxToJuncPts(int leafIndex, AllenMatchStick ams) {
		ArrayList<Integer> output = new ArrayList<Integer>();
		for (int j = 1; j <= ams.getnJuncPt(); j++) {
			if (Arrays.asList(ams.getJuncPtStruct(j).getComp()).contains(leafIndex));
			output.add(j);
		}
		return output;
	}

	/**
	 * special end: endPt of a leaf that should never be in a E2E, E2J, E2B etc..
	 * specialEndComp: comp of the leaf that this end belongs to.
	 */

	public boolean genMatchStickFromLeaf_comp(int leafIndx, int nComp, AllenMatchStick amsOfLeaf){
		boolean showDebug = false;
		//nComp = 2;
		setnComponent(nComp);
		int i;
		for (i=1; i<=getnComponent(); i++){
			getComp()[i] = new AllenTubeComp();
		}

		//STARTING LEAF
		getComp()[1].copyFrom(amsOfLeaf.getTubeComp(leafIndx));
		double PROB_addToBaseEndNotBranch = 1;
		int add_trial = 0;
		int nowComp = 2;
		//double randNdx;
		boolean addSuccess;
		while (true)
		{
			//FINDING JUNCS AND ENDS THAT ARE ASSOCIATED WITH THE LEAF SPECIFIED BY LEAFINDX
			ArrayList<Integer> juncList= (ArrayList<Integer>) leafIndxToJuncPts(leafIndx, amsOfLeaf);
			ArrayList<Integer> endList= (ArrayList<Integer>) leafIndxToEndPts(leafIndx, amsOfLeaf);

			EndPt_struct specialEnd = new EndPt_struct();
			JuncPt_struct notSpecialJunc = new JuncPt_struct();
			EndPt_struct notSpecialEnd = new EndPt_struct();
			//CHOOSE JUNC FROM LEAF
			int compIndx;
			int nseUNdx = 0;
			Point3d nsePos = new Point3d();
			Vector3d nseTangent = new Vector3d();
			double nseRad = 0;
			for(int juncIndx : juncList) {
				compIndx = amsOfLeaf.getJuncPt()[juncIndx].getIndexOfComp(leafIndx);
				int junc_uNdx = amsOfLeaf.getJuncPt()[juncIndx].getuNdx()[compIndx];


				//JUNC IS AN END
				if(junc_uNdx == 51 || junc_uNdx == 1) {
					notSpecialJunc.copyFrom(amsOfLeaf.getJuncPt()[juncIndx]);

					//SET NOT-SPECIAL END PARAMS BASED OFF THIS JUNC
					compIndx = notSpecialJunc.getIndexOfComp(leafIndx);
					nseUNdx = notSpecialJunc.getuNdx()[compIndx];
					nsePos = notSpecialJunc.getPos();
					nseTangent = notSpecialJunc.getTangent()[compIndx];
					nseRad = notSpecialJunc.getRad();

					//DEFINE SPECIAL END TO BE THE OTHER END PT
					specialEnd = new EndPt_struct();
					for(int endIndx: endList) {
						int end_uNdx = amsOfLeaf.getEndPtStruct(endIndx).getuNdx();
						boolean notJuncFlag = end_uNdx!=nseUNdx;
						boolean notBranchFlag = end_uNdx==1 || end_uNdx==51;
						if(notJuncFlag&&notBranchFlag) {
							specialEnd.copyFrom(amsOfLeaf.getEndPtStruct(endIndx));
						}
					}
				}
				//JUNC IS A MID POINT
				else { //THERE SHOULD BE TWO END POINTS, ONE AT 1 and ANOTHER AT 51
					for(int endIndx: endList) {
						int end_uNdx = amsOfLeaf.getEndPtStruct(endIndx).getuNdx();

						if(end_uNdx==1) {
							notSpecialEnd.copyFrom(amsOfLeaf.getEndPtStruct(endIndx));
						}
						else if(end_uNdx == 51) {
							specialEnd.copyFrom(amsOfLeaf.getEndPtStruct(endIndx));
						}
					}
					nseUNdx = notSpecialEnd.getuNdx();
					nsePos = notSpecialEnd.getPos();
					nseTangent = notSpecialEnd.getTangent();
					nseRad = notSpecialEnd.getRad();
				}
			}

			//DEFINE SPECIAL END TO BE THE END THAT IS NOT PREVIOUSLY A JUNC
			if(getSpecialEndComp().isEmpty())
				getSpecialEndComp().add(1);
			if(getSpecialEnd().isEmpty());
			getSpecialEnd().add(1);

			int seComp = getSpecialEndComp().get(0);
			int seUNdx = specialEnd.getuNdx();
			Point3d sePos = specialEnd.getPos();
			Vector3d seTangent = specialEnd.getTangent();
			double seRad = specialEnd.getRad();

			getEndPt()[getSpecialEnd().get(0)] = new EndPt_struct(seComp, seUNdx, sePos, seTangent, seRad);
			getEndPt()[getSpecialEnd().get(0)+1] = new EndPt_struct(seComp, nseUNdx, nsePos, nseTangent, nseRad);


			setnJuncPt(0);
			setnEndPt(2);

			//ROTATION INFORMATION
			AllenMAxisArc specialMAxis = getComp()[getSpecialEndComp().get(0)].getmAxisInfo();
			//			specialMAxis.setTransRotHis_alignedPt(getComp());
			//			getComp()[1].getmAxisInfo().setTransRotHis_alignedPt(nseUNdx);
			//			getComp()[1].getmAxisInfo().setTransRotHis_finalPos(getComp()[1].getmAxisInfo().getmPts()[nseUNdx]);
			//			getComp()[1].getmAxisInfo().setTransRotHis_rotCenter(nseUNdx);
			//			getComp()[1].getmAxisInfo().setTransRotHis_finalTangent(getComp()[1].getmAxisInfo().getmTangent()[nseUNdx]);
			//			getComp()[1].getmAxisInfo().setTransRotHis_devAngle(transRotHis_devAngle);

			////////////////////////////////////////////
			//ADD THE SECOND LIMB- FOLLOWS SPECIAL RULES
			////////////////////////////////////////////
			//Add E2J
			if(stickMath_lib.rand01()<PROB_addToBaseEndNotBranch) {
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
		//ADD ACCESSORY LIMBS - FOLLOWS SPECIAL RULES
		///////////////////////////////////////////////////////////////////////////
		add_trial = 0;
		double randNdx;
		addSuccess = false;
		while (true && nowComp <= nComp)
		{
			if ( showDebug)
				System.out.println("adding new MAxis on, now # " +  nowComp);
			randNdx = stickMath_lib.rand01();
			if (randNdx < getPROB_addToEndorJunc())
			{
				if (getnJuncPt() == 0 || stickMath_lib.rand01() < getPROB_addToEnd_notJunc())
					addSuccess = Add_AccessoryMStick(nowComp, 1);
				else
					addSuccess = Add_AccessoryMStick(nowComp, 2);
			}
			else
			{
				if (stickMath_lib.rand01() < getPROB_addTiptoBranch())
					addSuccess = Add_AccessoryMStick(nowComp, 3);
				else
					addSuccess = Add_AccessoryMStick(nowComp, 4);
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
		for (i=1; i<=getnComponent(); i++)
		{
			if( this.getComp()[i].RadApplied_Factory() == false) // a fail application
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
		this.centerShapeAtOrigin(getSpecialEndComp().get(0));

		if ( this.validMStickSize() ==  false)
		{
//			System.err.println("FAIL AT VALIDSIZE");
			if ( showDebug)
				System.out.println("\n FAIL the MStick size check ....\n");
			return false;
		}



		return true;


	}

	private int baseComp = 0;
	protected boolean Add_BaseMStick(int nowComp, int type) {
		boolean showDebug = false;
		//Base System: a single leaf is pre-defined to have one end and one juncion. The base is formed by adding to this junction
		//point, either E2J or B2J.
		//Add a new component to an existing MStick (there should only be one MStick)
		//1. type==1: E2J (Add end to end onto the end that used to be a junction)
		//2. type==2: B2J (Add a branch pt on the new BaseMStick and add the end that used to be a junction)

		//shared variable Delcaration
		//final double TangentSaveZone = Math.PI / 4.0;
		int i;
		int trialCount = 1; // an indicator that if something try too many time, then just give up

		// random get a new MAxisArc
		AllenMAxisArc nowArc = new AllenMAxisArc();
		nowArc.genArcRand();

		// type 1 base add
		if(type == 1) {

			// 1. pick an endPt - nowPtNDx
			int nowPtNdx;
			trialCount = 1;

			nowPtNdx = 2;
			if(nowPtNdx==getSpecialEnd().get(0)) {
				System.out.println("ERROR! We should not be adding to the special end");
				return false;
			}

			// 2. trnasRot the nowArc to the correction configuration
			int alignedPt = 1;
			Point3d finalPos = new Point3d(getEndPt()[nowPtNdx].getPos());
			Vector3d oriTangent = new Vector3d(getEndPt()[nowPtNdx].getTangent());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( oriTangent.angle(finalTangent) > getTangentSaveZone() ) // angle btw the two tangent vector
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


			// 3. update the EndPT to JuncPt
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { getEndPt()[nowPtNdx].getComp(), nowComp};
			int[] uNdxList = { getEndPt()[nowPtNdx].getuNdx(), alignedPt};
			Vector3d[] tangentList = { oriTangent, finalTangent};
			getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, getEndPt()[nowPtNdx].getRad());
			getComp()[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

			// 4. replace old endPt with new endPt
			getEndPt()[nowPtNdx] = null;
			getEndPt()[nowPtNdx] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], nowArc.getRad());

			//			 2.5 call the function to check if this new arc is valid
			if (checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}

			// 5. Update the baseComp
			setBaseComp(nowComp);
		}
		//2. type 2 base add
		else if(type == 2) {
			// 1. pick an EndPt
			trialCount = 1;
			int nowPtNdx;
			trialCount = 1;
			while (true)
			{
				nowPtNdx = stickMath_lib.randInt(1, getnEndPt());
				if (nowPtNdx != getSpecialEnd().get(0))
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. transRot newComp
			int nowUNdx = nowArc.getBranchPt();
			int alignedPt = nowUNdx;
			Vector3d rev_tangent = new Vector3d();
			Point3d finalPos = new Point3d(getEndPt()[nowPtNdx].getPos());
			Vector3d oriTangent = new Vector3d(getEndPt()[nowPtNdx].getTangent());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();

				rev_tangent.negate(finalTangent);
				if ( oriTangent.angle(finalTangent) > getTangentSaveZone() &&
						oriTangent.angle(rev_tangent) > getTangentSaveZone()    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check Nearby Situtation
			// 3. update JuncPt & endPt info
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { getEndPt()[nowPtNdx].getComp(), nowComp};
			int[] uNdxList = { getEndPt()[nowPtNdx].getuNdx(), nowUNdx};
			Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
			int[] ownerList = {getEndPt()[nowPtNdx].getComp(), nowComp, nowComp};
			double rad;
			rad = getEndPt()[nowPtNdx].getRad();
			this.getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

			// 2.5 call the function to check if this new arc is valid
			getComp()[nowComp].initSet(nowArc, true, 4);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			// 4. generate 2 new endPt
			this.getEndPt()[nowPtNdx].setValue(nowComp, 1, nowArc.getmPts()[1], nowArc.getmTangent()[1], 100.0);
			setnEndPt(getnEndPt() + 1);
			this.getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);
			//5. Update the baseComp
			setBaseComp(nowComp);
		}

		if ( showDebug)
			System.out.println("end of add tube func successfully");
		return true;
		// call the check function to see if the newly added component violate the skeleton nearby safety zone.
	}
	/**
	 * Used by genMatchStickFromLeaf_comp
	 * For adding match sticks beyond the base match stick
	 * Decides based on how many comps there are what kind of addition to do
	 * @param nowComp
	 * @param type
	 * @return
	 */
	protected boolean Add_AccessoryMStick(int nowComp, int type) {
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
			System.out.println("now nEndPt " + getnEndPt() + " , and nJuncPt " + getnJuncPt());
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
				nowPtNdx = stickMath_lib.randInt(1, this.getnEndPt());
				if (getEndPt()[nowPtNdx].getRad() > 0.2 && nowPtNdx!= getSpecialEnd().get(0))
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. trnasRot the nowArc to the correction configuration
			int alignedPt = 1;
			Point3d finalPos = new Point3d(getEndPt()[nowPtNdx].getPos());
			Vector3d oriTangent = new Vector3d(getEndPt()[nowPtNdx].getTangent());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( oriTangent.angle(finalTangent) > getTangentSaveZone() ) // angle btw the two tangent vector
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


			// 3. update the EndPT to JuncPt
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { getEndPt()[nowPtNdx].getComp(), nowComp};
			int[] uNdxList = { getEndPt()[nowPtNdx].getuNdx(), 1};
			Vector3d[] tangentList = { oriTangent, finalTangent};
			getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, getEndPt()[nowPtNdx].getRad());
			getComp()[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

			// 2.5 call the function to check if this new arc is valid
			if (checkSkeletonNearby(nowComp))
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			// 4. generate new endPt
			getEndPt()[nowPtNdx].setValue(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);
			// 5. save this new Comp

		}
		else if (type == 2) // end to Junction connection
		{
			//1. pick a Junction Pt

			if (this.getnJuncPt() == 0)
			{
				System.out.println("ERROR, should not choose type 2 addition when nJuncPt = 0");
				return false;
			}
			int nowPtNdx = stickMath_lib.randInt(1, getnJuncPt());
			//2. transRot the newComp
			int alignedPt = 1;
			Point3d finalPos = new Point3d(getJuncPt()[nowPtNdx].getPos());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{

				finalTangent = stickMath_lib.randomUnitVec();
				boolean flag = true;
				for (i=1; i<= getJuncPt()[nowPtNdx].getnTangent(); i++)
				{
					if ( finalTangent.angle(getJuncPt()[nowPtNdx].getTangent()[i]) <= getTangentSaveZone()){
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
			old_JuncInfo.copyFrom(getJuncPt()[nowPtNdx]);
			getJuncPt()[nowPtNdx].addComp(nowComp, 1, nowArc.getmTangent()[1]);
			getComp()[nowComp].initSet(nowArc, false, 2);
			// 2.5 call the function to check if this new arc is valid
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[nowPtNdx].copyFrom(old_JuncInfo);
				return false;
			}
			setnEndPt(getnEndPt() + 1);
			getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);

		}
		else if (type == 3) //end-to-branch connection
		{

			// 1. select a existing comp that is not the special comp.
			int pickedComp;
			int nTries=0;
			while(true)
			{
				pickedComp = stickMath_lib.randInt(1, nowComp-1); // one of the existing component
				if (pickedComp!=getSpecialEndComp().get(0))
					break;
				nTries++;
				if(nTries>100)
					return false;
			}
			// 2. transrot the newComp
			int alignedPt = 1;
			int nowUNdx = getComp()[pickedComp].getmAxisInfo().getBranchPt();
			Point3d finalPos = new Point3d( getComp()[pickedComp].getmAxisInfo().getmPts()[nowUNdx]);
			Vector3d oriTangent1 = new Vector3d( getComp()[pickedComp].getmAxisInfo().getmTangent()[nowUNdx]);
			Vector3d oriTangent2 = new Vector3d();
			Vector3d finalTangent = new Vector3d();
			oriTangent2.negate(oriTangent1);
			//System.out.println(oriTangent1);
			//System.out.println(oriTangent2);
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( finalTangent.angle(oriTangent1) > getTangentSaveZone() &&
						finalTangent.angle(oriTangent2) > getTangentSaveZone()    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check if newComp valid
			// 3. update the JuncPt & endPt info
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { pickedComp, nowComp};
			int[] uNdxList = { nowUNdx, 1};
			Vector3d[] tangentList = { oriTangent1, oriTangent2, finalTangent};
			int[] ownerList = { pickedComp, pickedComp, nowComp};
			double rad = 100.0;
			rad = getComp()[pickedComp].getRadInfo()[1][1]; // if it is existing tube, then there will be a value
			//otherwise, it should be initial value of 100.0
			this.getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);
			//JuncPt[nJuncPt].showInfo();
			// 2.5 call the function to check if this new arc is valid
			getComp()[nowComp].initSet(nowArc, false, 3);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			setnEndPt(getnEndPt() + 1);
			this.getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);
			getComp()[pickedComp].setBranchUsed(true);


		}
		else if (type == 4) // add branch to the existing EndPt
		{
			// 1. pick an EndPt
			trialCount = 1;
			int nowPtNdx;
			trialCount = 1;
			while (true)
			{
				nowPtNdx = stickMath_lib.randInt(1, this.getnEndPt());
				if (getEndPt()[nowPtNdx].getRad() > 0.2 && nowPtNdx != getSpecialEnd().get(0))
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. transRot newComp
			int nowUNdx = nowArc.getBranchPt();
			int alignedPt = nowUNdx;
			Vector3d rev_tangent = new Vector3d();
			Point3d finalPos = new Point3d(getEndPt()[nowPtNdx].getPos());
			Vector3d oriTangent = new Vector3d(getEndPt()[nowPtNdx].getTangent());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();

				rev_tangent.negate(finalTangent);
				if ( oriTangent.angle(finalTangent) > getTangentSaveZone() &&
						oriTangent.angle(rev_tangent) > getTangentSaveZone()    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check Nearby Situtation
			// 3. update JuncPt & endPt info
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { getEndPt()[nowPtNdx].getComp(), nowComp};
			int[] uNdxList = { getEndPt()[nowPtNdx].getuNdx(), nowUNdx};
			Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
			int[] ownerList = {getEndPt()[nowPtNdx].getComp(), nowComp, nowComp};
			double rad;
			rad = getEndPt()[nowPtNdx].getRad();
			this.getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

			// 2.5 call the function to check if this new arc is valid
			getComp()[nowComp].initSet(nowArc, true, 4);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			// 4. generate 2 new endPt
			this.getEndPt()[nowPtNdx].setValue(nowComp, 1, nowArc.getmPts()[1], nowArc.getmTangent()[1], 100.0);
			setnEndPt(getnEndPt() + 1);
			this.getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);

		}

		if ( showDebug)
			System.out.println("end of add tube func successfully");
		return true;
		// call the check function to see if the newly added component violate the skeleton nearby safety zone.
	}

	// and one body, removes from that body but ignores the given limb.
	public void genRemovedLeafMatchStick() {

		while (true) {
			// 1. PICK OUT A LEAF TO DELETE
			boolean[] removeList = new boolean[getComp().length];
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

	public void genMatchStickRandSuper(){
		super.genMatchStickRand();
	}

	public void genMatchStickRand() {
		int nComp;
//		 double[] nCompDist = { 0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
//		 double[] nCompDist = { 0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.00};
		// double[] nCompDist = {0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		double[] nCompDist = this.getPARAM_nCompDist();
		nComp = stickMath_lib.pickFromProbDist(nCompDist);
		// nComp = 2;

		// debug
		// nComp = 4;

		// The way we write like this can guarantee that we try to
		// generate a shape with "specific" # of components

		while (true) {

			while (true) {
//				System.err.println("Try Rand");
				if (genMatchStick_comp(nComp) == true) {
					break;
				}
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

			positionShape();

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
    The first component generated is set as the baseComp
    The rest of the components are all set as special ends.
	 */
	public boolean genMatchStick_comp(int nComp)
	{
		boolean showDebug = false;
		//        System.out.println("  Start random MAxis Shape gen...");
		if ( showDebug)
			System.out.println("Generate new random mStick, with " + nComp + " components");
		int i;
		setnComponent(nComp);
		//comp = new TubeComp[nComp+1];

		for (i=1; i<=nComp; i++)
			getComp()[i] = new AllenTubeComp();
		// 1. create first component at the center of the space.
		createFirstComp();
		setBaseComp(1);
		// 2. sequentially adding new components
		int nowComp = 2;
		double randNdx;
		boolean addSuccess;
		while (true)
		{
			if ( showDebug)
				System.out.println("adding new MAxis on, now # " +  nowComp);
			randNdx = stickMath_lib.rand01();
			if (randNdx < getPROB_addToEndorJunc())
			{
				if (getnJuncPt() == 0 || stickMath_lib.rand01() < getPROB_addToEnd_notJunc())
					addSuccess = Add_MStick(nowComp, 1);
				else
					addSuccess = Add_MStick(nowComp, 2);
			}
			else
			{
				if (stickMath_lib.rand01() < getPROB_addTiptoBranch())
					addSuccess = Add_MStick(nowComp, 3);
				else
					addSuccess = Add_MStick(nowComp, 4);
			}
			if (addSuccess == true) { // otherwise, we'll run this while loop again, and re-generate this component
				getSpecialEndComp().add(nowComp); //we add this as specialEndComp so we can create a noisemap for it.
				nowComp ++;
			}
			if (nowComp == nComp+1)
				break;
		}

		//up to here, the eligible skeleton should be ready
		// 3. Assign the radius value
		RadiusAssign(0); // no component to preserve radius
		// 4. Apply the radius value onto each component
		for (i=1; i<=getnComponent(); i++)
		{
			if( getComp()[i].RadApplied_Factory() == false) // a fail application
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
		this.centerShapeAtOrigin(getSpecialEndComp().get(0));
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

	@Override
	public void RadiusAssign(int nPreserve) {
		super.RadiusAssign(nPreserve);

		for(int i=1; i<=this.getNComponent(); i++) {
			//getComp()[i].normalizeRadInfo();
		}
	}

	/**
    Deal with the creation of first MAxisArc component
	 */
	protected void createFirstComp() // create the first component of the MStick
	{
		Point3d finalPos = new Point3d(0,0,0); //always put at origin;
		Vector3d finalTangent = new Vector3d(0,0,0);
		finalTangent = stickMath_lib.randomUnitVec();
		// System.out.println("random final tangent is : " + finalTangent);
		double devAngle = stickMath_lib.randDouble(0.0, Math.PI * 2);
		int alignedPt = 26;// make it always the center of the mAxis curve
		AllenMAxisArc nowArc = new AllenMAxisArc();
		nowArc.genArcRand();
		nowArc.transRotMAxis(alignedPt, finalPos, 1, finalTangent, devAngle);

		getComp()[1].initSet( nowArc, false, 0); // the MAxisInfo, and the branchUsed
		//update the endPt and JuncPt information
		getEndPt()[1] = new EndPt_struct(1, 1, getComp()[1].getmAxisInfo().getmPts()[1], getComp()[1].getmAxisInfo().getmTangent()[1] , 100.0);
		getEndPt()[2] = new EndPt_struct(1, 51, getComp()[1].getmAxisInfo().getmPts()[51], getComp()[1].getmAxisInfo().getmTangent()[51], 100.0);
		this.setnEndPt(2);
		this.setnJuncPt(0);

		//      System.out.println(endPt[1]);
		//      System.out.println(endPt[2]);
	}

	/**
Adding a new MAxisArc to a MatchStick
@param nowComp the index of the new added mAxis
@param type type from 1~4, indicate the type of addition, eg. E2E, E2J, E2B, B2E
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
			System.out.println("now nEndPt " + getnEndPt() + " , and nJuncPt " + getnJuncPt());
		}
		// random get a new MAxisArc
		AllenMAxisArc nowArc = new AllenMAxisArc();
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
				nowPtNdx = stickMath_lib.randInt(1, this.getnEndPt());
				if (getEndPt()[nowPtNdx].getRad() > 0.2)
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. trnasRot the nowArc to the correction configuration
			int alignedPt = 1;
			Point3d finalPos = new Point3d(getEndPt()[nowPtNdx].getPos());
			Vector3d oriTangent = new Vector3d(getEndPt()[nowPtNdx].getTangent());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( oriTangent.angle(finalTangent) > getTangentSaveZone() ) // angle btw the two tangent vector
					break;
				if ( trialCount++ == 300)
					return false;
				trialCount++;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


			// 3. update the EndPT to JuncPt
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { getEndPt()[nowPtNdx].getComp(), nowComp};
			int[] uNdxList = { getEndPt()[nowPtNdx].getuNdx(), 1};
			Vector3d[] tangentList = { oriTangent, finalTangent};
			getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, getEndPt()[nowPtNdx].getRad());
			getComp()[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

			// 2.5 call the function to check if this new arc is valid
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			// 4. generate new endPt
			getEndPt()[nowPtNdx].setValue(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);
			// 5. save this new Comp

		}
		else if (type == 2) // end to Junction connection
		{
			//1. pick a Junction Pt

			if (this.getnJuncPt() == 0)
			{
				System.out.println("ERROR, should not choose type 2 addition when nJuncPt = 0");
				return false;
			}
			int nowPtNdx = stickMath_lib.randInt(1, getnJuncPt());
			//2. transRot the newComp
			int alignedPt = 1;
			Point3d finalPos = new Point3d(getJuncPt()[nowPtNdx].getPos());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while (true)
			{

				finalTangent = stickMath_lib.randomUnitVec();
				boolean flag = true;
				for (i=1; i<= getJuncPt()[nowPtNdx].getnTangent(); i++)
				{
					if ( finalTangent.angle(getJuncPt()[nowPtNdx].getTangent()[i]) <= getTangentSaveZone()){
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
			old_JuncInfo.copyFrom(getJuncPt()[nowPtNdx]);
			getJuncPt()[nowPtNdx].addComp(nowComp, 1, nowArc.getmTangent()[1]);
			getComp()[nowComp].initSet(nowArc, false, 2);
			// 2.5 call the function to check if this new arc is valid
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[nowPtNdx].copyFrom(old_JuncInfo);
				return false;
			}
			setnEndPt(getnEndPt() + 1);
			getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);

		}
		else if (type == 3) //end-to-branch connection
		{

			// 1. select a existing comp, with free branch
			int pickedComp;
			while(true)
			{
				pickedComp = stickMath_lib.randInt(1, nowComp-1); // one of the existing component
				if ( getComp()[pickedComp].isBranchUsed() == false)
					break;
				if (showDebug)
					System.out.println("pick tube with branch unused");
			}
			// 2. transrot the newComp
			int alignedPt = 1;
			int nowUNdx = getComp()[pickedComp].getmAxisInfo().getBranchPt();
			Point3d finalPos = new Point3d( getComp()[pickedComp].getmAxisInfo().getmPts()[nowUNdx]);
			Vector3d oriTangent1 = new Vector3d( getComp()[pickedComp].getmAxisInfo().getmTangent()[nowUNdx]);
			Vector3d oriTangent2 = new Vector3d();
			Vector3d finalTangent = new Vector3d();
			oriTangent2.negate(oriTangent1);
			//System.out.println(oriTangent1);
			//System.out.println(oriTangent2);
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();
				if ( finalTangent.angle(oriTangent1) > getTangentSaveZone() &&
						finalTangent.angle(oriTangent2) > getTangentSaveZone()    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check if newComp valid
			// 3. update the JuncPt & endPt info
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { pickedComp, nowComp};
			int[] uNdxList = { nowUNdx, 1};
			Vector3d[] tangentList = { oriTangent1, oriTangent2, finalTangent};
			int[] ownerList = { pickedComp, pickedComp, nowComp};
			double rad = 100.0;
			rad = getComp()[pickedComp].getRadInfo()[1][1]; // if it is existing tube, then there will be a value
			//otherwise, it should be initial value of 100.0
			this.getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);
			//JuncPt[nJuncPt].showInfo();
			// 2.5 call the function to check if this new arc is valid
			getComp()[nowComp].initSet(nowArc, false, 3);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			setnEndPt(getnEndPt() + 1);
			this.getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);
			getComp()[pickedComp].setBranchUsed(true);


		}
		else if (type == 4) // add branch to the existing EndPt
		{
			// 1. pick an EndPt
			trialCount = 1;
			int nowPtNdx;
			trialCount = 1;
			while (true)
			{
				nowPtNdx = stickMath_lib.randInt(1, this.getnEndPt());
				if (getEndPt()[nowPtNdx].getRad() > 0.2)
					break; // we find a good endPt
				trialCount++;
				if (trialCount == 100)
					return false; // can't find an eligible endPt
			}
			// 2. transRot newComp
			int nowUNdx = nowArc.getBranchPt();
			int alignedPt = nowUNdx;
			Vector3d rev_tangent = new Vector3d();
			Point3d finalPos = new Point3d(getEndPt()[nowPtNdx].getPos());
			Vector3d oriTangent = new Vector3d(getEndPt()[nowPtNdx].getTangent());
			Vector3d finalTangent = new Vector3d();
			trialCount = 1;
			while(true)
			{
				finalTangent = stickMath_lib.randomUnitVec();

				rev_tangent.negate(finalTangent);
				if ( oriTangent.angle(finalTangent) > getTangentSaveZone() &&
						oriTangent.angle(rev_tangent) > getTangentSaveZone()    )
					break;
				if ( trialCount++ == 300)
					return false;
			}
			double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
			// 2.5 check Nearby Situtation
			// 3. update JuncPt & endPt info
			setnJuncPt(getnJuncPt() + 1);
			int[] compList = { getEndPt()[nowPtNdx].getComp(), nowComp};
			int[] uNdxList = { getEndPt()[nowPtNdx].getuNdx(), nowUNdx};
			Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
			int[] ownerList = {getEndPt()[nowPtNdx].getComp(), nowComp, nowComp};
			double rad;
			rad = getEndPt()[nowPtNdx].getRad();
			this.getJuncPt()[getnJuncPt()] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

			// 2.5 call the function to check if this new arc is valid
			getComp()[nowComp].initSet(nowArc, true, 4);
			if (this.checkSkeletonNearby(nowComp) == true)
			{
				getJuncPt()[getnJuncPt()] = null;
				setnJuncPt(getnJuncPt() - 1);
				return false;
			}
			// 4. generate 2 new endPt
			this.getEndPt()[nowPtNdx].setValue(nowComp, 1, nowArc.getmPts()[1], nowArc.getmTangent()[1], 100.0);
			setnEndPt(getnEndPt() + 1);
			this.getEndPt()[getnEndPt()] = new EndPt_struct(nowComp, 51, nowArc.getmPts()[51], nowArc.getmTangent()[51], 100.0);

		}

		if ( showDebug)
			System.out.println("end of add tube func successfully");
		return true;
		// call the check function to see if the newly added component violate the skeleton nearby safety zone.
	}



	public int chooseRandLeaf() {
		decideLeafBranch();
		List<Integer> choosableList = new LinkedList<Integer>();
		for (int i = 0; i < getnComponent(); i++) {
			if (getLeafBranch()[i] == true) {
				choosableList.add(i);
			}
		}
		Collections.shuffle(choosableList);
		return choosableList.get(0);
	}

	public boolean vetLeaf(int leafIndx) {
		try {

			AllenTubeComp toVet = this.getComp()[leafIndx];
			Vector3d tangent = toVet.getmAxisInfo().getmTangent()[toVet.getmAxisInfo().getTransRotHis_rotCenter()];
			boolean orientationCheck = vetLeafOrientation(tangent);
			return orientationCheck;

		} catch (Exception e) {
			return false;
		}
	}

	/**
	 * @param tangent
	 * @return
	 */
	private boolean vetLeafOrientation(Vector3d tangent) {
		double[] angles;
		angles = QualitativeMorph.Vector2Angles(tangent);

		boolean isLeafTooBackFacing = isLeafTooBackFacing(angles);

		return isLeafTooBackFacing;
	}

	/**
	 *
	 * @param angles: angles[0]: alpha/theta; angles[1]: beta/phi in spherical coordinates
	 * alpha/theta: angle of projection to x-y plane. Angle from x axis to y-axis
	 * beta/psi: angle between vector and z-axis.
	 * @return
	 */
	private boolean isLeafTooBackFacing(double[] angles) {
		double forbiddenAngle = 180 * Math.PI/180;
		double deviation = 45 * Math.PI/180;

		double angleToCheck = angles[1];
		while(angleToCheck < 0 * Math.PI/180) {
			angleToCheck += 360 * Math.PI/180;
		}
		while(angleToCheck > 360 * Math.PI/180) {
			angleToCheck -= 360 * Math.PI/180;
		}
		if((angleToCheck > forbiddenAngle - deviation) && (angleToCheck < forbiddenAngle + deviation)) {
			return false;
		}
		else {
			return true;
		}
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

		double maxRadius = getScaleForMAxisShape(); // degree
		double screenDist = 500;
		double minRadius = getMinScaleForMAxisShape();
		double maxBoundInMm = screenDist * Math.tan(maxRadius * Math.PI / 180 / 2);
		double minBoundInMm = screenDist * Math.tan(minRadius * Math.PI / 180 / 2);
		int i, j;

		//Point3d ori = new Point3d(0.0, 0.0, 0.0);
		//double dis;
		//double maxDis = 0;
		double maxX=0;
		double maxY=0;
		for (i = 1; i <= getnComponent(); i++) {
			for (j = 1; j <= getComp()[i].getnVect(); j++) {
				double xLocation = getScaleForMAxisShape() * getComp()[i].getVect_info()[j].x;
				double yLocation = getScaleForMAxisShape() * getComp()[i].getVect_info()[j].y;
				//				double xLocation = getComp()[i].getVect_info()[j].x;
				//				double yLocation = getComp()[i].getVect_info()[j].y;

				//dis = comp[i].vect_info[j].distance(ori);

				if(xLocation > maxBoundInMm || xLocation < -maxBoundInMm){
//					System.err.println("TOO BIG");
//					System.err.println("xLocation is: " + xLocation + ". maxBound is : " + maxBoundInMm);
					return false;
				}
				if(yLocation > maxBoundInMm || yLocation < -maxBoundInMm){
//					System.err.println("TOO BIG");
//					System.err.println("yLocation is: " + yLocation + ". maxBound is : " + maxBoundInMm);
					return false;
				}
				if(Math.abs(xLocation)>maxX)
					maxX = Math.abs(xLocation);
				if(Math.abs(xLocation)>maxY)
					maxY = Math.abs(yLocation);
			}
		}
		if (maxX < minBoundInMm && maxY < minBoundInMm) {
//			System.err.println("TOO SMALL");
//			System.out.println("AC:71923: " + maxX);
//			System.out.println("AC:71923: " + maxY);
			return false;
		}


		return true;
	}


	public void setScale(double minScale, double maxScale) {
		setMinScaleForMAxisShape(minScale);
		setScaleForMAxisShape(maxScale);
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

		setnComponent(in.getnComponent());

		//AC ADDITIONS//
		setSpecialEnd(in.getSpecialEnd());
		setSpecialEndComp(in.getSpecialEndComp());
		setBaseComp(in.getBaseComp());
		///////////////

		for (i=1; i<=getnComponent(); i++) {
			getComp()[i] = new AllenTubeComp();
			getComp()[i].copyFrom(in.getComp()[i]);
		}
		this.setnEndPt(in.getnEndPt());
		for (i=1; i<=getnEndPt(); i++) {
			getEndPt()[i] = new EndPt_struct();
			getEndPt()[i].copyFrom(in.getEndPt()[i]);
		}
		this.setnJuncPt(in.getnJuncPt());
		for (i=1; i<=getnJuncPt(); i++) {
			getJuncPt()[i] = new JuncPt_struct();
			getJuncPt()[i].copyFrom(in.getJuncPt()[i]);
		}
		this.setObj1(in.getObj1());

		for (i=1; i<=getnComponent(); i++)
			getLeafBranch()[i] = in.getLeafBranch()[i];
	}



	public void genMatchStickFromFile(String fname, double[] rotation) {
		String in_specStr;
		StringBuffer fileData = new StringBuffer(100000);
		try
		{
			BufferedReader reader = new BufferedReader(
					new FileReader(fname));
			char[] buf = new char[1024];
			int numRead=0;
			while((numRead=reader.read(buf)) != -1){
				String readData = String.valueOf(buf, 0, numRead);
				//System.out.println(readData);
				fileData.append(readData);
				buf = new char[1024];

			}
			reader.close();
		}
		catch (Exception e)
		{
			System.out.println("error in read XML spec file");
			System.out.println(e);
		}

		in_specStr = fileData.toString();

		AllenMStickSpec inSpec = new AllenMStickSpec();
		inSpec = AllenMStickSpec.fromXml(in_specStr);


		genMatchStickFromShapeSpec(inSpec, rotation);


	}

	public void genMatchStickFromFile(String fname) {
		String in_specStr;
		StringBuffer fileData = new StringBuffer(100000);
		try
		{
			BufferedReader reader = new BufferedReader(
					new FileReader(fname));
			char[] buf = new char[1024];
			int numRead=0;
			while((numRead=reader.read(buf)) != -1){
				String readData = String.valueOf(buf, 0, numRead);
				//System.out.println(readData);
				fileData.append(readData);
				buf = new char[1024];

			}
			reader.close();
		}
		catch (Exception e)
		{
			System.out.println("error in read XML spec file");
			System.out.println(e);
		}

		in_specStr = fileData.toString();

		AllenMStickSpec inSpec = new AllenMStickSpec();
		inSpec = AllenMStickSpec.fromXml(in_specStr);

		genMatchStickFromShapeSpec(inSpec, new double[] {0,0,0});
	}

	public void genAllenMatchStickFromMatchStickFile(String fname){
		String in_specStr;
		StringBuffer fileData = new StringBuffer(100000);
		try
		{
			BufferedReader reader = new BufferedReader(
					new FileReader(fname));
			char[] buf = new char[1024];
			int numRead=0;
			while((numRead=reader.read(buf)) != -1){
				String readData = String.valueOf(buf, 0, numRead);
				//System.out.println(readData);
				fileData.append(readData);
				buf = new char[1024];

			}
			reader.close();
		}
		catch (Exception e)
		{
			System.out.println("error in read XML spec file");
			System.out.println(e);
		}

		in_specStr = fileData.toString();

		MStickSpec inSpec = new MStickSpec();
		inSpec = MStickSpec.fromXml(in_specStr);

		super.genMatchStickFromShapeSpec(inSpec, new double[] {0,0,0});
	}


	/**
	 *    genMatchStickFrom spec data
	 *    Read in a spec structure, and dump those info into this MAxis structure
	 */
	public void genMatchStickFromShapeSpec( AllenMStickSpec inSpec, double[] rotation)
	{
		// i can't see how inSpec is changed by this function
		//but it seems to be the case........
		//AC: Alden, it's because you're not using deep copy of rotCenter and finalPos.
		cleanData();

		// 1. general info
		int nComp = inSpec.getmAxis().getnComponent();
		setnComponent(nComp);
		int i, j, k;

		// 1.5 AC Info
		setSpecialEnd(new LinkedList<>(inSpec.getmAxis().getSpecialEnd()));
		setSpecialEndComp(inSpec.getmAxis().getSpecialEndComp());
		setBaseComp(inSpec.getmAxis().getBaseComp());

		// 2. tube info
		for (i=1; i<=nComp; i++)
		{
			//debug
			//System.out.println("comp " + i + " : ");
			getComp()[i] = new AllenTubeComp();
			getComp()[i].setBranchUsed(inSpec.getmAxis().getTube()[i].isBranchUsed());
			getComp()[i].setConnectType(inSpec.getmAxis().getTube()[i].getConnectType());
			for (j=0; j<3; j++)
				for (k=0; k<2; k++)
				{
					getComp()[i].getRadInfo()[j][k] = inSpec.getmAxis().getTube()[i].getRadInfo()[j][k];
					// System.out.print(comp[i].radInfo[j][k] + " " );
				}
			//System.out.println(" " );

			getComp()[i].getmAxisInfo().setArcLen(inSpec.getmAxis().getTube()[i].getmAxis_arcLen());
			getComp()[i].getmAxisInfo().setRad(inSpec.getmAxis().getTube()[i].getmAxis_rad());
			getComp()[i].getmAxisInfo().setBranchPt(inSpec.getmAxis().getTube()[i].getmAxis_branchPt());
			//System.out.println("branchPt " + comp[i].mAxisInfo.branchPt);

			getComp()[i].getmAxisInfo().setTransRotHis_alignedPt(inSpec.getmAxis().getTube()[i].getTransRotHis_alignedPt());
			getComp()[i].getmAxisInfo().setTransRotHis_rotCenter(inSpec.getmAxis().getTube()[i].getTransRotHis_rotCenter());
			getComp()[i].getmAxisInfo().getTransRotHis_finalPos().set(new Point3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalPos()));
			//getComp()[i].getmAxisInfo().setTransRotHis_finalPos(new Point3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalPos()));
			getComp()[i].getmAxisInfo().getTransRotHis_finalTangent().set(new Vector3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalTangent()));
			//getComp()[i].getmAxisInfo().setTransRotHis_finalTangent(new Vector3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalTangent()));
			getComp()[i].getmAxisInfo().setTransRotHis_devAngle(inSpec.getmAxis().getTube()[i].getTransRotHis_devAngle());
		}

		// 3. endPt info
		setnEndPt(inSpec.getmAxis().getnEndPt());

		for (i=1; i<=getnEndPt(); i++)
		{
			getEndPt()[i] = new EndPt_struct();
			getEndPt()[i].setComp(inSpec.getmAxis().getEndPt()[i].getComp());
			getEndPt()[i].setuNdx(inSpec.getmAxis().getEndPt()[i].getuNdx());
			getEndPt()[i].setPos(new Point3d( inSpec.getmAxis().getEndPt()[i].getPos()));
			getEndPt()[i].setTangent(new Vector3d( inSpec.getmAxis().getEndPt()[i].getTangent()));
			getEndPt()[i].setRad(inSpec.getmAxis().getEndPt()[i].getRad());
		}

		// 4. juncPt info
		setnJuncPt(inSpec.getmAxis().getnJuncPt());
		for (i=1; i<=getnJuncPt(); i++)
		{
			getJuncPt()[i] = new JuncPt_struct();
			getJuncPt()[i].setnComp(inSpec.getmAxis().getJuncPt()[i].getnComp());
			getJuncPt()[i].setnTangent(inSpec.getmAxis().getJuncPt()[i].getnTangent());
			getJuncPt()[i].setRad(inSpec.getmAxis().getJuncPt()[i].getRad());
			getJuncPt()[i].setPos(new Point3d(inSpec.getmAxis().getJuncPt()[i].getPos()));

			for (j=1; j<= getJuncPt()[i].getnComp(); j++)
			{
				getJuncPt()[i].getComp()[j] = inSpec.getmAxis().getJuncPt()[i].getComp()[j];
				getJuncPt()[i].getuNdx()[j] = inSpec.getmAxis().getJuncPt()[i].getuNdx()[j];
			}
			for (j=1; j<= getJuncPt()[i].getnTangent(); j++)
			{
				getJuncPt()[i].getTangent()[j] = new Vector3d( inSpec.getmAxis().getJuncPt()[i].getTangent()[j]);
				getJuncPt()[i].getTangentOwner()[j] = inSpec.getmAxis().getJuncPt()[i].getTangentOwner()[j];
			}

		}

		// May 22nd, we find after GA
		// sometimes the tangent will be wrong direction
		// (while we assume the tangent in JuncPt, EndPt are correct
		// In this case we want to do the modifcation!
		// This might not be the ultimate solving way
		// but, just do it for now

		for (i=1; i<=nComp; i++) {
			getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
			getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
					getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
					getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
					getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
					getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
			getComp()[i].RadApplied_Factory(); // since we didn't save these info
		}



		// 5. final rotation info
		setFinalRotation(new double[3]);
		for (i=0; i<3; i++)
			getFinalRotation()[i] = inSpec.getmAxis().getFinalRotation()[i] + rotation[i];

		setFinalShiftinDepth(new Point3d());
		getFinalShiftinDepth().x = inSpec.getmAxis().getFinalShiftInDepth()[0];
		getFinalShiftinDepth().y = inSpec.getmAxis().getFinalShiftInDepth()[1];
		getFinalShiftinDepth().z = inSpec.getmAxis().getFinalShiftInDepth()[2];

		// 6. calculate the smooth vect and fac info

		// 2008, Nov, we should not do a rotation again here, since the original ShapeSpec info should already be rotated
		// again, or we should do it!
		//        this.finalRotateAllPoints( finalRotation[0], finalRotation[1], finalRotation[2]);

		boolean res = smoothizeMStick();
		if ( res == false) {
			System.out.println("Fail to smooth while using info from a shapeSpec");
			System.out.println("THIS SHOULD NOT HAPPEN");
			return;
		}

		// ***** IMPORTANT
		// temp, Feb 15th 2011
		// a temporary work away for the thin tube in post-hoc
		// we want to have the correct smooth of the matchStick type shape
		// in that case, we don't worry if the original mesh and now mesh is incompatible
		// So, we will jus activate the following 3 lines. which igonroe all the below codes
		//        int a = 3;
		//if (a==3)
		//  return;


		//May 22nd
		// we found in our old generating system
		// the 'finalTangent' is sometimes at 'wrong direction'
		// At here we want to check the similarity ( reproducibility)
		// of our new synthesized shape & original vertex distance
		if ( res == true)
		{
			return;
//			            if ( inSpec.getNVect() < 10) // this might happen, not sure
//			            {
//			//                System.out.println("no old smooth vertex info yet");
//			                return;
//			            }
//			            Point3d[] oriVecList = inSpec.getVectInfo();
//			            double vect_dist = 0.0;
//			            int nVect1 = this.obj1.nVect;
//			            int nVect2 = inSpec.getNVect();
//			            System.out.println("      vec # check " + nVect1 + " " + nVect2);
//			            if ( nVect1 != nVect2)
//			            {
//			                res = false;
//			                System.out.println("            vec # unmatch");
//			            }
//			            if ( res == true)
//			            {
//			                for (i= 1; i<= this.obj1.nVect; i++)
//			                {
//			                    Point3d p1 = new Point3d(obj1.vect_info[i]);
//			                    Point3d p2 = oriVecList[i];
//			                    vect_dist += p1.distance(p2);
//			                }
//			                System.out.println("            total vect dist is :" + vect_dist);
//			                if ( vect_dist > 5.0)
//			                    res = false;
//			            }
		}

		boolean tryFlip = true;
		// step1. try to flip the tangent dir of single tube
		if ( res == false)
		{

			System.out.println("we should try to switch the tangent dir");
			if ( tryFlip == false)
				return;
			// this.nComponent = -1;
			int tryComp;
			for (tryComp= 1; tryComp <=nComp; tryComp++)
			{
				//key line  ---> flip the tangent dir
				System.out.println("try to flip comp " + tryComp);
				getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().negate();

				for (i=1; i<=nComp; i++)
				{
					getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
					getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
							getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
							getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
							getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
							getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
					getComp()[i].RadApplied_Factory(); // since we didn't save these info
				}

				res = smoothizeMStick();
				if ( res == false) // success to smooth
				{
					System.out.println("Fail to smooth while using info from a shapeSpec");
					System.out.println("THIS SHOULD NOT HAPPEN");
				}


				if ( res == true)
				{
					Point3d[] oriVecList = inSpec.getVectInfo();
					double vect_dist = 0.0;
					int nVect1 = getObj1().getnVect();
					int nVect2 = inSpec.getNVect();
					System.out.println("vec # check " + nVect1 + " " + nVect2);
					if ( nVect1 != nVect2)
					{
						res = false;
						System.out.println("vec # unmatch");
					}
					if ( res == true)
					{
						for (i= 1; i<= getObj1().getnVect(); i++)
						{
							Point3d p1 = new Point3d(getObj1().vect_info[i]);
							Point3d p2 = oriVecList[i];
							vect_dist += p1.distance(p2);
						}
						System.out.println("total vect dist is :" + vect_dist);
						if ( vect_dist > 5.0)
							res = false;
					}
				}

				//debug, remember to remove it //feb 15 2011

				if ( res == true) // great this flip work
				{
					System.out.println("flip " + tryComp + " work");
					break;
				}
				else                //flip back
					getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().negate();

			} // for loop
		}

		if ( res == false)
		{
			System.out.println("try flip all final tangent one-by-one, no work!");
			System.out.println("check this shape out!!!");
			// July 23rd 2009
			//debug, may need to remove later
			//  this.nComponent = -1;

		}
		// step2. try to change the finalTangent dir to what we have in JuncPt/EndPt
		boolean JuncAssignWork = false;
		if ( res == false)
		{

			System.out.println("try to use tangent Info in Junc/End Pt");

			int tryComp;
			for (tryComp= 1; tryComp <=nComp; tryComp++)
			{
				// collect all the possible tangent into an array
				Vector3d[] candidate = new Vector3d[20];
				for (i=0; i<20; i++) candidate[i] = new Vector3d();
				int nCandidate = 0;
				for (i=1; i<= getnEndPt(); i++)
				{
					if (getEndPt()[i].getComp() == tryComp)
					{
						candidate[nCandidate].set( getEndPt()[i].getTangent());
						candidate[nCandidate+1].set( getEndPt()[i].getTangent());
						candidate[nCandidate+1].negate();
						nCandidate +=2;
					}
				}

				for (i=1; i<= getnJuncPt(); i++)
				{
					for (j=1; j<= getJuncPt()[i].getnTangent(); j++)
						if  (getJuncPt()[i].getTangentOwner()[j] == tryComp)
						{
							candidate[nCandidate].set( getJuncPt()[i].getTangent()[j]);
							candidate[nCandidate+1].set( getJuncPt()[i].getTangent()[j]);
							candidate[nCandidate+1].negate();
							nCandidate +=2;

						}
				}

				for (k=0; k< nCandidate; k++)
				{
					//key line  ---> flip the tangent dir
					System.out.println("try to assign comp " + tryComp + " with " + k + " candidate");
					Vector3d oriVec = new Vector3d(getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent());
					getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().set(candidate[k]);
					//comp[tryComp].mAxisInfo.transRotHis_finalTangent.negate();
					//if (tryComp > 1) //flip back last one
					//comp[tryComp-1].mAxisInfo.transRotHis_finalTangent.negate();

					for (i=1; i<=nComp; i++)
					{
						getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
						getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
								getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
								getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
								getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
								getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
						getComp()[i].RadApplied_Factory(); // since we didn't save these info
					}

					res = this.smoothizeMStick();
					if ( res == false) // success to smooth
					{
						System.out.println("Fail to smooth while using info from a shapeSpec");
						System.out.println("THIS SHOULD NOT HAPPEN");
					}

					if ( res == true)
					{
						Point3d[] oriVecList = inSpec.getVectInfo();
						double vect_dist = 0.0;
						int nVect1 = getObj1().getnVect();
						int nVect2 = inSpec.getNVect();
						System.out.println("vec # check " + nVect1 + " " + nVect2);
						if ( nVect1 != nVect2)
						{
							res = false;
							System.out.println("vec # unmatch");
						}
						if ( res == true)
						{
							for (i= 1; i<= getObj1().getnVect(); i++)
							{
								Point3d p1 = new Point3d(getObj1().vect_info[i]);
								Point3d p2 = oriVecList[i];
								vect_dist += p1.distance(p2);
							}
							System.out.println("total vect dist is :" + vect_dist);
							if ( vect_dist > 5.0)
								res = false;
						}
					}

					if ( res == true) // great this flip work
					{
						System.out.println("flip " + tryComp + " work");
						JuncAssignWork = true;
						break;
					}
					else //set back
						getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().set(oriVec);
				} //for loop of k
				if (JuncAssignWork == true)
					break;
			} // for loop
		}

		if ( res == false)
		{
			System.out.println("try flip all final tangent one-by-one, no work!");
			System.out.println("check this shape out!!!");
			// July 23rd 2009
			//debug, may need to remove later
			//  this.nComponent = -1;

		}
		// step3. try a intensive all possible flip
		if ( res == false)
		{
			System.out.println("Intensive flip trial...");
			if ( tryFlip == false)
				return;
			// this.nComponent = -1;
			int tryTimes= 1;

			for (tryTimes = 1; tryTimes <= Math.pow(2, getnComponent()) -1; tryTimes++)
			{
				//key line  ---> flip the tangent dir
				System.out.println("try to flip times " + tryTimes);
				int[] flipState = new int[getnComponent()];
				int divider = (int) Math.pow(2, getnComponent()-1);
				int nowV = tryTimes;
				for (j=0; j <getnComponent(); j++)
				{
					//System.out.println( j + " " + nowV + " " + divider);
					flipState[j] = nowV / divider;
					nowV = nowV % divider;
					divider = divider /2;
				}

				//debug
				for (j=0; j<getnComponent(); j++)
					System.out.print( flipState[j] + " " );
				System.out.println(" ");
				System.out.println("nComp " + nComp);
				System.out.println("nComponent " + getnComponent());
				for (j=1; j<=nComp; j++)
					if (flipState[j-1] == 1)
						getComp()[j].getmAxisInfo().getTransRotHis_finalTangent().negate();

				for (i=1; i<=nComp; i++)
				{
					getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
					getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
							getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
							getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
							getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
							getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
					getComp()[i].RadApplied_Factory(); // since we didn't save these info
				}

				res = this.smoothizeMStick();
				if ( res == false) // success to smooth
				{
					System.out.println("Fail to smooth while using info from a shapeSpec");
					System.out.println("THIS SHOULD NOT HAPPEN");
				}

				if ( res == true)
				{
					Point3d[] oriVecList = inSpec.getVectInfo();
					double vect_dist = 0.0;
					int nVect1 = this.getObj1().getnVect();
					int nVect2 = inSpec.getNVect();
					System.out.println("vec # check " + nVect1 + " " + nVect2);
					if ( nVect1 != nVect2)
					{
						res = false;
						System.out.println("vec # unmatch");
					}
					if ( res == true)
					{
						for (i= 1; i<= getObj1().getnVect(); i++)
						{
							Point3d p1 = new Point3d(getObj1().vect_info[i]);
							Point3d p2 = oriVecList[i];
							vect_dist += p1.distance(p2);
						}
						System.out.println("total vect dist is :" + vect_dist);
						if ( vect_dist > 5.0)
							res = false;
					}
				}

				if ( res == true) // great this flip work
				{
					System.out.println("flip " + tryTimes+ " work");
					break;
				}
				//flip back
				for (j=1; j<=nComp; j++)
					if (flipState[j-1] == 1)
						getComp()[j].getmAxisInfo().getTransRotHis_finalTangent().negate();

			} // for loop
		}

		// not implement yet
		//step4. change multiple tangent to the Junc/End Pt info
		if ( res == false)
		{
			System.out.println("try flip all intensive flip, still no work!");
			System.out.println("check this shape out!!!");
			System.out.println("check this shape out!!!");

			//this.nComponent = -1;
		}

	}

	public AllenTubeComp[] getComp() {
		return comp;
	}

	public EndPt_struct[] getEndPt() {
		return endPt;
	}

	public void setEndPt(EndPt_struct[] endPt) {
		this.endPt = endPt;
	}

	public int getnEndPt() {
		return nEndPt;
	}

	public void setnEndPt(int nEndPt) {
		this.nEndPt = nEndPt;
	}

	public int getnJuncPt() {
		return nJuncPt;
	}

	public void setnJuncPt(int nJuncPt) {
		this.nJuncPt = nJuncPt;
	}

	public JuncPt_struct[] getJuncPt() {
		return JuncPt;
	}

	public void setJuncPt(JuncPt_struct[] juncPt) {
		JuncPt = juncPt;
	}

	public MStickObj4Smooth getObj1() {
		return obj1;
	}

	public void setObj1(MStickObj4Smooth obj1) {
		this.obj1 = obj1;
	}

	public boolean[] getLeafBranch() {
		return LeafBranch;
	}

	public void setLeafBranch(boolean[] leafBranch) {
		LeafBranch = leafBranch;
	}

	public double getMinScaleForMAxisShape() {
		return minScaleForMAxisShape;
	}

	public void setMinScaleForMAxisShape(double minScaleForMAxisShape) {
		this.minScaleForMAxisShape = minScaleForMAxisShape;
	}



	public int getBaseComp() {
		return baseComp;
	}

	public void setBaseComp(int baseComp) {
		this.baseComp = baseComp;
	}

	public double getPROB_addToEndorJunc() {
		return PROB_addToEndorJunc;
	}

	public double getPROB_addToEnd_notJunc() {
		return PROB_addToEnd_notJunc;
	}

	public double getPROB_addTiptoBranch() {
		return PROB_addTiptoBranch;
	}

	public double[] getFinalRotation() {
		return finalRotation;
	}

	public double[] getPARAM_nCompDist() {
		return PARAM_nCompDist;
	}

	public double getTangentSaveZone() {
		return TangentSaveZone;
	}

	public void setComp(AllenTubeComp[] comp) {
		this.comp = comp;
	}

	public AllenTubeComp getTubeComp(int i) {
		return getComp()[i];
	}

	public List<Integer> getSpecialEnd() {
		return specialEnd;
	}

	public void setSpecialEnd(List<Integer> specialEnd) {
		this.specialEnd = specialEnd;
	}

	public List<Integer> getSpecialEndComp() {
		return specialEndComp;
	}

	public void setSpecialEndComp(List<Integer> specialEndComp) {
		this.specialEndComp = specialEndComp;
	}

    /**
     * It is imperative that these properties are set before the object is generated/is smoothized.
     *
	 * @param maxImageDimensionDegrees
	 */
    public void setProperties(double maxImageDimensionDegrees) {
        //OBJECT PROPERTIES
        //SETTING SIZES
        /**
         * With this strategy of scale setting, we set our maxImageDimensionDegrees to
         * twice about what we want the actual size of our stimuli to be. Then we try to draw the stimuli
         * to be approx half the size.
         */
//        double scale = maxImageDimensionDegrees /1.5;
		double scale = maxImageDimensionDegrees;
        double minScale = scale/2;
        setScale(minScale, scale);

        //CONTRAST
        double contrast = 0.5;
        setContrast(contrast);

        //COLOR
        RGBColor white = new RGBColor(1,1,1);
        setStimColor(white);

        //TEXTURE
        setTextureType("SHADE");

    }

	/**
	 A public function that will start generating an offspring of this existing shape
	 The parent is the current shape.
	 The result will be stored in this object

	  While we've not reached a legal specified mutation
	  	1. Decide if we're going to add or remove limbs

	  	2. Determines which limbs are leafs and which are not

	  	3. Decides for each limb, whether to do nothing, replace whole, do a fine change, or remove it
	  	Probability depends on whether the limb is a leaf or not (we shouldn't remove a center limb or completely replace it)

	  	4. Checks if the number of changes that are occuring is not too big or small
	  	IF everything is fine, we break out of the loop


	  Mutation Process Loop (If at any point, a mutation fails, we retry)
	  	1. Make a backup of the specified changes

	  	2. Removal mutations

	  	3. Whole change mutations
	  	4. Fine change mutations

	  	5. Add mutations - local loop to try multiple times

	  	6. Mutate junction radii

	  Post - Process

	  	1. Check size of mstick

	  	2. Change final rotation

	  	3. Smoothize

	 */
	public boolean mutate(int debugParam) {
		final int MaxMutateTryTimes = 10;
		final int MaxAddTubeTryTimes = 15;
		final int MaxCompNum = 4;
		final int MinCompNum = 2;
		final int MaxDeletionNum = 1;

		// 4 possible task for each tube
		// [ 1.nothing 2.replace whole 3. fine chg 4. Remove it]
		// The distribution will be different for center & leaf stick
		double[] prob_leaf = {0.4, 0.6, 0.8, 1.0};
		//double[] prob_center = {0.6, 0.8, 1.0, 1.0};
		double[] prob_center = {0.6, 0.6, 1.0, 1.0};
		double[] prob_addNewTube = { 0.3333, 0.6666, 1.0}; // 1/3 no add , 1/3 add 1, 1/3 add 2 tubes

		if ( this.getnComponent() <=3) {
			prob_addNewTube[0] = 0.3;
			prob_addNewTube[1] = 1.0;
		} else if ( this.getnComponent() >=4 && this.getnComponent() <=5) {
			prob_addNewTube[0] = 0.5;
			prob_addNewTube[1] = 1.0;
		} else if ( this.getnComponent() >=6) {
			prob_addNewTube[0] = 0.7;
			prob_addNewTube[1] = 1.0;
		}

		this.decideLeafBranch();

		int i;
		int old_nComp;
		int[] task4Tube = new int[getnComponent()+1];
		int[] task4Tube_backup = new int[getnComponent()+1];
		int nAddTube, nRemoveTube, nResultTube;
		// 1. decide what kind of modification should go on
		int nChgTotal;
		int minChgTotal = 2;
		int maxChgTotal = 3;
		while (true) {
			boolean noChgFlg = true;
			for (i=1; i<=getnComponent(); i++) {
				if (getLeafBranch()[i] == true)
					task4Tube[i] = stickMath_lib.pickFromProbDist(prob_leaf);
				else
					task4Tube[i] = stickMath_lib.pickFromProbDist(prob_center);

				if (task4Tube[i] != 1)
					noChgFlg = false; // at least one chg will occur
			}
			nAddTube = stickMath_lib.pickFromProbDist(prob_addNewTube) - 1;
			nRemoveTube =0;
			for (i=1; i<=getnComponent(); i++)
				if (task4Tube[i] == 4)
					nRemoveTube++;
			nResultTube = getnComponent() + nAddTube - nRemoveTube;

			// calculate nChgTotal
			nChgTotal = 0;
			for (i=1; i<=getnComponent(); i++)
				if (task4Tube[i] != 1)
					nChgTotal++;
			nChgTotal += nAddTube;
			// so the # of nChgTotal means the # of tubes been ( modified or removed) + # of tube added
			if ( nChgTotal > maxChgTotal || nChgTotal < minChgTotal)
			{
				//if ( showDebug)
				//  System.out.println("nChgtotal is now " + nChgTotal);
				continue; // we don't want to small or too big change
			}
			if ( noChgFlg == false && nResultTube <= MaxCompNum  && nResultTube >= MinCompNum
					&& nRemoveTube <= MaxDeletionNum ) // a legal condition
				break;
		}

		//debug
		if (debugParam == 1) {
			//only remove 1 component each time
			for (i=1; i<=getnComponent(); i++)
				task4Tube[i] = 1;
			while (true) {
				i =stickMath_lib.randInt(1, getnComponent());
				if (getLeafBranch()[i] == true) {
					task4Tube[i] = 4;
					break;
				}
			}
			nRemoveTube = 1;
			nAddTube = 0;
		} else if ( debugParam == 2) {
			nRemoveTube = 0;
			for (i=1; i<=getnComponent(); i++)
				task4Tube[i] = 1;
			nAddTube = 1;
		} else if ( debugParam == 3) {
			nRemoveTube = 0;
			nAddTube = 0;
			for (i=1; i<=getnComponent(); i++)
				task4Tube[i] = 1;
			int randComp  = stickMath_lib.randInt(1, getnComponent());
			task4Tube[randComp] = 2;
		} else if ( debugParam == 4) {
			nRemoveTube = 0;
			nAddTube = 0;
			for (i=1; i<=getnComponent(); i++)
				task4Tube[i] = 1;
			int randComp  =stickMath_lib.randInt(1, getnComponent());
			task4Tube[randComp] = 3;
		}

		// Now start the part of really doing the morphing

		// Dec 24th 2008.
		// At this point, we decide what kind of morphing to do
		// but, sometimes, some details will fail.
		// what I would like to do is try the morph several times before give up

		// March 10th 2009.
		// This is a bug I found after recording for a while
		// everytime we should load the task4Tube from the back
		// since if we re-do the mutate, the task4Tube might already
		// change during the previous manipulation.

		for (i=1; i<=getnComponent(); i++)
			task4Tube_backup[i] = task4Tube[i];

		int mutateTryTimes = 1;
		boolean successMutateTillNow;
		for (mutateTryTimes = 1; mutateTryTimes <= MaxMutateTryTimes; mutateTryTimes++) {
			//load the backup of task4Tube
			for (i=1; i<=getnComponent(); i++)
				task4Tube[i] = task4Tube_backup[i];

			successMutateTillNow = true;
			//1. remove the stick
			boolean[] removeFlg = new boolean[getnComponent()+1];
			for (i=1; i<=getnComponent(); i++)
				if (task4Tube[i] == 4)
					removeFlg[i] = true;
			old_nComp = getnComponent(); // since this number will chg later in removeComponent
			// 2. fine tune and replacement
			// 2.1 remap the task4Tube
			if (nRemoveTube > 0) // else , we can skip this procedure
				this.removeComponent(removeFlg);

			int counter = 1;
			for (i=1; i<= old_nComp; i++)
				if ( task4Tube[i] != 4)
					task4Tube[counter++] = task4Tube[i];

			// 2.2 really doing the fine tune & replace
			for (i=1; i<= getnComponent(); i++) {
				boolean res = true;
				if (task4Tube[i] == 2) // replace
					res = this.replaceComponent(i);
				if (task4Tube[i] == 3) // fine tune
					res = this.fineTuneComponent(i);

				// if res == false, we want to go out to big Trial loop & try again
				if (!res) {
					successMutateTillNow = false;
				}
			}
			if ( successMutateTillNow == false) continue;

			// 3. Add new tube on the shape
			// we will try to add several times locally
			if (nAddTube > 0) {
				AllenMatchStick tempStoreStick = new AllenMatchStick();
				tempStoreStick.copyFrom(this);
				int addtube_trytime = 0;
				while (true) {
					boolean res = this.addTubeMutation(nAddTube);
					if (res)
						break;
					else {
						addtube_trytime++;
						if ( addtube_trytime > MaxAddTubeTryTimes) {
							successMutateTillNow = false;
							break;
						}
					}
					this.copyFrom(tempStoreStick);
				}
			}
			if (!successMutateTillNow)
				continue;

			// 5. reassign the radius value at junction point
			this.MutateSUB_reAssignJunctionRadius();

			// 6. translate the shape, so that the first component is centered at origin.
			//            this.centerShapeAtOrigin(-1);

			if (!this.validMStickSize())
				successMutateTillNow = false;

			if (!successMutateTillNow)
				continue;

			this.changeFinalRotation();

			return this.smoothizeMStick();
		}

		return false;
	}

	@Override
	protected void addTube(int i){
		getComp()[i] = new AllenTubeComp();
	}

	public AllenMStickData getMStickData(){
		AllenMStickData data = new AllenMStickData();

		//TODO: WE HAVE TO BECAREFUL OF SIDE EFFECTS OF THIS METHOD. Must be the last thing.
		modifyMStickFinalInfoForAnalysis();

		AllenMStickSpec analysisMStickSpec = new AllenMStickSpec();
		analysisMStickSpec.setMStickInfo(this);

		data.setAnalysisMStickSpec(analysisMStickSpec);
		data.setShaftData(getShaftData());
		data.setTerminationData(getTerminationData());
		data.setJunctionData(getJunctionData());

		return data;
	}

	private List<JunctionData> getJunctionData() {
		List<JunctionData> junctionDatas = new LinkedList<>();
		for (int i=1; i<=getNJuncPt(); i++){
			JunctionData junctionData = new JunctionData();

			//Position - Spherical Coordinates
			JuncPt_struct juncPt = getJuncPt()[i];
			Point3d junctionCenterCartesian = juncPt.getPos();
			SphericalCoordinates junctionPositionSpherical = CoordinateConverter.cartesianToSpherical(junctionCenterCartesian);
			junctionData.angularPosition = junctionPositionSpherical.getAngularCoordinates();
			junctionData.radialPosition = junctionPositionSpherical.r;

			//Angle Bisector Direction
			junctionData.angleBisectorDirection = new LinkedList<AngularCoordinates>();
			//for every pair
			for(int j=1; j<=juncPt.getnComp(); j++){
				for(int k=j+1; k<=juncPt.getnComp(); k++){
					Vector3d[] junctionTangents = new Vector3d[]{juncPt.getTangent()[j], juncPt.getTangent()[k]};
					Vector3d bisectorTangent = calculateBisectorVector(junctionTangents);
					SphericalCoordinates bisectorTangentSpherical = CoordinateConverter.cartesianToSpherical(bisectorTangent);
					junctionData.angleBisectorDirection.add(bisectorTangentSpherical.getAngularCoordinates());
				}
			}

			//Radius
			junctionData.radius = juncPt.getRad();

			//Junction Subtense
			junctionData.angularSubtense = new LinkedList<AngularCoordinates>();
			//for every pair
			for(int j=1; j<=juncPt.getnComp(); j++){
				for(int k=j+1; k<=juncPt.getnComp(); k++){
					SphericalCoordinates angle1 = CoordinateConverter.cartesianToSpherical(juncPt.getTangent()[j]);
					SphericalCoordinates angle2 = CoordinateConverter.cartesianToSpherical(juncPt.getTangent()[k]);
					double theta = angleDiff(angle1.theta, angle2.theta);
					double phi = angleDiff(angle1.phi, angle2.phi);
					AngularCoordinates subtense = new AngularCoordinates(theta, phi);
					junctionData.angularSubtense.add(subtense);
				}
			}

			//TODO: Planar Rotation

			//
			junctionDatas.add(junctionData);
		}
		return junctionDatas;
	}

	private List<TerminationData> getTerminationData() {
		List<TerminationData> terminationDatas = new LinkedList<>();
		for (int i=1; i<= getNEndPt(); i++){
			TerminationData terminationData = new TerminationData();
			EndPt_struct endPt = getEndPt()[i];

			//Position - Spherical Coordinates
			Point3d terminationPositionCartesian = endPt.getPos();
			SphericalCoordinates terminationSphericalCoordinates = CoordinateConverter.cartesianToSpherical(terminationPositionCartesian);
			terminationData.angularPosition = terminationSphericalCoordinates.getAngularCoordinates();
			terminationData.radialPosition = terminationSphericalCoordinates.r;

			//Direction
			Vector3d directionCartesian = endPt.getTangent();
			terminationData.direction = CoordinateConverter.cartesianToSpherical(directionCartesian).getAngularCoordinates();

			//Radius
			terminationData.radius = endPt.getRad();

			//
			terminationDatas.add(terminationData);
		}
		return terminationDatas;
	}

	private List<ShaftData> getShaftData() {
		List<ShaftData> shaftDatas = new LinkedList<>();
		for (int i=1; i<=getNComponent(); i++){
			ShaftData shaftData = new ShaftData();
			AllenTubeComp tube = getComp()[i];
			AllenMAxisArc mAxis = tube.getmAxisInfo();

			//Position - Spherical Coordinates
			Point3d shaftCenterCartesian = mAxis.getmPts()[26];
			SphericalCoordinates shaftCenterSpherical = CoordinateConverter.cartesianToSpherical(shaftCenterCartesian);
			shaftData.angularPosition = shaftCenterSpherical.getAngularCoordinates();
			shaftData.radialPosition = shaftCenterSpherical.r;

			//Orientation
			Vector3d orientationCartesian = mAxis.getmTangent()[26];
			SphericalCoordinates orientationSpherical = CoordinateConverter.cartesianToSpherical(orientationCartesian);
			shaftData.orientation = orientationSpherical.getAngularCoordinates();

			//Radius
			shaftData.radius = tube.getRadInfo()[1][1];

			//Length
			shaftData.length = mAxis.getArcLen();

			//Curvature
			shaftData.curvature = mAxis.getCurvature();

			//
			shaftDatas.add(shaftData);
		}
		return shaftDatas;
	}

	private double angleDiff(double angle1, double angle2) {
		double diff = angle1 - angle2;
		while(diff < 0){
			diff+=2*Math.PI;
		}
		while(diff>2*Math.PI){
			diff-=2*Math.PI;
		}
		return diff;
	}

	private Vector3d calculateBisectorVector(Vector3d[] bisectedVectors) {
		Vector3d bisectorTangent = new Vector3d(0,0,0);
		for(Vector3d tangent: bisectedVectors){
			tangent.normalize();
			bisectorTangent.add(tangent);
		}
		if(!bisectorTangent.equals(new Vector3d(0,0,0)))
			bisectorTangent.normalize();
		else{
			//If the vector completely cancel each other out, we will get a divide by
			//zero error. In this case, add a small pertubation to avoid a crash.
			bisectorTangent.add(new Vector3d(0.000001, 0.000001, 0.000001));
			bisectorTangent.normalize();
		}
		return bisectorTangent;
	}
}