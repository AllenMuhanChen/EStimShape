package org.xper.sach.testing;

import javax.swing.JFrame;

import org.math.plot.Plot2DPanel;
import org.xper.sach.util.SachMathUtil;


public class Blah6 {


	public static void main(String[] args) {		

		// testing randUshaped and other ways of created biased random #s
		
		double z0 = 240;
		double[] z = new double[10000];

		for (int n=0;n<z.length;n++) {
//			z[n] = SachMathUtil.randUshaped(0, 360, z0);
			z[n] = SachMathUtil.normAngle(SachMathUtil.randBoundedGauss(360/5, z0+180, z0, z0+360));
		}

//		z = SachMathUtil.randUshaped(0, 360, z0, z.length);
		
//		System.out.println(Arrays.toString(z));


		// create your PlotPanel (you can use it as a JPanel)
		Plot2DPanel plot = new Plot2DPanel();

		// add a line plot to the PlotPanel
		plot.addHistogramPlot("hist", z, 30);

		// put the PlotPanel in a JFrame, as a JPanel
		JFrame frame = new JFrame("a plot panel");
		frame.setSize(400, 300);
		frame.setContentPane(plot);
		frame.setVisible(true);

//		// testing BiasRandom
//									// 0, 1, 2, 3, 4, 5, 6, 7, 8	
//		double[] props = new double[]{ 0, 5,10,15,15,15,15, 0, 0 }; 
//		BiasRandom br = new BiasRandom(props);
//		double[] l = new double[10000];
//		
//		for (int n=0;n<l.length;n++) {		
//			l[n] = br.selectEvent();
//		}
//		
//		//System.out.println(Arrays.toString(l));
//
//		
//		// create your PlotPanel (you can use it as a JPanel)
//		Plot2DPanel plot = new Plot2DPanel();
//
//		// add a line plot to the PlotPanel
//		plot.addHistogramPlot("hist", l, 0.0, 9.0, props.length*2);
//		
//		// put the PlotPanel in a JFrame, as a JPanel
//		JFrame frame = new JFrame("a plot panel");
//		frame.setSize(400, 300);
//		frame.setContentPane(plot);
//		frame.setVisible(true);
		
		
		
//		int[] a = new int[]{6,3,7,8,9,5,3,5,3,2,5,8,5,4,6,4};
//		
//		int[] b = SachMathUtil.unique(a);
//		
//		System.out.println("a=" + Arrays.toString(a));
//		System.out.println("b=" + Arrays.toString(b));
//		
//		
//		double[] c = new double[100];
//		for (int n=0;n<c.length;n++) {
//			c[n] = SachMathUtil.randBoolean(0.5) ? 1d : 0d;
//		}
//		//System.out.println("c=" + Arrays.toString(c));
//
//		// create your PlotPanel (you can use it as a JPanel)
//		Plot2DPanel plot = new Plot2DPanel();
//
//		// add a line plot to the PlotPanel
//		plot.addHistogramPlot("hist",c,0,2,5);
//		
//		// put the PlotPanel in a JFrame, as a JPanel
//		JFrame frame = new JFrame("a plot panel");
//		frame.setSize(400, 300);
//		frame.setContentPane(plot);
//		frame.setVisible(true);
		

		
		
	}	



}

