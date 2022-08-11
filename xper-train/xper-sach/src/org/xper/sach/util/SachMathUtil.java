package org.xper.sach.util;


import java.util.ArrayList;
import java.util.Arrays;
import java.util.Random;
import java.util.List;

import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
//import org.apache.commons.math.special.*;
import org.xper.drawing.Coordinates2D;

public class SachMathUtil {
	
	public static double epsilon = 0.000001;	
	public static Random rand = new Random();


	public static double sind(double deg) {
		// sine using degrees
		return Math.sin(deg*Math.PI/180);
	}
	
	public static double cosd(double deg) {
		// cosine using degrees
		return Math.cos(deg*Math.PI/180);
	}
	
	public static double tand(double deg) {
		// tangent using degrees
		return Math.tan(deg*Math.PI/180);
	}
	
	public static Coordinates2D cart2pol(double x, double y) {
		double theta = Math.atan2(y,x)*180/Math.PI;		// convert to degrees
		double rho   = Math.hypot(x,y);
				
		Coordinates2D theta_rho = new Coordinates2D(theta,rho);
		return theta_rho; 
	}
	
	public static Coordinates2D cart2pol(double[] cart) {
		double theta = Math.atan2(cart[1],cart[0])*180/Math.PI;		// convert to degrees
		double rho   = Math.hypot(cart[0],cart[1]);
				
		Coordinates2D theta_rho = new Coordinates2D(theta,rho);
		return theta_rho; 
	}
	
	public static Coordinates2D pol2cart(double theta, double rho) {
		double x = rho * Math.sin(theta*Math.PI/180);		// +y = 0deg, +x = 90deg
		double y = rho * Math.cos(theta*Math.PI/180);
				
		Coordinates2D x_y = new Coordinates2D(x,y);
		return x_y; 
	}
	
	public static Coordinates2D pol2cart(double[] pol) {
		double x = pol[1] * Math.sin(pol[0]*Math.PI/180);		// +y = 0deg, +x = 90deg
		double y = pol[1] * Math.cos(pol[0]*Math.PI/180);
				
		Coordinates2D x_y = new Coordinates2D(x,y);
		return x_y; 
	}
	
	public static double pol2cart_x(double theta, double rho) {
		double x = rho * Math.sin(theta*Math.PI/180);
		return x; 
	}
	
	public static double pol2cart_y(double theta, double rho) {
		double y = rho * Math.cos(theta*Math.PI/180);
		return y; 
	}
	
	public static double normAngle(double angle) {
		// this takes an angle in degrees and normalizes it to between 0 and 360
		return ((angle % 360) + 360) % 360;
	}
	
	// convert mm to deg and back (need a distance of eyes from screen measure in mm):
	
	public double mm2deg(double distance, double mm) {
		return Math.atan(mm / distance) * 180.0 / Math.PI;
	}

	public double deg2mm(double distance, double deg) {
		return Math.tan(deg * Math.PI / 180.0) * distance;
	}

	
	
	
	
	// randomizers
	
	public static int randRange(int upper, int lower) {
		// this creates a random number between upper and lower (inclusive)
		if (lower > upper) System.out.println("---Error: lower is larger than upper!---");
		int rand = (int)(Math.random()*((upper-lower)+1))+lower;
		return rand;
	}
	
	public static int[] randRange(int upper, int lower, int numRands) {
		if (lower > upper) System.out.println("---Error: lower is larger than upper!---");
		int[] rand = new int[numRands];
		for (int n=0;n<numRands;n++) {
			rand[n] = (int)(Math.random()*((upper-lower)+1))+lower;
		}
		return rand;
	}
	
	public static double randRange(double upper, double lower) {
		// this creates a random number between upper and lower
		double rand = rescaleValue(Math.random(),upper,lower);
		return rand;
	}
	
	public static double[] randRange(double upper, double lower,int numRands) {
		// this creates a random number between upper and lower
		double[] rand = new double[numRands];
		for (int n=0;n<numRands;n++) {
			rand[n] = rescaleValue(Math.random(),upper,lower);
		}
		return rand;
	}
	
	public static float randRange(float upper, float lower) {
		// this creates a random number between upper and lower
		float rand = rescaleValue((float)Math.random(),upper,lower);
		return rand;
	}
	
	public static double rescaleValue(double x, double upper, double lower) {
		// this rescales a value bounded by upper and lower limits
		if (lower >= upper) System.out.println("---Error: lower is larger than upper!---");
		x = x * (upper-lower) + lower;
		return x;
	}
	
