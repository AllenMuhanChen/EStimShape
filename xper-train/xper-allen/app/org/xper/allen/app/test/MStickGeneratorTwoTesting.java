package org.xper.allen.app.test;

import org.xper.allen.app.nafc.NoisyMStickPngGenerator;
public class MStickGeneratorTwoTesting {
	public static void main(String[] args) {
		System.out.println(NoisyMStickPngGenerator.stringToTupleArray("(1,2),(5,10)")[1][1]);
	}
}
