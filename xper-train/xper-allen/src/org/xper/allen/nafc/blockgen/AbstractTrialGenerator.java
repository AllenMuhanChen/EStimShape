package org.xper.allen.nafc.blockgen;



import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

import org.xper.drawing.Coordinates2D;

public abstract class AbstractTrialGenerator {
	
	protected static int[] frequencyToNumTrials(double[] typesFrequencies, int numTrials) {
		int[] typesNumTrials = new int[typesFrequencies.length];
		for(int i=0; i<typesFrequencies.length; i++) {
			typesNumTrials[i] = (int) Math.round((double) numTrials * typesFrequencies[i]);
		}
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total Round(numTrials .* Frequencies) should = numTrials");
		}
		return typesNumTrials;
	}
	
	/**
	 * generic method for returning a list of trials<K> 
	 * @param <K>
	 * @param numTrials: totla number of trials in block being generated. Used to double check input is correct
	 * @param types: array of types <K>
	 * @param typesNumTrials: number of trials for each type
	 * @return
	 */
	protected <K> List<K> populateTrials(int numTrials, K[] types, int[] typesNumTrials) {
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total typesNumTrials should equal total numTrials");
		}
		List<K> trialList = new LinkedList<>();
		int numTypes = types.length;
		for(int i=0; i<numTypes; i++) {
			for (int j=0; j<typesNumTrials[i]; j++) {
				trialList.add(types[i]);
			}
		}
		return trialList;
	}

	
	/**
	 * populating using frequency. 
	 * @param <K>
	 * @param numTrials
	 * @param types
	 * @param typesFrequency
	 * @return
	 */
	protected <K> List<K> populateTrials(int numTrials, K[] types, double[] typesFrequency) {
		int[] typesNumTrials = new int[types.length];
		for(int i=0; i<types.length; i++) {
			typesNumTrials[i] = (int) Math.round(typesFrequency[i]* (double) numTrials);
		}
		if(IntStream.of(typesNumTrials).sum()!= numTrials) {
			throw new IllegalArgumentException("Total number of trials rounded from frequencies does not equal correct total num of trials");
		}
		
		List<K> trialList = new LinkedList<>();
		int numTypes = types.length;
		for(int i=0; i<numTypes; i++) {
			for (int j=0; j<typesNumTrials[i]; j++) {
				trialList.add(types[i]);
			}
		}
		return trialList;
	}
	

	

	



}
