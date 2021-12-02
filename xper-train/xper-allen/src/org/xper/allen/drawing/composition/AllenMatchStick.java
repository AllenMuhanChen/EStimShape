package org.xper.allen.drawing.composition;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import javax.vecmath.Point3d;

import org.xper.drawing.stick.EndPt_struct;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.MStickObj4Smooth;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.stick.TubeComp;
import org.xper.drawing.stick.stickMath_lib;
import org.xper.utils.RGBColor;

import com.thoughtworks.xstream.XStream;

/**
 * MatchStick class with ability to make deep clones and manipulations of shapes
 * @author r2_allen
 *
 */
public class AllenMatchStick extends MatchStick implements Serializable {
   
	protected final double PROB_addToEndorJunc = 0; 	// 60% add to end or junction pt, 40% to the branch
    protected final double PROB_addToEnd_notJunc = 0.3; // when "addtoEndorJunc", 50% add to end, 50% add to junc
       

	protected final double[] PARAM_nCompDist = {0.0,0, 0, 0, 1, 0.0, 0, 0};

	public AllenMatchStick(){}

	/* FAILED DEEP COPY ATTEMPT
    public Object clone() throws CloneNotSupportedException
    {
    	AllenMatchStick ams = (AllenMatchStick)super.clone();

    	ams.finalShiftinDepth = new Point3d(super.finalShiftinDepth.getX(),super.finalShiftinDepth.getY(),super.finalShiftinDepth.getZ());
    	ams.comp = new TubeComp[9];
    	ams.endPt = new EndPt_struct[50];
        ams.JuncPt = new JuncPt_struct[50];
        ams.obj1 = new MStickObj4Smooth();
        ams.stimColor = new RGBColor(1,1,1);
        return ams;

    }
	 */

	public void genMatchStickFromLeaf(TubeComp leaf)
	{
		//int nComp;
		//double nCompDist = { 0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		//double[] nCompDist = { 0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.00};
		//double[] nCompDist = {0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		//double[] nCompDist = this.PARAM_nCompDist;
		//nComp = stickMath_lib.pickFromProbDist(nCompDist);
		int nComp = 2; //TODO Specify nComp; 
		this.cleanData();
		//  debug
		//  nComp = 4;

		//The way we write like this can guarantee that we try to
		// generate a shape with "specific" # of components

		while (true)
		{
			while (true)
			{
				if (genMatchStick_from_leaf(leaf, nComp) == true)
					break;
				//            else
				//                System.out.println("        Attempt to gen shape fail. try again");
			}

			this.finalRotation = new double[3];
			//          for (int i=0; i<3; i++)
			//              finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			//debug

			//finalRotation[0] = 90.0;
			//finalRotation[1] = 0.0;
			//finalRotation[2] = 0;

			//this.finalRotateAllPoints(finalRotation[0], finalRotation[1], finalRotation[2]);

			// this.centerShapeAtOrigin(-1);

			boolean res = this.smoothizeMStick();
			if ( res == true) // success to smooth
				break; //else we need to gen another shape
			//          else
			//              System.out.println("      Fail to smooth combine the shape. try again.");




		}

	}
	
