package org.xper.sach.util;

import java.util.Random;
//import shape_template.*;

public class MyMathRepository {

	public static double epsilon = 0.000001;	
	public static Random rand = new Random(); // uses the current time in msec to set seed


	/* Generating a random number (non-integer) between 'a' and 'b'. */	
	public static double randDouble(double a, double b) {
		double Result;

		Result=rand.nextDouble() * (b-a) + a;
		return Result;
	}

	public static int randInteger(int low,int high){
		int Result;
		//Random rand = new Random();
		//int tmp = (rand.nextInt())%(high-low+1);
		//if(tmp<0)
		//tmp = -tmp;

		Result = low + rand.nextInt(high-low+1);

		return Result;
	}

	public static boolean randBoolean(){
		boolean Result;

		Result = rand.nextBoolean();
		return Result;
	}


	/* Note that rand.nextGaussian() generates random values from a normal 
	 * distribution with mean mu=0 and standard deviation sigma = 1;
	 * To generation a rand number from a distribution with mean=currentVal
	 * and sigma= spreadSTD, we do currentVal + spreadSTD*rand.nextGaussian()
	 * 
	 */
	public static double randGauss(double currentVal, double spreadSTD){
		double Result;

		Result = 	currentVal + spreadSTD*rand.nextGaussian();

		return Result;
	}

	public static double applyUniformTrans(double origVal,double halfWidth,double minVal,double maxVal,boolean circular){

		double newVal;
		double lowerLim,upperLim;

		lowerLim = origVal - halfWidth;
		upperLim = origVal + halfWidth;

		newVal = randDouble(lowerLim, upperLim);

		if(newVal>maxVal){
			if(!circular){
				newVal = maxVal;
			}
			else{
				newVal = minVal + (newVal - maxVal);
			}
		}
		else{
			if(newVal<minVal)
				if(!circular){
					newVal = minVal;
				}
				else{
					newVal = maxVal - (minVal-maxVal);
				}
		}


		return newVal;
	}



	public static int randInteger_CDF(double[] cdfList){

		int lengthOfCDF = cdfList.length;
		if(lengthOfCDF==0){
			System.out.println("Should not reach this part of the code");
			System.exit(-1);
		}


		double tmpNum = MyMathRepository.randDouble(0.0,1.0);

		int i=0;
		while (i<lengthOfCDF){

			if(tmpNum <= cdfList[i])
				return i;
			else
				i++;
		}

		if(tmpNum == cdfList[lengthOfCDF-1])
			return (lengthOfCDF-1);

		System.out.println("Should not reach this part of the code");
		System.exit(-1);

		return -1;
	}





	/* Calculates vergence angle (degrees) using interOcularDist and distance of fixation point from
    viewer (fixation depth) */
	public static double calcVergenceAngleToDepth(double interOcularDist,double fixDepth){
		double tempRadians;
		tempRadians = 2*Math.atan((interOcularDist/2)/fixDepth);
		return tempRadians*180/Math.PI;
	}

	/* Calculates fixation depth (from viewer/camera) corresponding to a vergence angle (degrees_ */   
	public static double calcDepthToVergenceAngle(double interOcularDist,double vergAngle){
		double vergeAngleRadians = vergAngle*Math.PI/180;
		return (interOcularDist/2)/Math.tan(vergeAngleRadians/2);
	}    


	/* Calculates the radius of a sphere required to be 'sizeDeg' in visual angle w.r.t camera and
	 * at a fixation depth of 'fixDepth' (again w.r.t to camera). The angle refers to the peak-to-peak
	 * distance when the sphere is placed such that the front is at the fixation point.
	 * Note: The angle must be less than 45 degrees for this function to work properly.
	 * */
	public static double calcSphereRadius(double sizeDeg,double fixDepth)throws OutOfRangeException{
		if(sizeDeg>=45)
			throw new OutOfRangeException("Angle needs to be less than 45");

		double tmpAng = Math.tan((sizeDeg/2)*Math.PI/180);
		double Result = -(fixDepth*tmpAng)/(tmpAng - 1);

		return Result;

	}    

	/* Converts the normalized size parameter globalMorphSize to real physical size     
  double minStimSizeInDeg, double maxStimSizeInDeg,double minGlobalMorphSize,double maxGlobalMorphSize
	 */
	//public static double unNormSize(double globalMorphSize, double fixationDepth){
	//	double radiusMin = calcSphereRadius(TestSphere.minStimSizeInDeg,fixationDepth);
	// 	double radiusMax = calcSphereRadius(TestSphere.maxStimSizeInDeg,fixationDepth);	
	//  	return (radiusMax- radiusMin)*(globalMorphSize - TestSphere.minGlobalMorphSize)/(TestSphere.maxGlobalMorphSize - TestSphere.minGlobalMorphSize) + radiusMin;
	//   }


