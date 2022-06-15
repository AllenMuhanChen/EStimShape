package org.xper.allen.nafc.blockgen;

public class NoiseChances {
	public double[][] noiseChances;
	public double[] noiseChancesProportions;

	public NoiseChances(double[][] noiseChances, double[] noiseChancesProportions) {
		this.noiseChances = noiseChances;
		this.noiseChancesProportions = noiseChancesProportions;
	}
}