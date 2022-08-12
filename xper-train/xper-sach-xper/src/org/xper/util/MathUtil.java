package org.xper.util;

public class MathUtil {
	/**
	 * 
	 * @param x sample
	 * @param m mean
	 * @param s standard deviation
	 * @return
	 */
	public static double normal(double x, double m, double s) {
		double e;
		e = (x - m) / s;
		return (Math.exp(-e * e / 2.0) / Math.sqrt(2.0 * Math.PI * s * s));
	}
	
	public static double rand (double b, double e) {
		return Math.random() * (e - b) + b;
	}
}