	/* Rotations about principle axes:
	 *  -Right-hand coordinate system.
	 *  - Sign of rotations. E.g. If from the origin we look down the positive x-axis, a positive rotation will be clock-wise about that axis. 
	 *  // Note if one the otheer hand we're looking down the negative x-axis it will be counter-clockwise.
	 */
	public static double[] RotateX(double deg, double Pt[]) 
	{	  
		double PtX=Pt[0],PtY=Pt[1],PtZ=Pt[2];
		double Result[]= new double[3];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		Result[0]=PtX;
		Result[1]=PtY*cosdeg-PtZ*sindeg;
		Result[2]=PtY*sindeg+PtZ*cosdeg;

		return Result;
	}

	public static double[] RotateY(double deg,double Pt[])
	{
		double PtX=Pt[0],PtY=Pt[1],PtZ=Pt[2];
		double Result[]= new double[3];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		Result[0]=PtX*cosdeg+PtZ*sindeg;
		Result[1]=PtY;
		Result[2]=-PtX*sindeg+PtZ*cosdeg;
		return Result;
	}

	public static double[] RotateZ(double deg,double Pt[])
	{
		double PtX=Pt[0],PtY=Pt[1],PtZ=Pt[2];
		double Result[]= new double[3];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		Result[0]=PtX*cosdeg-PtY*sindeg;
		Result[1]=PtX*sindeg+PtY*cosdeg;
		Result[2]=PtZ;
		return Result;
	}

	public static double[] Rotate2D(double deg,double Pt[])
	{
		double PtX=Pt[0],PtY=Pt[1];
		double Result[]= new double[2];
		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		Result[0]=PtX*cosdeg-PtY*sindeg;
		Result[1]=PtX*sindeg+PtY*cosdeg;
		return Result;
	}
	
	public static double[][] Rotate2D(double deg,double Pt[][])
	{	
		double result[][] = new double[Pt.length][2];
		for (int n=0; n<Pt.length; n++) {
			double cosdeg = Math.cos(deg*Math.PI/180);
			double sindeg = Math.sin(deg*Math.PI/180);
	
			result[n][0]=Pt[n][0]*cosdeg-Pt[n][1]*sindeg;
			result[n][1]=Pt[n][0]*sindeg+Pt[n][1]*cosdeg;
		}
		return result;

	}
	
	
	
	/* Rotation about an arbitrary axis: The convention as always is if we are looking from the origin to the tip of the axis then a positive
	 * 'deg' will turn us clockwise, equivalently if from the tip we look down at the origin a positive 'deg' will be anti-clock wise.
	 * axis needs to be a unit vector defined in the same coordinate system as point.
	 */

