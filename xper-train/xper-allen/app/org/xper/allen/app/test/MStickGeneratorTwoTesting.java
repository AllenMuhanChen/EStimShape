package org.xper.allen.app.test;

import org.xper.allen.app.nafc.NoisyMStickPngRandTrialGenerator;
public class MStickGeneratorTwoTesting {
	public static void main(String[] args) {
		System.out.println(NoisyMStickPngRandTrialGenerator.stringToLims("(1,2),(5,10)")[1][1]);
	}
}
