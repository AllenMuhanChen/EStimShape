package org.xper.allen.app.nafc;

import org.xper.allen.nafc.vo.NoiseType;

public abstract class TrialGenerator {
	public static Integer[] stringToIntegerArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		Integer[] intArr = new Integer[length];
		for(int i=0; i<length; i++) {
			intArr[i] = Integer.parseInt(strArr[i]);
		}
		
		return intArr;
	}

	public static int[] stringToIntArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		int[] intArr = new int[length];
		for(int i=0; i<length; i++) {
			intArr[i] = Integer.parseInt(strArr[i]);
		}
		return intArr;
	}

	public static double[] stringToDoubleArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		double[] doubleArr = new double[length];
		for(int i=0; i<length; i++) {
			doubleArr[i] = Double.parseDouble(strArr[i]);
		}
		return doubleArr;
	}

	public static NoiseType[] stringToNoiseTypeArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		NoiseType[] noiseTypeArr = new NoiseType[length];
		for(int i=0; i<length; i++) {
			noiseTypeArr[i] = NoiseType.valueOf(strArr[i]);
		}
		return noiseTypeArr;
	}

	/**
	 * "(0.5,1),(0.25,0.5),(0.75,1)" --> double[3][2] 
	 * 								 --> [0.5][1]
	 * 									 [0.25][0.5]
	 * 									 [0.75][1]
	 * @param string
	 * @return
	 */
	public static double[][] stringToTupleArray(String string) {
		String[] strArr = string.split("\\),");

		int length = strArr.length;
		double[][] noiseTypeArr = new double[length][2];
		for(int i=0; i<length; i++) {
			String removedParenthesis = strArr[i].replaceAll("\\(", "").replaceAll("\\)", "");

			String[] split = removedParenthesis.split(",");
			noiseTypeArr[i][0] = Double.parseDouble(split[0]);
			noiseTypeArr[i][1] = Double.parseDouble(split[1]);
		}
		return noiseTypeArr;
	}
}