	public static double[] RotateAboutAxis(double deg, double axis[], double Pt[]){

		double resultX,resultY,resultZ;	
		double PtX=Pt[0],PtY=Pt[1],PtZ=Pt[2];
		double axisX=axis[0],axisY=axis[1],axisZ=axis[2];
		double Result[] = new double[3];

		double cosdeg = Math.cos(deg*Math.PI/180);
		double sindeg = Math.sin(deg*Math.PI/180);

		resultX = (cosdeg + (1-cosdeg)*axisX*axisX)*PtX;
		resultX+= ((1-cosdeg)*axisX*axisY - axisZ*sindeg)*PtY;
		resultX+= ((1-cosdeg)*axisX*axisZ + axisY*sindeg)*PtZ;

		resultY = ((1-cosdeg)*axisX*axisY + axisZ*sindeg)*PtX;
		resultY+= (cosdeg + (1-cosdeg)*axisY*axisY)*PtY;
		resultY+= ((1-cosdeg)*axisY*axisZ - axisX*sindeg)*PtZ;

		resultZ = ((1-cosdeg)*axisX*axisZ - axisY*sindeg)*PtX;
		resultZ+= ((1-cosdeg)*axisY*axisZ + axisX*sindeg)*PtY;
		resultZ+= (cosdeg + (1-cosdeg)*axisZ*axisZ)*PtZ;

		Result[0] = resultX;
		Result[1] = resultY;
		Result[2] = resultZ;

		return Result;
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

	/* Find vector angle that bisects two vectors
	 */
	public static double getBisectingAngle(double[] A,double[] B) {
		// convert vectors to unit vectors and average them
		
		
		
		return 1;
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
		double[] Result = new double[3];
		double mag = vectorMagnitude(unNormVector);

		if (mag == 0){
			for(int i=0;i<3;i++){
				Result[i] = unNormVector[i];
			}
		}
		else{
			for(int i=0;i<3;i++){
				Result[i] = unNormVector[i]/mag;
			}

		}

		return Result;
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



	/* Coefficients of a plane using 3 point:
	 * We find the coefficients for the equation Ax + By + Cz + D = 0
	 * We find the equation of the plane using (P-P0).N = 0 (P0 is a point on the plane and N is a unit normal vector
	 * found by taking cross product.
	 */

	public static double[] genplaneCoeffs(double[] A, double[] B, double[] C){
		// vector CA = A - C
		// vector CB = B - C
		// cross product  = CA x CB

		double[] Result = new double[4]; // Coefficients A,B,C,D in Ax + By + Cz + D = 0
		double[] vecCA = new double[3];
		double[] vecCB = new double[3];
		double[] unNormCrossProd = new double[3];
		double[] NormCrossProd = new double[3];


		for(int i=0; i<3;i++){
			vecCA[i] = A[i]  - C[i]; // Vector points from 
			vecCB[i] = B[i] -  C[i]; // Vector points from
		}	

		// Cross-product of tempVec1 X tempVec2	
		unNormCrossProd = doVectorProd(vecCA,vecCB);

		// Normalize:
		NormCrossProd   = normVector(unNormCrossProd);

		// Coefficients: A, B, C, D;
		Result[0] = NormCrossProd[0]; 
		Result[1] = NormCrossProd[1];
		Result[2] = NormCrossProd[2];
		Result[3] = -MyMathRepository.doDotProd(C, NormCrossProd);

		return Result;

	}





	public static boolean isPtOutsideNoFlyZone(double[] pt,double[] topPlaneCoef,double[] bottomPlaneCoef,double[] leftPlaneCoef, double[] rightPlaneCoef, double[] nearPlaneCoef){		
		boolean Result = true;
		double a,b,c,d,e;
		a=evalPlaneEqu(pt, topPlaneCoef);
		b=evalPlaneEqu(pt, bottomPlaneCoef);
		c=evalPlaneEqu(pt, leftPlaneCoef);
		d=evalPlaneEqu(pt, rightPlaneCoef);
		e=evalPlaneEqu(pt, nearPlaneCoef);

		if(a<0 && b<0 && c<0 && d<0 && e<0){ // So the point has to fail all planes in order to be INSIDE which means definitively it is outside.
			Result = false;
		}
		return Result;
	}



	public static double evalPlaneEqu(double[] pt, double[] planeCoeffs){
		double Result, temp=0;

		for (int i = 0; i<3; i++){
			temp = temp + pt[i]*planeCoeffs[i];
		}
		Result  = temp + planeCoeffs[3];

		return Result;
	}



	public static boolean allFalse(boolean[] a){
		boolean Result;
		boolean currentBooleanState = true;
		int i = 0;
		int lengthArray = a.length;
		while(i< lengthArray && currentBooleanState){
			if (a[i]){
				currentBooleanState = false;
			}
			i++;
		}

		Result= currentBooleanState;

		return Result;
	}

	public static boolean allTrue(boolean[] a){
		boolean Result;
		boolean currentBooleanState = true;
		int i = 0;
		while(i<a.length && currentBooleanState){
			if (!a[i]){
				currentBooleanState = false;
			}
			i++;
		}

		Result= currentBooleanState;

		return Result;
	}



	public static int countFalse(boolean[] a){
		int Result;
		int tempSum = 0;
		int lengthArray = a.length;
		for(int i=0; i<lengthArray; i++){
			if (!a[i]){
				tempSum = tempSum + 1;
			}

		}

		Result = tempSum;
		return Result;

	}

	public static int countTrue(boolean[] a){
		int Result;
		int tempSum = 0;
		for(int i=0; i<a.length; i++){
			if (a[i]){
				tempSum = tempSum + 1;
			}

		}

		Result = tempSum;
		return Result;

	}

	public static double[] scale3DPt(double[] pt,double scaleFactor){
		double[] Result = new double[3];
		for (int i=0;i<3;i++){
			Result[i] = pt[i]*scaleFactor;
		}
		return Result;

	}

	// A-B
	public static double[] Vec3DSubtract(double[] A, double[] B){
		double[] Result = new double[3];

		for(int i=0;i<3;i++){
			Result[i]= A[i]-B[i];
		}

		return Result;
	}

	public static double euclid3Ddist(double[] A, double[] B){
		double Result;
		double temp= 0;
		for(int i=0;i<3;i++){
			temp = temp + (A[i]-B[i])*(A[i]-B[i]);
		}
		Result = Math.sqrt(temp);
		return Result;
	}


	public static double euclid2Ddist(double[] A, double[] B){
		double Result;
		double temp= 0;
		for(int i=0;i<2;i++){
			temp = temp + (A[i]-B[i])*(A[i]-B[i]);
		}
		Result = Math.sqrt(temp);
		return Result;
	}

	// This function returns numb elements from src randomly chosen:
		public static int[] randSelection(int[] src, int numb){
			// Note numb<=numbElements)
			//Random rand = new Random();

			int numbElements = src.length;

			int[] Result      = new int[numb];
			double[] tempRand = new double[numbElements];
			int[] tempRandSortedIndx = new int[numbElements];

			// First generate numbElements random numbers:
			for(int i=0;i<numbElements;i++){
				tempRand[i]=rand.nextDouble();  	
			}

			//Sort from low to high, and return the sorted indices (not the actual numbers)
			tempRandSortedIndx = sortLowToHighIndx(tempRand);

			// Select first numb
			for (int i=0;i<numb;i++){
				Result[i] = src[tempRandSortedIndx[i]];
			}

			return Result;
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


		// Sorts integers from low to high and depending on returnNumbers either returns the sorted numbers or the sorted indices (not the numbers)
		public static int[] sortLowToHighInteger(int[] tempArray, boolean returnNumbers){
			int min; int temp;
			int arrLength = tempArray.length;
			int[] numbers = new int[arrLength];
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
				for(int scan=index+1;scan<arrLength;scan++){
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

			if(returnNumbers)
				return numbers;
			else
				return indicesSort;

		}

		public static int findMaxInteger(int[] inpArr){
			int lengthArr = inpArr.length;
			int maxVal = inpArr[0];
			for(int i = 1;i<lengthArr;i++){
				if(inpArr[i]>maxVal)
					maxVal = inpArr[i];
			}
			return maxVal;
		}


		/* Function: countUniqueElementInteger
		 * It finds the unique elements in 'arr' and returns the number of unique elements  
		 */

		public static int countUniqueElementsInteger(int[] arr){
			int numElements = arr.length;
			int[] uniqueElements = new int[arr.length];
			int counter,uniqueElementCounter;
			int testElement;
			boolean foundRepeat = false;
			int[] finalUniqueElements;

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


			return uniqueElementCounter;

		}// End of function


		/* Function: getUniqueElementsInteger
		 * It finds the unique elements in 'arr' and returns the unique elements. Important: It preserves the order present in arr. For example,
		 * if we have 0 1 2 3 4 5 6 7 0 1 2 then we want to output 0 1 2 3 4 5 6 7 NOT 3 4 5 6 7 0 1 2.
		 */   
		public static int[] getUniqueElementsInteger(int[] arr){
			int numElements = arr.length;
			int[] uniqueElements = new int[arr.length];
			int counter,uniqueElementCounter;
			int testElement;
			boolean foundRepeat = false;
			int[] finalUniqueElements;

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

		}// End of function


		/* Function: Finds out whether the integer array targArr contains the integer src. Returns true if this is the  
		 * case.
		 */
		public static boolean match(int src, int[] targArr){
			int arrayLength = targArr.length;
			int counter = 0;	
			boolean foundMatch = false;
			while(counter<arrayLength && !foundMatch){
				if(targArr[counter] == src)
					foundMatch = true;
				counter++;	
			}
			return foundMatch;	
		}





		/* Function: removeElements. It generates an array containing the elements in src except for the elements indexed by
		 * indxToRm.
		 */
		public static int[] removeElementsByIndx(int[] src, int[] indxToRm){
			// Set the length of the new array:
			int lengthOfNewArray = (src.length) - (indxToRm.length);
			int[] newArr = new int[lengthOfNewArray];
			int counter;
			boolean rmvIndx;

			counter=0;
			for (int i=0; i<src.length;i++){
				rmvIndx = match(i,indxToRm);
				if(!rmvIndx){
					newArr[counter] = src[i];
					counter++;
				}
			}

			return newArr;
		}


		// Calculates how many of the elements in the array 'src' match any of the integers contained in targArr[].
		public static int numMatches(int[] src, int[] targArr){
			boolean foundMatch;
			int numMatches = 0;
			for (int i=0; i<src.length;i++){
				foundMatch = match(src[i],targArr);
				if(foundMatch){
					numMatches++;
				}
			}
			return numMatches;
		}

		//Calculates how many of the integer pts (2d) in the array 'src' match any of the integer pts (2d) contained in targArr[].
		public static int numMatches2dPts(int[][] src, int[][] targArr){
			boolean foundMatch;
			int numMatches = 0;
			for (int i=0; i<src.length;i++){
				foundMatch = match2dPts(src[i],targArr);
				if(foundMatch){
					numMatches++;
				}
			}
			return numMatches;
		}

		/* Function: Finds out whether the array targArr contains the 2D pt src. Returns true if this is the  
		 * case.
		 */
		public static boolean match2dPts(int[] src, int[][] targArr){
			int arrayLength = targArr.length;
			int counter = 0;	
			boolean foundMatch = false;
			while(counter<arrayLength && !foundMatch){
				if(targArr[counter][0] == src[0] && targArr[counter][1] == src[1])
					foundMatch = true;
				counter++;	
			}
			return foundMatch;	
		}




		/* Function: removeElementsByPt. It generates an array containing the elements in src except for the elements contained in ptsToRm.
		 * Note src does not necessarily have to contain those points.
		 */
		public static int[] removeElementsByPt(int[] src, int[] ptsToRm) throws OutOfRangeException{

			int[] tempArr = new int[src.length]; // Initially we make the array as large as possible.
			int[] finalArr;
			int finalLength;
			int counter;
			int numPtsRemoved;
			boolean rmvIndx;

			counter=0;
			numPtsRemoved=0;
			for (int i=0; i<src.length;i++){
				rmvIndx = match(src[i],ptsToRm);
				if(!rmvIndx){
					tempArr[counter] = src[i];
					counter++;
				}
				else{
					numPtsRemoved++;	
				}
			}

			// Resize 
			finalLength = src.length - numPtsRemoved;
			finalArr = new int[finalLength];
			finalArr = resizeArray(tempArr,finalLength);

			return finalArr;

		}


		/* Function: removeElementsByPt. It generates an array containing the elements in src except for the elements contained in ptsToRm.
		 * Note src does not necessarily have to contain those points.
		 */
		public static int[][] removeElementsByPt2D(int[][] src, int[][] ptsToRm){

			int[][] tempArr = new int[src.length][2]; // Initially we make the array as large as possible.
			int[][] finalArr;
			int finalLength;
			int counter;
			int numPtsRemoved;
			boolean rmvIndx;

			counter=0;
			numPtsRemoved=0;
			for (int i=0; i<src.length;i++){
				rmvIndx = match2dPts(src[i],ptsToRm);
				if(!rmvIndx){
					tempArr[counter][0] = src[i][0];
					tempArr[counter][1] = src[i][1];
					counter++;
				}
				else{
					numPtsRemoved++;	
				}
			}

			// Resize 
			finalLength = src.length - numPtsRemoved;
			finalArr = new int[finalLength][2];
			finalArr = resizeArray2D(tempArr,finalLength);

			return finalArr;

		}




		/* Function: findAllperms. It lists all possible permutations of elements in 'arr'. For example if arr = {4,5,6}
		 * then the function would return {{4,5,6},{4,6,5},{5,4,6},{5,6,4},{6,4,5},{6,5,4}}.
		 */	

		public static int[][] findAllPerms(int[] arr){
			int size = arr.length;
			int iterations = factorial(size);
			int count, temp;
			int i,j;
			int[] data = new int[size];
			int[][] result = new int[iterations][size];

			for (i = 0; i < size; i++) {
				data[i] = i;
			}

			for(i=0;i<size;i++){
				result[0][i] = arr[data[i]];
			}

			for (count = 0; count < iterations - 1; count++) {

				i = size - 1;

				while (data[i-1] >= data[i]) 
					i = i-1;

				j = size;

				while (data[j-1] <= data[i-1]) 
					j = j-1;

				temp = data[i-1];
				data[i-1] = data[j-1];
				data[j-1] = temp;

				i++; 
				j = size;

				while (i < j) {
					temp = data[i-1];
					data[i-1] = data[j-1];
					data[j-1] = temp;
					i++;
					j--;
				}


				for(i=0;i<size;i++){
					result[count+1][i] = arr[data[i]];
				}


			}


			return result;
		}


		public static int factorial(int x){
			if(x<=1)
				return 1;
			else
				return x*factorial(x-1);
		}


		public static double[] solveQuadFunc(double A, double B, double C){
			double temp = Math.sqrt(B*B - 4*A*C);
			double Result[] = new double[2];
			Result[0] = (-B - temp)/(2*A);	
			Result[1] = (-B + temp)/(2*A);	
			return Result; 
		}


		/* Function: matchingIndx. It finds the index at which 'src' matches 'targArr'. If there
		 * is no match we return a -1. Note also 'targArr' may contain repeated values and so in these
		 * cases we may have multiple matches. Here we only take one of the matches, we pick the index 
		 * that's most closest to the middle  
		 */
		/*
public static int[] matchingIndx(int src, int[] targArr){
int lengthOfTarg = targArr.length;
int counter = 0;

for(int i=0;i<targArr.length;i++)	
    if(src==targArr[i]){
    	counter++;
    }

}
		 */  

		/* Function: distVecShortestPath:
		 */

		public static int[] distVecShortestPath(int[] pt1,int[] pt2,int inpNumPtsPerSectNoReps){

			int firstPtUDim  = pt1[0];
			int firstPtVDim  = pt1[1];

			int secondPtUDim = pt2[0];
			int secondPtVDim = pt2[1];

			int[] dist = new int[2];
			int absDiffV;

			dist[0] = Math.abs(secondPtUDim - firstPtUDim);
			absDiffV = Math.abs(secondPtVDim - firstPtVDim);

			if(absDiffV>(inpNumPtsPerSectNoReps/2)){
				dist[1] = inpNumPtsPerSectNoReps-absDiffV;	
			}
			else{
				dist[1] = absDiffV;
			}

			return dist;
		}



		/* Function: distanceBetwGridPts. It calculates the distance in both dimensions between pt1 and pt2. The fourth argument goClockWise will
		 * be used when we have a closed surface (more specifically if we are circular (closed) in v direction), indicating in what direction to calculate  the distance.
		 */

		public static int[] distanceBetwGridPts(boolean openSurface,int inpNumPtsPerSectNoReps, int[] pt1,int[] pt2, boolean goClockWise){
			boolean openSurf = openSurface;
			int numPtsPerSectNoReps = inpNumPtsPerSectNoReps;

			int firstPtUDim  = pt1[0];
			int firstPtVDim  = pt1[1];
			int secondPtUDim = pt2[0];
			int secondPtVDim = pt2[1];

			int[] dist = new int[2];
			int tmpDiffV;

			dist[0] = Math.abs(secondPtUDim - firstPtUDim);	
			tmpDiffV = secondPtVDim - firstPtVDim;

			if(openSurf){
				dist[1] = Math.abs(tmpDiffV);		
			}
			else{ // closed surface	
				if(tmpDiffV>0){ 
					if(goClockWise)
						dist[1] = tmpDiffV;
					else
						dist[1] = numPtsPerSectNoReps-tmpDiffV;
				}
				else{
					if(tmpDiffV==0)
						dist[1] = tmpDiffV;
					else{// tmpDiffV<0
						if(goClockWise)
							dist[1] = numPtsPerSectNoReps - Math.abs(tmpDiffV);
						else
							dist[1] = Math.abs(tmpDiffV);
					}

				}
			}

			return dist;	
		}




		public static boolean isShortestVDirCW(int[] pt1,int[] pt2,int inpNumPtsPerSectNoReps){
			boolean dirVClockWise;
			int firstPtVDim  = pt1[1];
			int secondPtVDim = pt2[1];	

			int tmpDiffV = secondPtVDim  - firstPtVDim;
			int diffVDim = Math.abs(tmpDiffV); 
			int halfNumPts = inpNumPtsPerSectNoReps/2;

			if(diffVDim > halfNumPts ){		
				if(firstPtVDim>halfNumPts){ // We go clockwise
					dirVClockWise = true;
				}
				else{
					dirVClockWise = false;

				}
			}
			else{
				if(diffVDim<halfNumPts){
					if(secondPtVDim>=firstPtVDim){
						dirVClockWise = true;
					}
					else{
						dirVClockWise = false;
					}
				}
				else{ //diffVDim==halfNumPts
					// In this case both available paths are equi-distant
					// We do clockwise:
					dirVClockWise = true;
				}

			}


			return dirVClockWise;
		}








		public static int distanceBetwGridPtsInVDir(boolean openSurface,int inpNumPtsPerSectNoReps, int pt1,int pt2, boolean goClockWise){
			boolean openSurf = openSurface;

			int firstPtVDim  = pt1;
			int secondPtVDim = pt2;

			int dist;
			int tmpDiffV;

			tmpDiffV = secondPtVDim - firstPtVDim;

			if(openSurf){
				dist = Math.abs(tmpDiffV);		
			}
			else{ // closed surface	
				if(tmpDiffV>0){ 
					if(goClockWise)
						dist = tmpDiffV;
					else
						dist = inpNumPtsPerSectNoReps-tmpDiffV;
				}
				else{
					if(tmpDiffV==0)
						dist = tmpDiffV;
					else{// tmpDiffV<0
						if(goClockWise)
							dist = inpNumPtsPerSectNoReps - Math.abs(tmpDiffV);
						else
							dist = Math.abs(tmpDiffV);
					}

				}
			}

			return dist;	
		}





		/* Function: diffVector. Find the vector pointing from pt1 to pt2. Note it returns a type double;
		 * Clockwise is defined as positive. Anti-clockwise is negative.
		 */

		public static double[] differenceVector(boolean openSurface,int inpNumPtsPerSectNoReps,int[] pt1, int[] pt2, boolean goClockWise){
			boolean openSurf = openSurface;
			int firstPtUDim  = pt1[0];
			int firstPtVDim  = pt1[1];
			int secondPtUDim = pt2[0];
			int secondPtVDim = pt2[1];
			double[] diffVector = new double[2]; 
			int tmpDiffV;
			diffVector[0] = (double)(secondPtUDim - firstPtUDim);	
			tmpDiffV = secondPtVDim - firstPtVDim; // Integer	

			if(openSurf){
				diffVector[1] = (double)(tmpDiffV);		
			}
			else{ // Closed
				if(tmpDiffV>0){ 
					if(goClockWise)
						diffVector[1] = (double)tmpDiffV;
					else
						diffVector[1] = -1.0*(inpNumPtsPerSectNoReps-tmpDiffV);
				}
				else{ // tmpDiffV<0  or tmpDiffV==0
					if(tmpDiffV==0)
						diffVector[1] = (double)tmpDiffV;			
					else{// tmpDiffV<0
						if(goClockWise)
							diffVector[1] = (double)(inpNumPtsPerSectNoReps - Math.abs(tmpDiffV));
						else
							diffVector[1] = (double)tmpDiffV; // not when we reach here tmpDiffV is already negative (so don't need -1*)
					}
				}

			}//else

			return diffVector;
		}// function



		/* Function: findDistanceBetweenPaths
		 * int[][] path1: first dim indicates which point in the path and the second dimension refers to the U,V dimension.
		 * function finds the shortest 'distance' between the 2 paths. It goes through all pairwise comparisons of the points in
		 * the two paths and finds the smallest value. In calculating a distance between two points we take the larger of the 
		 * two dimensions (u and v). Note also when calculating the distance in the 'v' direction for closed surfaces we take
		 * the shortest path.
		 */
		public static int findDistanceBetweenPaths(boolean openSurface,int inpNumPtsPerSectNoReps, int[][] path1,int[][] path2){
			boolean openSurf = openSurface;

			int pt1UDim,pt1VDim;	
			int pt2UDim,pt2VDim;
			int diffU,diffV;
			int maxDiff;
			int counter;
			int lengthPath1 = path1.length;
			int lengthPath2 = path2.length;

			int[] listDistances = new int[lengthPath1*lengthPath2];
			int shortestDistance;
			int[] sortedDist    = new int[lengthPath1*lengthPath2];

			counter = 0;


			if(!openSurf){
				for(int i=0;i<lengthPath1;i++){
					pt1UDim=path1[i][0];
					pt1VDim=path1[i][1];
					for(int j=0;j<lengthPath2;j++){
						pt2UDim=path2[j][0];
						pt2VDim=path2[j][1];

						diffU = Math.abs(pt1UDim - pt2UDim);
						diffV = Math.abs(pt1VDim - pt2VDim);

						if(diffV>(inpNumPtsPerSectNoReps/2))
							diffV=inpNumPtsPerSectNoReps - diffV;


						if(diffU>=diffV){
							maxDiff	= diffU;
						}
						else{
							maxDiff	= diffV;	
						}

						listDistances[counter] = maxDiff;
						counter++;
					}
				}
			}
			else{
				for(int i=0;i<lengthPath1;i++){
					pt1UDim=path1[i][0];
					pt1VDim=path1[i][1];
					for(int j=0;j<lengthPath2;j++){
						pt2UDim=path2[j][0];
						pt2VDim=path2[j][1];

						diffU = Math.abs(pt1UDim - pt2UDim);
						diffV = Math.abs(pt1VDim - pt2VDim);

						if(diffU>=diffV){
							maxDiff	= diffU;
						}
						else{
							maxDiff	= diffV;	
						}

						listDistances[counter] = maxDiff;
						counter++;
					}
				}

			}

			// Find the shortest distance:
			sortedDist = sortLowToHighInteger(listDistances, true); // returns sorted numbers. 
			shortestDistance = sortedDist[0];

			return shortestDistance;
		}




		/* Function: fndShortestDistVec
		 * int[][] path1/2: first dim indicates which point in the path and the second dimension refers to the U,V dimension.
		 * For each point in path1 we calculate its distance to all the points in path2 and then store the shortest distance inside
		 * the array shortestDistance[].
		 * In calculating a distance between two points we take the larger of the  two dimensions (u and v). Note also when 
		 * calculating the distance in the 'v' direction for closed surfaces we take the shortest path.
		 */

		public static int[] fndShortestDistVec(boolean openSurface,int inpNumPtsPerSectNoReps, int[][] path1,int[][] path2){
			boolean openSurf = openSurface;

			int pt1UDim,pt1VDim;	
			int pt2UDim,pt2VDim;
			int diffU,diffV;
			int maxDiff;

			int lengthPath1 = path1.length;
			int lengthPath2 = path2.length;

			int[] listDistances;
			int[] sortedDist     = new int[lengthPath2];

			int[] shortestDistance = new int[lengthPath1];

			if(!openSurf){

				for(int i=0;i<lengthPath1;i++){

					pt1UDim = path1[i][0];
					pt1VDim = path1[i][1];

					listDistances = new int[lengthPath2];

					for(int j=0;j<lengthPath2;j++){
						pt2UDim=path2[j][0];
						pt2VDim=path2[j][1];

						diffU = Math.abs(pt1UDim - pt2UDim);
						diffV = Math.abs(pt1VDim - pt2VDim);

						if(diffV>(inpNumPtsPerSectNoReps/2))
							diffV=inpNumPtsPerSectNoReps - diffV;


						if(diffU>=diffV){
							maxDiff	= diffU;
						}
						else{
							maxDiff	= diffV;	
						}

						listDistances[j] = maxDiff;

					}

					sortedDist = sortLowToHighInteger(listDistances, true); // returns sorted numbers. 
					shortestDistance[i] = sortedDist[0];
				}

			}
			else{
				for(int i=0;i<lengthPath1;i++){
					pt1UDim=path1[i][0];
					pt1VDim=path1[i][1];

					listDistances = new int[lengthPath2];

					for(int j=0;j<lengthPath2;j++){
						pt2UDim=path2[j][0];
						pt2VDim=path2[j][1];

						diffU = Math.abs(pt1UDim - pt2UDim);
						diffV = Math.abs(pt1VDim - pt2VDim);

						if(diffU>=diffV){
							maxDiff	= diffU;
						}
						else{
							maxDiff	= diffV;	
						}

						listDistances[j] = maxDiff;
					}

					// Find the shortest distance:
					sortedDist = sortLowToHighInteger(listDistances, true); // returns sorted numbers. 
					shortestDistance[i] = sortedDist[0];	

				}

			}

			return shortestDistance;
		}


















		/* Function: resizeArray
		 * Takes the oldArray and copies the first 'desiredLength' of its elements into a new array 'newArray'.
		 * Assumes the oldArray has at least desiredLength elements.
		 */
		public static int[] resizeArray(int[] oldArray,int desiredLength) throws OutOfRangeException{
			if(oldArray.length<desiredLength)
				throw new OutOfRangeException("In function resizeArray oldArray.length<desiredLength");

			int[] newArray = new int[desiredLength];
			for(int k=0; k<desiredLength; k++){
				newArray[k]= oldArray[k]; 
			}
			return newArray;	
		}


		public static int[][] resizeArray2D(int[][] oldArray,int desiredLength){
			int[][] newArray = new int[desiredLength][2];
			for(int k=0; k<desiredLength; k++){
				newArray[k][0]= oldArray[k][0]; 
				newArray[k][1]= oldArray[k][1]; 
			}
			return newArray;	
		}


		public static boolean doesLineSegCutTriangle(double[] triVertex1, double[] triVertex2, double[] triVertex3,double[] linePt1,double[] linePt2){

			double[] d = new double[3];
			double[] V3minusV1 = new double[3];
			double[] dCrossV3minusV1 = new double[3];
			double[] Pt1minusV1  = new double[3];
			double[] v2minusV1  = new double[3];
			double[] Pt1minusV1Crossv2minusV1 = new double[3];

			double multip;
			double tmp;
			double t,u,v;

			for(int i=0;i<3;i++){
				d[i] = linePt2[i] - linePt1[i]; 
				V3minusV1[i]  = triVertex3[i] - triVertex1[i];
				//Pt1minusV1[i] = linePt1[i] - triVertex1[i];
				v2minusV1[i]  = triVertex2[i] - triVertex1[i];
			}

			// Cross product: d x (triVertex3 - triVertex1)
			dCrossV3minusV1 = doVectorProd(d,V3minusV1);

			//Common multiplier:
			tmp = doDotProd(dCrossV3minusV1,v2minusV1);
			if(tmp>-epsilon && tmp <epsilon){
				return false;
			}

			multip = 1/tmp;

			for(int i=0;i<3;i++){
				Pt1minusV1[i] = linePt1[i] - triVertex1[i];
			}

			u  = multip*doDotProd(dCrossV3minusV1,Pt1minusV1);
			if(u<0.0 || u>1.0)
				return false;


			// cross product: Pt1minusV1 x v2minusV1
			Pt1minusV1Crossv2minusV1 = doVectorProd(Pt1minusV1,v2minusV1);


			v = multip*doDotProd(Pt1minusV1Crossv2minusV1,d);
			if(v<0.0 || (u+v) >1.0)
				return false;


			t = multip*doDotProd(Pt1minusV1Crossv2minusV1,V3minusV1);	
			if(t<0.0 || t>1.0)
				return false;


			return true;
		}



		// Return true if it's possible to find intersection points, false otherwise.
		// It places the values inside interSectiondouble, not arrays are passed by reference.

		public static boolean find2Dcircle_circleIntersection(double[] interSectiondouble, double[] centerA, double radiusA, double[] centerB, double radiusB){
			double d,a,h,radiusASquared;
			double centerADim1, centerADim2, centerBDim1, centerBDim2;
			double oneOverD;
			double tmpScaleFactor;
			double tmpPtDim1,tmpPtDim2;
			double tempDim1,tempDim2;

			centerADim1 = centerA[0];
			centerADim2 = centerA[1];

			centerBDim1 = centerB[0];
			centerBDim2 = centerB[1];

			// Distance between centers:
			d = euclid2Ddist(centerA,centerB);

			if( d>(radiusA+radiusB) ){
				return false;
			}
			if( d<Math.abs(radiusA-radiusB)){
				return false;
			}
			if(d == 0 && radiusA==radiusB){
				return false;
			}

			radiusASquared = radiusA*radiusA;

			a = (radiusASquared - radiusB*radiusB + d*d)/ (2*d);

			h = Math.sqrt(radiusASquared - a*a);

			oneOverD = 1/d;
			tmpPtDim1 = centerADim1 + oneOverD*a*(centerBDim1 - centerADim1);
			tmpPtDim2 = centerADim2 + oneOverD*a*(centerBDim2 - centerADim2);

			tmpScaleFactor = oneOverD*h;
			tempDim1 = tmpScaleFactor*(centerBDim2-centerADim2);
			tempDim2 = tmpScaleFactor*(centerBDim1-centerADim1);

			interSectiondouble[0] = tmpPtDim1 + tempDim1;
			interSectiondouble[1] = tmpPtDim2 - tempDim2;

			interSectiondouble[2] = tmpPtDim1 - tempDim1;
			interSectiondouble[3] = tmpPtDim2 + tempDim2;

			return true;
		}


		/*
    public static void main(String[] args){
    	double[] result = new double[100];
    	for(int i=0;i<100;i++){
    		result[i] = randDouble(-1.0,-0.5);

    	System.out.println(result[i]);
    	}
    }   
		 */
}