	public static float rescaleValue(float x, float upper, float lower) {
		// this rescales a value bounded by upper and lower limits
		if (lower >= upper) System.out.println("---Error: lower is larger than upper!---");
		x = x * (upper-lower) + lower;
		return x;
	}
	
	public static boolean randBoolean(){
		return rand.nextBoolean();
	}
	
	public static boolean[] randBoolean(double propTrue,int numRands){
		// propTrue: the average proportion of 'true' results (0:1)
		// numRands: the number of random booleans to create
		boolean[] out = new boolean[numRands];
		for (int n=0;n<numRands;n++) {
			out[n] = rand.nextDouble()<propTrue;
		}
		return out;
	}
	
	public static boolean randBoolean(double propTrue){
		return randBoolean(propTrue,1)[0];
	}
	
	public static double randGauss(double sigma,double mu) {
		return rand.nextGaussian() * sigma + mu;		
	}
	
	public static double randBoundedGauss(double sigma, double mu, double vMin, double vMax) {
		double out;
		do { out = SachMathUtil.randGauss(sigma,mu);
		} while (out < vMin || out > vMax);
		return out;		
	}
	
	public static double randUshaped(double vMin,double vMax, double ctr) {
		// input checking:
		if (vMin >= vMax || ctr < vMin || ctr > vMax) {
			System.err.println("ERROR: check inputs!! ctr must lie between vMin and vMax!");
			return -1;
		}
		
		// remove vMin from inputs:
		vMax-=vMin;
		ctr-=vMin;
		
		// other vairables:
		double hlf = vMax/2;
		double sd = vMax/4;	// this seems to do the best job
		double r,d,m,p=0;
		boolean repeat;
		
		do {
			repeat = false;
			r = rand.nextGaussian()*sd+hlf;
			
			if (ctr<hlf) {
				m = (vMax-ctr)/hlf;
				d = vMax-ctr/m;
				if (r>0 && r<hlf) {
					p = r*m+ctr;
				} else if (r>d && r<vMax) {
					p = (r-d)*m;
				} else {
					repeat = true;
				}
			} else {
				m = ctr/hlf;
				d = (vMax-ctr)/m;
				if (r>0 && r<d) {
					p = r*m+ctr;
				} else if (r>hlf && r<vMax) {
					p = (r-hlf)*m;
				} else {
					repeat = true;
				}
			}
		} while (repeat);		
		
		return p+vMin;	// add back vMin
	}

	public static double[] randUshaped(double vMin,double vMax, double ctr,int numVals) {
		double[] p = new double[numVals];
		for (int n=0;n<numVals;n++) {
			p[n] = randUshaped(vMin,vMax,ctr);
		}
		return p;
	}
	
	public static double[] randUshaped(double vMin,double vMax, double[] ctr,int numVals) {
		double[] p = new double[numVals];
		for (int n=0;n<numVals;n++) {
			p[n] = randUshaped(vMin,vMax,ctr[n]);
		}
		return p;
	}
	
	// ------
	
	public static int[] removeElement(int[] s, int r) {
	    List<Integer> result = new ArrayList<Integer> ();
	    for (int i : s) {
	        if (i != r) {
	            result.add(i);
	        }
	    }

	    int[] toReturn = new int[result.size()];
	    for (int i=0; i<result.size(); i++) {
	        toReturn[i] = result.get(i);
	    }

	    return toReturn;
	}
	
	public static double[] rotate2D(double deg,double pt[])
	{ // rotate about 0,0
		double result[]= new double[2];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		result[0]=cosdeg*pt[0]-sindeg*pt[1];
		result[1]=sindeg*pt[0]+cosdeg*pt[1];
		
		return result;
	}
	
	public static double[][] rotate2D(double deg,double pt[][])
	{ // rotate about 0,0
		double result[][] = new double[pt.length][2];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);
		
