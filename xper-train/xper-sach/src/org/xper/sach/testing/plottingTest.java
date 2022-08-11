package org.xper.sach.testing;

import java.awt.Color;

import javax.swing.JFrame;

import org.math.plot.Plot2DPanel;
import org.xper.sach.util.SachMathUtil;

public class plottingTest {


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

		// category and avg response
		double[] cats = {0,1,2,3,4,5,6,7};
		double[] resps = {10, 20, 5, 0, 15, 30, 10, 25};
//		double[][] XY = {{0,10},{1,20},{2,5},{3,0},{4,15},{5,30},{6,10},{7,25}};
		double[][] XY = {{0.5,10},{1.5,20},{2.5,5},{3.5,0},{4.5,15},{5.5,30},{6.5,10},{7.5,25}};
		double[] dX = {1,1,1,1,1,1,1,1};
//		double[][] XY = {{0,10/2},{1,20/2},{2,5/2},{3,0/2},{4,15/2},{5,30/2},{6,10/2},{7,25/2}};
//		double[][] dXdY = {{1,10},{1,20},{1,5},{1,0},{1,15},{1,30},{1,10},{1,25}};

		// create your PlotPanel (you can use it as a JPanel)
		Plot2DPanel plot1 = new Plot2DPanel();

		// add a line plot to the PlotPanel
//		plot1.addHistogramPlot("hist", z, 30);
		plot1.addHistogramPlot("bar", XY, dX);
		plot1.setAxisLabel(0, "category");
		plot1.setAxisLabel(1, "response");
		plot1.removePlotToolBar();
		
//		plot1.addBarPlot("category preference", cats, resps);
//		plot1.addStaircasePlot("stair", cats, resps);
//		plot1.addLinePlot("line", cats, resps);
		
		// put the PlotPanel in a JFrame, as a JPanel
		JFrame frame = new JFrame("a plot panel");
		frame.setSize(400, 300);
		frame.setContentPane(plot1);
		frame.setVisible(true);

		
	}	



}

