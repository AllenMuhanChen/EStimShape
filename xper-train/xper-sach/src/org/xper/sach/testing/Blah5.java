package org.xper.sach.testing;

//import java.util.ArrayList;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;
//import org.apache.commons.math3.stat.descriptive.moment.*;

import org.xper.sach.util.BiasRandom;
import org.xper.sach.util.MyMathRepository;
import org.xper.sach.util.SachMapUtil;
import org.xper.sach.util.SachMathUtil;
import org.xper.sach.util.SachIOUtil;

//import javax.media.jai.*;

public class Blah5 {


	public static void main(String[] args) {		
				
//		int numRows = 10;
//		int numCols = 2;
//		double[][] in = new double[numRows][numCols];
//		for(int n=0;n<numRows;n++) {
//			in[n] = SachMathUtil.randRange(10d,0d,numCols);
//		}
//		System.out.println("in=" + Arrays.deepToString(in));
//		
//		System.out.println("max x=" + SachMathUtil.max(0, in));
//		System.out.println("max y=" + SachMathUtil.max(1, in));
//
//		
//		List<Double[]> d = new ArrayList<Double[]>();
//		System.out.println(d.size());
//		d.add(new Double[]{3.14d,1.28d});
//		System.out.println(d.size());

//		double[] p;
//		double[][] polygon1 = new double[][]{{-2.5, -3.5}, {-3.5, -3.5}, {-3.5, -4.5}, {-2.5, -4.5}};
//		
////		System.out.println("x max="+SachMathUtil.max(0,polygon1));
////		System.out.println("x min="+SachMathUtil.min(0,polygon1));
////		System.out.println("y max="+SachMathUtil.max(1,polygon1));
////		System.out.println("y min="+SachMathUtil.min(1,polygon1));
//		
//		System.out.println(Arrays.deepToString(Arrays.copyOfRange(polygon1, 3, 4)));
		
//		p = new double[]{20, 20};
//		System.out.print(SachMathUtil.isInPolygon(polygon1, p));
//		System.out.println("  pnpoly: "+pnpoly(polygon1, p));
//
//		

//		boolean b;
//		b = SachMathUtil.randBoolean();
//		
//		for (int i=0;i<10;i++) {
//			System.out.print(SachMathUtil.randBoolean() + " ");
//		}
		
		
//		double[][] poly = new double[][]{{0,0}, {10,0}, {10,10}, {0,10}, {9,9}};
//		
//		System.out.println(SachMathUtil.doAnySegmentsCross(poly));
//		
//		//System.out.println(SachMathUtil.doIntersect(poly[0], poly[1], poly[3], poly[4]));
//
//		for (int n=0;n<10;n++) {
//			System.out.print(SachMathUtil.randRange(4, 0) + " ");
//		}
		
//		List<Integer> ll = new ArrayList<Integer>();
//		ll.add(0);
//		ll.add(1);
//		ll.add(2);
//		ll.add(3);
//		ll.add(4);
//		ll.add(5);
//		
//		System.out.println(ll.toString());
//		
//		ll.add(3, 10);
//		
//		System.out.println(ll.toString());
//		
//		ll.add(7, 10);
//		
//		System.out.println(ll.toString());
//		
//		for (int n=50;n<5;n++) {
//			System.out.print("p ");
//		} 
		
//		double[] x = new double[]{-1.0,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1.0};
//		double[] y = new double[x.length];
//		
//		y = SachMathUtil.pow_nonImag(x,1/3d);
//		
//		System.out.println(Arrays.toString(x));
//		System.out.println(Arrays.toString(y));
//		
//		x = new double[]{0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0};
//		y = SachMathUtil.cubeRootFcn(x, 360);
//		System.out.println(Arrays.toString(y));

//		double[] o = new double[1080/60*2+1];
//		for (int n=0;n<o.length;n++) {
//			o[n] = -1080 + n*60;
//		}
//		System.out.println(Arrays.toString(o));
//		
//		double[] p = new double[o.length];
//		for (int n=0;n<p.length;n++) {
////			p[n] = ((o[n] % 360) + 360) % 360;
//			p[n] = SachMathUtil.normAngle(o[n]);
//		}
//		System.out.println(Arrays.toString(p));
//		
//		int s = 0;
//		int[] t = new int[10];
//		for (int n=0;n<10;n++) {
//			t[n] = s += n;
//			System.out.println("s=" + s);
//		}
//		System.out.println(Arrays.toString(t));
		
		
		
//		double[] morphProps = new double[]{ 0.15,0.15,0.15,0.15,0.15,0.10,0.15 }; 
//		double[] morphLims = new double[morphProps.length];
//		double runningTotal = 0;
//		for (int n=0;n<morphLims.length;n++) {
//			morphLims[n] = runningTotal += morphProps[n];
//		}
//		System.out.println(Arrays.toString(morphProps));
//		System.out.println(Arrays.toString(morphLims));
//		
//		BiasRandom br = new BiasRandom(morphProps);
		
		// bounded gaussian
		
//		double[] z = new double[100];
//		
//		for (int n=0;n<100;n++) {
//			z[n] = SachMathUtil.randBoolean(0.1) ? 0 : -1;
//		}
//		
//		System.out.println(Arrays.toString(z));
//		System.out.println(SachMathUtil.mean(z));
		
		
		System.out.println(System.getProperty("user.dir"));
		System.out.println(System.getProperty("user.home"));
		System.out.println(System.getProperty("user.name"));


		
	}
	
	public static double hoch(double basis, int exponent) {
	    if (exponent > 0) {
	        return (basis * hoch(basis, exponent - 1));
	    } else if (exponent < 0) {
	        return (1/hoch(basis, -exponent));
	    } else {
	        return 1;
	    }
	}
	
	
	static boolean pnpoly(double[][] poly,double[] pt) {
		// very terse method for finding if pt lies inside of a polygon
		int numPoly = poly.length;
		int i, j;
		boolean c = false;
		for (i = 0, j = numPoly-1; i < numPoly; j = i++) {
			if (SachMathUtil.onSegment(poly[i],pt,poly[j])) return true;
			if ( ((poly[i][1]>pt[1]) != (poly[j][1]>pt[1])) && (pt[0] < (poly[j][0]-poly[i][0])*(pt[1]-poly[i][1])/(poly[j][1]-poly[i][1])+poly[i][0]) ) {
				c = !c;
				System.out.print(".");
			}
		}
		return c;
	}
	
	

}