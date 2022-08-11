package org.xper.sach.testing;

import java.util.Arrays;

//import org.xper.drawing.Window;
import org.xper.sach.util.SachMathUtil;

public class blah4 {

	//protected static Window window;
	
	
	public static void main(String[] args) {
		
		//window.create();
		
//		int[][] aa = {{0,2},{0,4},{1,6},{1,8},{1,10},{1,12},{0,14},{0,16}};
//		System.out.println(Arrays.deepToString(aa));
//		
//		int p = 0;
//		int[][] bb = SachMathUtil.mergeArrays(Arrays.copyOfRange(aa,0,p+1),Arrays.copyOfRange(aa,p,aa.length));//,Arrays.copyOfRange(aa,5,7));
//		System.out.println(Arrays.deepToString(bb));
//
//		
//		int[] c = new int[4];
//		System.out.println(Arrays.toString(c));
		
//		// find b in bb:
//		int[] b = {1,10};
//		System.out.println(Arrays.toString(b));
////		int idx = -1;
////		// search matrix for {1,8}
////		for (int n=0;n<aa.length;n++) {
////			if (aa[n][0] == b[0] & aa[n][1] == b[1]) {
////				idx = n;
////				break;
////			}			
////		}
//		
//		int idx = SachMathUtil.searchMtxIntArr(aa,b);
//		//int b = Arrays.binarySearch(aa,new int[]{1,10});
//		
//		System.out.println(idx);
		
//		int[] a = {1, 2, 1, 1, 5, 2, 3, 3, 5, 3, 1, 2, 2};sq
//		System.out.println(Arrays.toString(a));
//		
//		int[] b = SachMathUtil.findAllValues(a, 2);
//		System.out.println(Arrays.toString(b));
		
		
		// a + m * (1 - a)
//		double[] thetas = {0,45,90,135,180,225,270,315,360};
//		System.out.println(Arrays.toString(thetas));
//		for (double theta : thetas) {
//			System.out.print(mySin(theta) + " ");
//		}
//		for (double theta : thetas) {
//			System.out.print(Math.sin(theta*Math.PI/180) + " ");
//		}
//		System.out.println();
//		for (double theta : thetas) {
//			System.out.print(Math.cos(theta*Math.PI/180) + " ");
//		}
		
		//double ans = Math.sqrt(2) + Math.sin((theta+90)*Math.PI/180)*(1-Math.sqrt(2));
		//System.out.println(ans);
		
//		double ori = 225;
//		
//		double[] oris = {270,180,90};
//		System.out.println("oris:   " + Arrays.toString(oris));
//
//		double[] out = findFlankingOris(ori,Arrays.copyOf(oris,oris.length));
//		
//		int idx = SachMathUtil.findFirst(oris, out[1]);
//
//		System.out.println("sorted: " + Arrays.toString(oris));
//		System.out.println("idx:  " + out[0]);
//		System.out.println("low:  " + out[1]);
//		System.out.println("ori:  " + ori);
//		System.out.println("high: " + out[2]);
//		System.out.println("idx:  " + idx);

		for (int n=0;n<20;n++) {
			System.out.print(n%8 + " ");
		}
	}
	
	static double mySin(double theta) {
		double rad = (theta)*Math.PI/180;
		
		double lower = 1;
		double upper = Math.sqrt(2);
		
		
		return Math.abs(Math.sin(rad))*(upper-lower)+lower;// + Math.sqrt(2); 
	}
	
	static double[] findFlankingOris(double ori,double[] oris) {
		Arrays.sort(oris);

		int oriIdx = -1;
//		while (oriIdx < oris.length-1 & ori > oris[oriIdx]) oriIdx++;
//		
//		double oriA = oris[(oriIdx==oris.length) ? 0 : oriIdx];
//		double oriB = oris[(oriIdx==0) ? oris.length-1 : oriIdx-1];

		double high = -1, low = -1;
//		for (int n = 0; n < oris.length; n++) {
//			if (ori > oris[n]) {
//				oriB = oris[n];
//			}
//		}
		for (int n = 0; n < oris.length; n++) {
			if (ori < oris[n]) { 
				//oriA = oris[n];
				oriIdx = n;
				break;
			}
		}

		//if (oriA==-1) oriA = oris[0];
		//if (oriB==-1) oriB = oris[oris.length-1];
//		
//		if (oriIdx == -1) oriIdx = 0;
		high = oris[(oriIdx==-1) ? ++oriIdx : oriIdx];
		low = oris[(oriIdx==0)  ? oris.length-1 : oriIdx-1];
		
		return new double[]{oriIdx,low,high};
	}

}