		for (int n=0; n<pt.length; n++) {
			result[n][0]=cosdeg*pt[n][0]-sindeg*pt[n][1];
			result[n][1]=sindeg*pt[n][0]+cosdeg*pt[n][1];
		}
		return result;
	}
	
	public static double[] rotateAxis2D(double deg, double ctr[], double pt[]){
		// rotate point (pt) deg degrees around arbitrary center (ctr)
		double result[] = new double[2];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		result[0] = cosdeg*(pt[0]-ctr[0]) - sindeg*(pt[1]-ctr[1]) + ctr[0];
		result[1] = sindeg*(pt[0]-ctr[0]) + cosdeg*(pt[1]-ctr[1]) + ctr[1];

		return result;
	}

	public static double[][] rotateAxis2D(double deg, double ctr[], double pt[][]){
		// rotate point (pt) deg degrees around arbitrary center (ctr)
		double result[][] = new double[pt.length][2];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);
		
		for (int n=0; n<pt.length; n++) {
			result[n][0] = cosdeg*(pt[n][0]-ctr[0]) - sindeg*(pt[n][1]-ctr[1]) + ctr[0];
			result[n][1] = sindeg*(pt[n][0]-ctr[0]) + cosdeg*(pt[n][1]-ctr[1]) + ctr[1];
		}
		return result;		
	}
	
	final static public double[][] mergeArrays(final double[][] ...arrays) {
		int size = 0;
		for (double[][] a: arrays) size += a.length;
		double[][] res = new double[size][2];
		int destPos = 0;
		for (int i=0;i<arrays.length;i++) {
			if (i>0) destPos += arrays[i-1].length;
			int length = arrays[i].length;

			System.arraycopy(arrays[i],0,res,destPos,length);
		}
		return res;
	}
	
	final static public int[][] mergeArrays(final int[][] ...arrays) {
		int size = 0;
		for (int[][] a: arrays) size += a.length;
		int[][] res = new int[size][2];
		int destPos = 0;
		for (int i=0;i<arrays.length;i++) {
			if (i>0) destPos += arrays[i-1].length;
			int length = arrays[i].length;

			System.arraycopy(arrays[i],0,res,destPos,length);
		}
		return res;
	}
	
	final static public int[] mergeArrays(final int[] ...arrays) {
		int size = 0;
		for (int[] a: arrays) size += a.length;
		int[] res = new int[size];
		int destPos = 0;
		for (int i=0;i<arrays.length;i++) {
			if (i>0) destPos += arrays[i-1].length;
			int length = arrays[i].length;

			System.arraycopy(arrays[i],0,res,destPos,length);
		}
		return res;
	}
	
	// search
	
	public static int searchMtxIntArr(int[][] mtx,int[] elem) {
		// find elem (int[]) in mtx (int[][]):
		for (int n=0;n<mtx.length;n++) {
			if (mtx[n][0] == elem[0] & mtx[n][1] == elem[1]) {
				return n;
			}			
		}
		return -1; // not found
	}

	public static int[] findAllValues(int[] ARR,int ELEM) {
		// output all indices where the elements of the array ARR equal ELEM
		int[] outArr = new int[ARR.length];
		int counter = 0;
		
		for (int n=0;n<ARR.length;n++) {
			if (ARR[n] == ELEM) {
				outArr[counter] = n;
				counter++;
			}
		}
		outArr = resizeArray(outArr,counter);
		
		return outArr;
	}
	
	public static int findFirst(double[] ARR,double ELEM) {
		// output first index where the elements of the array ARR equal ELEM
		for (int n=0;n<ARR.length;n++) {
			if (ARR[n] == ELEM) {
				return n;
			}
		}
		return -1;
	}
	
	public static int[] resizeArray(int[] oldArr,int desiredLength) {
		int[] newArr = new int[desiredLength];
		for(int k=0; k<desiredLength; k++){
			newArr[k]= oldArr[k]; 
		}
		return newArr;
	}
	
	public static double[][] deepCopyMatrix(double[][] inMtx) {
		int numRows = inMtx.length;
		double[][] outMtx = new double[numRows][];
		for(int row=0;row<numRows;row++) {
			outMtx[row] = inMtx[row].clone();
		}
		
		return outMtx;
	}
	
	
	   
	public static int[] unique(int[] arr) {
		/* Function: unique
		 * It finds the unique elements in 'arr' and returns the unique elements, preserving their order.
		 */
		int[] finalUniqueElements = new int[]{};
		int numElements = arr.length;
		if (numElements < 1) return finalUniqueElements;
		int[] uniqueElements = new int[arr.length];
		int counter,uniqueElementCounter;
		int testElement;
		boolean foundRepeat = false;

		uniqueElements[0] = arr[0];
		uniqueElementCounter = 1;
		for(int i=1;i<numElements;i++){
			testElement = arr[i];
			counter = i-1;
			foundRepeat = false;
			while((counter>=0) &&(!foundRepeat)){
				if(testElement==arr[counter])
					foundRepeat = true;	

				counter--;	
			}
			if (!foundRepeat){
				uniqueElements[uniqueElementCounter] = testElement;
				uniqueElementCounter++;
			}

		}

		// Re-size uniqueElements
		finalUniqueElements = new int[uniqueElementCounter];
		for (int i=0;i<uniqueElementCounter;i++){
			finalUniqueElements[i] = uniqueElements[i];
		}
		
		return finalUniqueElements;
	}
	
	
	
	// ---------------------------
	
	public static double[] findPointAlongLine(double inPoint[], double deg, double length) {
		// angle in degrees
		double rad = deg*Math.PI/180; 
		double[] outPoint = {inPoint[0] + length*Math.cos(rad),inPoint[1] + length*Math.sin(rad)};
		
		return outPoint;
	}
	
	public static double[] findLineIntersection(double pt1[], double deg1, double pt2[], double deg2) {
		// find if points P and Q intersect, points are double[]={x,y}
		double[] intersectPt = new double[2];
		
		double length = 1;
		double[] pt1_ = findPointAlongLine(pt1,deg1,length);
		double[] pt2_ = findPointAlongLine(pt2,deg2,length);
		
		// Ax + By = C, A = y2-y1, B = x2-x1, C = A*x1+B*y1
		double A1 = pt1_[1] - pt1[1]; 
		double A2 = pt2_[1] - pt2[1]; 
		double B1 = pt1[0] - pt1_[0]; 
		double B2 = pt2[0] - pt2_[0]; 
		double C1 = A1*pt1[0] + B1*pt1[1]; 
		double C2 = A2*pt2[0] + B2*pt2[1];
		
		double det = A1*B2 - A2*B1;
		
		if (det == 0) {
			// if lines parallel, return the midline between the points
			intersectPt[0] = (pt1[0]+pt2[0])/2;
			intersectPt[1] = (pt1[1]+pt2[1])/2;
			//intersectPt = null;
		} else {
			intersectPt[0] = (B2*C1 - B1*C2)/det;
			intersectPt[1] = (A1*C2 - A2*C1)/det;
		}
		
		return intersectPt;
	}
	
	
	
	
	
	
	// VECTOR MATH -- linear algebra ------------------------------------------------------------------------------------
	
	/* Convert angle (theta) in degrees and magnitude (rho) to vector cartesian coordinates [x y] */
	public static double[] pol2vect(double theta, double rho) {
		double x = rho * Math.cos(theta*Math.PI/180);		// +y = 90deg, +x = 0deg --- zero is to the right!
		double y = rho * Math.sin(theta*Math.PI/180);

		return new double[]{x,y};
	}
	
	/* Get angle from vector point */
	public static double vectorAngle(double[] pt) {
		double theta = Math.atan2(pt[1],pt[0])*180/Math.PI;		// convert to degrees
		//double rho   = Math.hypot(pt[0],pt[1]);

		return theta; 
	}
	
	/* Dot product of vectors A and B (either 2D or 3D)
	 */
	public static double doDotProd(double A[], double B[])
	{
		double Result;
		double temp = 0;
		int ALength = A.length;

		for(int i=0;i<ALength;i++){
			temp = temp + A[i]*B[i];
		}

		Result = temp;

		return Result;	
	}


	/* Function: getAngle. It finds the angle between vectors A and B in degrees: (either 2D or 3D)
	 * If one or both of the vector of zero magnitude the angle is assigned to zero.
	 */
	public static double getAngle(double A[], double B[])
	{
		double Result;
		double temp1, temp2;
		double magA = vectorMagnitude(A);
		double magB = vectorMagnitude(B);

		temp1 = doDotProd(A,B);
		if(magA==0 || magB==0)
			Result =0;
		else{   
			temp2 = temp1/(magA*magB);
			Result  = Math.acos(temp2)*180/Math.PI;
		}
		return Result;	
	}


	/*
	 * Find vector magnitude. (either 2D or 3D)
	 */
	public static double vectorMagnitude(double A[]){
		double Result;
		double temp = 0;
		int ALength = A.length;

		for(int i=0;i<ALength;i++){
			temp = temp + A[i]*A[i];
		}

		Result = Math.sqrt(temp);	

		return Result;
	}

	/*
	 * Normalize vector
	 */ 
	public static double[] normVector(double[] unNormVector){
		int legthVect = unNormVector.length;
		double[] Result = new double[legthVect];
		double mag = vectorMagnitude(unNormVector);

		if (mag == 0){
			for(int i=0;i<legthVect;i++){
				Result[i] = unNormVector[i];
			}
		}
		else{
			for(int i=0;i<legthVect;i++){
				Result[i] = unNormVector[i]/mag;
			}

		}

		return Result;
	}

	
	/* Find bisecting vector angle -- add unit vectors and get angle, returns direction of smaller angle */
	public static double bisectingVector(double[] A,double[] B) {
			// assuming 2D vectors
		int vecDims = A.length;
		if (vecDims > 2) System.err.println("vector has too many dimensions!");
		
			// get unit vectors for each
		double[] unitA = normVector(A);
		double[] unitB = normVector(B);
		
		return vectorAngle(addVectors(unitA,unitB));
	}
	
	/* add vectors */
	public static double[] addVectors(double[] A,double[] B) {
		int vecDims = A.length;
		double[] res = new double[vecDims];
		
		for (int n=0;n<vecDims;n++) {
			res[n] = A[n] + B[n];
		}
		
		return res;
	}
	
	/* subtract vectors */
	public static double[] subtractVectors(double[] A,double[] B) {
		int vecDims = A.length;
		double[] res = new double[vecDims];
		
		for (int n=0;n<vecDims;n++) {
			res[n] = A[n] - B[n];
		}
		
		return res;
	}
	

	/*
	 * Vector product: (3D)
	 */

	public static double[] doVectorProd(double[] A,double[] B){
		double[] Result = new double[3];
		double Ax = A[0],Ay=A[1],Az=A[2];
		double Bx = B[0],By=B[1],Bz=B[2];

		// Cross-product of A X B:	
		Result[0]=Ay*Bz-Az*By;
		Result[1]=Az*Bx-Ax*Bz;
		Result[2]=Ax*By-Ay*Bx;

		return Result;
	}

	// --------------------------------
	
	public static double vectSum(double[] vect,int[] idx) {
		// sum over the idx members of the vector
		double sum = 0;
		for (int n : idx) {
			sum += vect[n];
		}
		return sum;
	}
	
	public static double vectSum(double[] vect) {
		// sum over all members of the vector
		double sum = 0;
		for (int n=0;n<vect.length;n++) {
			sum += vect[n];
		}
		return sum;
	}
	
	public static double vectSum(int[] vect) {
		// sum over all members of the vector
		double sum = 0;
		for (int n=0;n<vect.length;n++) {
			sum += vect[n];
		}
		return sum;
	}
	
	
	//-------------------------------
	// sorting
	
	
