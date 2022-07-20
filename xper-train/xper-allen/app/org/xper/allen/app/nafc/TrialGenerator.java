package org.xper.allen.app.nafc;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseType;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

public abstract class TrialGenerator {
	public static List<Integer> stringToIntegers(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		Integer[] intArr = new Integer[length];
		for(int i=0; i<length; i++) {
			intArr[i] = Integer.parseInt(strArr[i]);
		}
		
		return Arrays.asList(intArr);
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

	public static List<Double> stringToDoubles(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		Double[] doubleArr = new Double[length];
		for(int i=0; i<length; i++) {
			doubleArr[i] = Double.parseDouble(strArr[i]);
		}
		return Arrays.asList(doubleArr);
	}

	public static List<NoiseType> stringToNoiseTypes(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		List<NoiseType> noiseTypes = new LinkedList<>();
		for(int i=0; i<length; i++) {
			noiseTypes.add(NoiseType.valueOf(strArr[i]));
		}
		return noiseTypes;
	}

	/**
	 * "(0.5,1),(0.25,0.5),(0.75,1)" --> double[3][2] 
	 * 								 --> [0.5][1]
	 * 									 [0.25][0.5]
	 * 									 [0.75][1]
	 * @param string
	 * @return
	 */
	public static List<Lims> stringToLims(String string) {
		String[] strArr = string.split("\\),");

		int length = strArr.length;
		List<Lims> lims = new LinkedList<>();
		for(int i=0; i<length; i++) {
			String toParse = strArr[i];
			Lims lim = stringToLim(toParse);
			lims.add(lim);
		}
		return lims;
	}

	public static Lims stringToLim(String toParse) {
		String removedParenthesis = toParse.replaceAll("\\(", "").replaceAll("\\)", "");
		String[] split = removedParenthesis.split(",");
		Lims lim = new Lims();
		lim.setLowerLim(Double.parseDouble(split[0]));
		lim.setUpperLim(Double.parseDouble(split[1]));
		return lim;
	}
}