	public boolean genMatchStick_from_leaf(TubeComp leaf, int nComp){
		this.nComponent = nComp;
		int i;
		for (i=1; i<=nComponent; i++){
			comp[i] = new TubeComp();
		}
		
		//STARTING LEAF
		comp[1].copyFrom(leaf);
        this.endPt[1] = new EndPt_struct(1, 1, comp[1].mAxisInfo.mPts[1], comp[1].mAxisInfo.mTangent[1] , 100.0);
        this.endPt[2] = new EndPt_struct(1, 51, comp[1].mAxisInfo.mPts[51], comp[1].mAxisInfo.mTangent[51], 100.0);
        this.nEndPt = 2;
        this.nJuncPt = 0;
		/////////////////////////////
        
		int nowComp = 2;
		boolean showDebug = true;
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
					addSuccess = this.Add_MStick(nowComp, 1);
				else
					addSuccess = this.Add_MStick(nowComp, 2);
			}
			else
			{
				if (stickMath_lib.rand01() < PROB_addTiptoBranch)
					addSuccess = this.Add_MStick(nowComp, 3);
				else
					addSuccess = this.Add_MStick(nowComp, 4);
			}
			if (addSuccess == true) // otherwise, we'll run this while loop again, and re-generate this component
				nowComp ++;
			if (nowComp == nComp+1)
				break;
		}

		//up to here, the eligible skeleton should be ready
		// 3. Assign the radius value
		this.RadiusAssign(1); // KEEP FIRST ELEMENT SAME RADIUS
		// 4. Apply the radius value onto each component
		for (i=1; i<=nComponent; i++)
		{
			if( this.comp[i].RadApplied_Factory() == false) // a fail application
			{
				return false;
			}
		}


		// 5. check if the final shape is not working ( collide after skin application)


		if ( this.finalTubeCollisionCheck() == true)
		{
			if ( showDebug)
				System.out.println("\n FAIL the final Tube collsion Check ....\n");
			return false;
		}


		// Dec 24th 2008
		// re-center the shape before do the validMStickSize check!
		//this.centerShapeAtOrigin(-1);
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
	
	
	//TODO: Convert this into a method that takes an arguement one limb/tube and one body, removes from that body but ignores the given limb. 
	public void genRemovedLeafMatchStick(){

		while (true)
		{
			//1. PICK OUT A LEAF TO DELETE
			boolean[] removeList = new boolean[comp.length];
			removeList[chooseRandLeaf()] = true;


			//2. DO THE REMOVING
			removeComponent(removeList);

			//3. 
			finalRotation = new double[3];
			//           for (int i=0; i<3; i++)
			//               finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			//debug

			//finalRotation[0] = 90.0;
			//finalRotation[1] = 0.0;
			//finalRotation[2] = 0;

			//this.finalRotateAllPoints(finalRotation[0], finalRotation[1], finalRotation[2]);

			//this.centerShapeAtOrigin(-1);


			//TODO: Sometimes after removing the limb the resulting print is all black. NEed to figure out what's wrong. 
			boolean res = smoothizeMStick();
			if ( res == true) // success to smooth
				break; //else we need to gen another shape
			//           else
			System.out.println("      Fail to smooth combine the shape. try again.");

		}

	}

	
	


	public void genMatchStickRand()
	{
		int nComp;
		//double nCompDist = { 0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		//double[] nCompDist = { 0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.00};
		//double[] nCompDist = {0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
		double[] nCompDist = this.PARAM_nCompDist;
		//nComp = stickMath_lib.pickFromProbDist(nCompDist);
		nComp = 2;
		
		this.cleanData();
		//  debug
		//  nComp = 4;

		//The way we write like this can guarantee that we try to
		// generate a shape with "specific" # of components

		while (true)
		{
			while (true)
			{
				if (genMatchStick_comp(nComp) == true)
					break;
				//            else
				//                System.out.println("        Attempt to gen shape fail. try again");
			}

			this.finalRotation = new double[3];
			//          for (int i=0; i<3; i++)
			//              finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

			//debug

			//finalRotation[0] = 90.0;
			//finalRotation[1] = 0.0;
			//finalRotation[2] = 0;

			//this.finalRotateAllPoints(finalRotation[0], finalRotation[1], finalRotation[2]);

			// this.centerShapeAtOrigin(-1);

			boolean res = this.smoothizeMStick();
			if ( res == true) // success to smooth
				break; //else we need to gen another shape
			//          else
			//              System.out.println("      Fail to smooth combine the shape. try again.");




		}

	}


	public int chooseRandLeaf(){
		this.decideLeafBranch();
		List<Integer> choosableList = new LinkedList<Integer>();
		for (int i=0; i<nComponent; i++){
			if(LeafBranch[i]==true){
				choosableList.add(i);
			}
		}
		Collections.shuffle(choosableList);
		return choosableList.get(0);
	}

	
	
	/**
	 * Creates a deep copy via serializing to xml and converting back. 
	 * @return
	 */
	public AllenMatchStick deepCopy(){
		final XStream XSTREAM = new XStream();
		return (AllenMatchStick) XSTREAM.fromXML(XSTREAM.toXML(this));
	}


}