//	public static double[] sort(double a[]) {
//		for (int i = 0; i < a.length; i++) {
//		    int min = i;
//	            int j;
//
//	            /*
//	             *  Find the smallest element in the unsorted list
//	             */
//	            for (j = i + 1; j < a.length; j++) {
//		        if (stopRequested) {
//			    return;
//	                }
//
//			if (a[j] < a[min]) {
//	                    min = j;
//	                }
//		        pause(i,j);
//		    }
//
//	            /*
//	             *  Swap the smallest unsorted element into the end of the
//	             *  sorted list.
//	             */
//	            int T = a[min];
//	            a[min] = a[i];
//		    a[i] = T;
//		    pause(i,j);
//	        }
//	    }
	
	public static int[] selectionSort(double[] xin) {
		double[] xout = Arrays.copyOf(xin,xin.length);
		int[] idxs = new int[xin.length];
		
	    for (int i=0; i<xout.length; i++) {
	        int minIndex = i;      // Index of smallest remaining value.
	        for (int j=i+1; j<xout.length; j++) {
	            if (xout[minIndex] > xout[j]) {
	                minIndex = j;  // Remember index of new minimum
	            }
	        }
	        if (minIndex != i) { 
	            //...  Exchange current element with smallest remaining.
	            double temp = xout[i];
	            xout[i] = xout[minIndex];
	            xout[minIndex] = temp;
	            idxs[i] = minIndex;
	        } else {
	        	idxs[i] = i;
	        }
	        	
	    }
	    
	    return idxs;
	}
	
	
	// Sorts numbers from low to high and returns the sorted indices (not the numbers)
	public static int[] sortLowToHighIndx(double[] tempArray){
		int min; double temp;
		int arrLength = tempArray.length;
		double[] numbers = new double[arrLength];
		int[] indicesSort = new int[arrLength];
		int tempIndx;

		for (int i=0;i<arrLength;i++){
			numbers[i] = tempArray[i];
		}
		for (int i=0;i<arrLength;i++){
			indicesSort[i]=i;	
		}

		for(int index=0;index<(arrLength-1);index++){
			min =index;
			for(int scan=(index+1);scan<arrLength;scan++){
				if(numbers[scan]<numbers[min]){
					min = scan;
				}
			}
			temp = numbers[min];
			numbers[min] = numbers[index];
			numbers[index] = temp;

			tempIndx = indicesSort[min];
			indicesSort[min] = indicesSort[index];
			indicesSort[index] = tempIndx;

		}

		return indicesSort;
	}
	
	public static boolean areAnyNull(double[][] Arr){
		for (int n=0;n<Arr.length;n++) {
			if (Arr[n] == null) {
				return true;
			}
		}
		return false;
	}
	
	public static boolean isArrEqual(byte[] A,byte[] B) {
		int lenA = A.length;
		int lenB = B.length;
		if (lenA != lenB) return false;
		
		for (int n=0;n<lenA;n++) {
			if (A[n] != B[n]) return false;
		}
		return true;
	}
	
	// ----------------------------
	
	public static double mean(double[] ARR) {
		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();
		for (int n=0;n<ARR.length;n++) {
			stats.addValue(ARR[n]);
		}
		return stats.getMean();	
	}
	
	public static long mean(long[] ARR) {
		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();
		for (int n=0;n<ARR.length;n++) {
			stats.addValue(ARR[n]);
		}
		return (long) stats.getMean();	
	}
	
	public static double std(double[] ARR) {
		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();
		for (int n=0;n<ARR.length;n++) {
			stats.addValue(ARR[n]);
		}
		return stats.getStandardDeviation();
	}
	
	public static double mean(List<Double> ARR) {
		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();
		for (int n=0;n<ARR.size();n++) {
			stats.addValue(ARR.get(n));
		}
		return stats.getMean();	
	}
	
	public static double std(List<Double> ARR) {
		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();
		for (int n=0;n<ARR.size();n++) {
			stats.addValue(ARR.get(n));
		}
		return stats.getStandardDeviation();
	}
	
	
	
	// ------------------------------
	
	public static double[][] flipMtx(double[][] inMtx) {
		int numRows = inMtx.length;
		int numCols = inMtx[0].length;
		double[][] outMtx = new double[numCols][numRows];
		for(int row=0;row<numRows;row++) {
			for(int col=0;col<numCols;col++) {
				outMtx[col][row] = inMtx[row][col];
			}
		}
		return outMtx;
	}
	
	public static int min(int... args) {
        int m = Integer.MAX_VALUE;
        for (int a : args) {
            m = Math.min(m, a);
        }
        return m;
    }

    public static int max(int... args) {
        int m = -Integer.MAX_VALUE;
        for (int a : args) {
            m = Math.max(m, a);
        }
        return m;
    }
	
    public static double min(double... args) {
    	double m = Double.POSITIVE_INFINITY;
        for (double a : args) {
            m = Math.min(m, a);
        }
        return m;
    }

    public static double max(double... args) {
    	double m = Double.NEGATIVE_INFINITY;
        for (double a : args) {
            m = Math.max(m, a);
        }
        return m;
    }
    
    public static double max(int col, double[]... args) {
    	double m = Double.NEGATIVE_INFINITY;
        for (double[] a : args) {
            m = Math.max(m, a[col]);
        }
        return m;
    }
	
    public static double min(int col, double[]... args) {
    	double m = Double.POSITIVE_INFINITY;
        for (double[] a : args) {
            m = Math.min(m, a[col]);
        }
        return m;
    }
    
	public static List<Double[]> convertToCollection(double[][] in) {
		// output a list of Double[] for x values and Double[] for y values:
		List<Double[]> out = new ArrayList<Double[]>();
		int numVals = in.length;
		Double[] x = new Double[numVals];
		Double[] y = new Double[numVals];
		
		for (int n=0;n<numVals;n++) {
			x[n] = Double.valueOf(in[n][0]);
			y[n] = Double.valueOf(in[n][1]);
		}		
		return out;
	}
	
	public static double[] pow_nonImag(double[] x,double exponent) {
		// avoid imaginary number issues to that I can compute y = x^(1/3) for negative x values
		int numVals = x.length;
		double[] y = new double[numVals];
		
		for (int n=0;n<numVals;n++) {
			y[n] = Math.signum(x[n])*Math.pow(Math.abs(x[n]),exponent);		
		}
		return y;		
	}
	
	public static double pow_nonImag(double x,double exponent) {
		// avoid imaginary number issues to that I can compute y = x^(1/3) for negative x values
		return Math.signum(x)*Math.pow(Math.abs(x),exponent);		
	}
	
	public static double cubeRootFcn(double x,double max) {
		// function for a scaled cube root with offset
		// x = [0:1]
		return max*(pow_nonImag(x*2-1,1/3d)+1)/2;
	}
	
	public static double[] cubeRootFcn(double[] x,double max) {
		// function for a scaled cube root with offset
		// x = [0:1]
		int numVals = x.length;
		double[] y = new double[numVals];
		
		for (int n=0;n<numVals;n++) {
			y[n] = max*(pow_nonImag(x[n]*2-1,1/3d)+1)/2;		
		}
		return y;
	}
	
	public static double nPowerFcn(double x,double max,double exponent) {
		// function for a scaled and shifted power function
		// input: x = [0:1]
		// output: shifted zero to 0.5, output ranges from 0 to max
		return max*(pow_nonImag(x*2-1,exponent)+1)/2;
	}
	
	public static double erf(double z) {
		// error function approximation
		// fractional error in math formula less than 1.2 * 10 ^ -7.
	    // although subject to catastrophic cancellation when z in very close to 0
	    // from Chebyshev fitting formula for erf(z) from Numerical Recipes, 6.2
		double t = 1.0 / (1.0 + 0.5 * Math.abs(z));

        // use Horner's method
        return Math.signum(z) * (1 - t * Math.exp( -z*z   -   1.26551223 +
        		t * ( 1.00002368 +
        				t * ( 0.37409196 + 
        						t * ( 0.09678418 + 
        								t * (-0.18628806 + 
        										t * ( 0.27886807 + 
        												t * (-1.13520398 + 
        														t * ( 1.48851587 + 
        																t * (-0.82215223 + 
        																		t * ( 0.17087277))))))))) ) );
    }
	

	
	
	// -------------------------------------
	// collision test stuff:
	
	public static boolean anyInBoundingBox(double[][] poly,double[]...pts) {
		// find if any points lie within a box bounding a polygon
		// pts and poly are arrays of [x y] arrays	
		double maxX = SachMathUtil.max(0,poly);
		double minX = SachMathUtil.min(0,poly);
		double maxY = SachMathUtil.max(1,poly);
		double minY = SachMathUtil.min(1,poly);
		
		for (double[] pt : pts) {
			if (pt[0]>=minX && pt[0]<=maxX && pt[1]>=minY && pt[1]<=maxY) {
				return true;
			}
		}
		return false;
	}
	
	public static double[][] inBoundingBox(double[][] poly,double[]...pts) {
		// find any points that lie within a box bounding a polygon
		// pts and poly are arrays of [x y] arrays
		List<Double[]> inPts = new ArrayList<Double[]>();
		
		double maxX = SachMathUtil.max(0,poly);
		double minX = SachMathUtil.min(0,poly);
		double maxY = SachMathUtil.max(1,poly);
		double minY = SachMathUtil.min(1,poly);
		
		for (double[] pt : pts) {
			if (pt[0]>=minX && pt[0]<=maxX && pt[1]>=minY && pt[1]<=maxY) {
				inPts.add(new Double[]{pt[0],pt[1]});
			}
		}
		
		double[][] inPtsOut = new double[inPts.size()][2];
		Double[] xy;
		for(int n=0;n<inPts.size();n++) {
			xy = inPts.get(n);
			inPtsOut[n] = new double[]{xy[0],xy[1]};
		}
		return inPtsOut;
	}
	
	public static boolean isInPolygon(double[][] poly,double[]...pts) {
		// find whether any points are inside a polygon
		double[] ptXtreme;
		int count, next;
		int numVerts = poly.length;
		
		for (double[] pt : pts) {
			ptXtreme = new double[]{Double.MAX_VALUE,pt[1]};
			count = 0;
			
			for (int i=0;i<numVerts;i++) {
				next = (i+1)%numVerts;
				if (doIntersect(poly[i],poly[next],pt,ptXtreme)) {
					if (orientation(poly[i],pt,poly[next]) == 0) {
						return onSegment(poly[i],pt,poly[next]);
					}
					count++;
				}
			}
			if (count%2 == 1) {	// if odd
				return true;
			}
		}
		return false;
	}
	
	public static boolean doesLineCrossPolygon(double[][] poly,double[] ptA, double[] ptB) {
		// This is a special case, where I'm trying to find out if a new limb
		// will overlap any part of the existing limbs. if only their lengths 
		// (and not control pts) instersect, then the isInPolygon method won't 
		// capture this overlap. So here I use the line segment from the center 
		// of the old node to the center of the new one and find if it crosses 
		// the polygon border more than once (it needs to cross one time when the 
		// old node center exits the polygon describing the current control pts. 
		// inputs: poly contains the ordered list of polygon points, ptA and ptB 
		// 		   are the start and end of the line segment
		
		int count, next;
		int numVerts = poly.length;
		
		count = 0;

		for (int i=0;i<numVerts;i++) {
			next = (i+1)%numVerts;
			if (doIntersect(poly[i],poly[next],ptA,ptB)) {
				int ori = orientation(ptA,ptB,poly[i]);		// this has to be in the same order as done in doIntersect or you get float poat precision errors!
				if (ori == 0) {	// in case point is on line segment, don't count twice!
					break;
				}
				count++;
			}
			if (count > 1) return true;
		}
		return false;
	}
	
	
	public static boolean doIntersect(double[] p1,double[] q1,double[] p2,double[] q2) {
		// function that returns true if line segment 'p1q1' and 'p2q2' intersect.
		// Find the four orientations needed for general and
	    // special cases
	    int o1 = orientation(p1, q1, p2);
	    int o2 = orientation(p1, q1, q2);
	    int o3 = orientation(p2, q2, p1);
	    int o4 = orientation(p2, q2, q1);
	 
	    // General case
	    if (o1 != o2 && o3 != o4)
	        return true;
	 
	    // Special Cases
	    // p1, q1 and p2 are colinear and p2 lies on segment p1q1
	    if (o1 == 0 && onSegment(p1, p2, q1)) return true;
	 
	    // p1, q1 and p2 are colinear and q2 lies on segment p1q1
	    if (o2 == 0 && onSegment(p1, q2, q1)) return true;
	 
	    // p2, q2 and p1 are colinear and p1 lies on segment p2q2
	    if (o3 == 0 && onSegment(p2, p1, q2)) return true;
	 
	     // p2, q2 and q1 are colinear and q1 lies on segment p2q2
	    if (o4 == 0 && onSegment(p2, q1, q2)) return true;
	 
	    return false; // Doesn't fall in any of the above cases
	}
	
	static int orientation(double[] p,double[] q,double[] r) {
		// find orientation of ordered triplet of points (p, q, r). 
		// output: 0 --> p, q and r are colinear; 1 --> Clockwise; 2 --> Counterclockwise		
		double val = (q[1]-p[1])*(r[0]-q[0]) - (q[0]-p[0])*(r[1]-q[1]);
	 
	    if (val == 0) return 0;	// colinear
	    return (val > 0)? 1: 2; // clock or counterclock wise
	}
	
	public static boolean onSegment(double[] p,double[] q,double[] r) {
		// Given three colinear points p, q, r, the function checks if point q lies on line segment 'pr'
		if (q[0]<=max(p[0],r[0]) && q[0]>=min(p[0],r[0]) && q[1]<=max(p[1],r[1]) && q[1]>=min(p[1],r[1]))
	        return true;
	    return false;
	}
	
	public static boolean doAnySegmentsCross(double[][] pts) {
		// this method checks if any segment (from consecutive pts) crosses any other
		// input: pts -- an array of x,y points, a segment is composed of any consecutive set of points
		// output: true if any line segments cross any other from the set of points
		
		int numVerts = pts.length;
		int m_next,n_next;
		
		for (int m=0;m<numVerts;m++) {
			m_next = (m+1)%numVerts;
			for (int n=m+1;n<numVerts;n++) {
				n_next = (n+1)%numVerts;
				if (doIntersect(pts[m],pts[m_next],pts[n],pts[n_next])) {
					// check if points are the same
					if (pts[m_next]!=pts[n] && pts[n_next]!=pts[m]) {
						return true;
					}
				}
			}
		}
			
		return false;
	}
}


	
