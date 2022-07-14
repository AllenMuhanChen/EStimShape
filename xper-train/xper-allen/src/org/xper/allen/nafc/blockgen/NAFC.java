package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

public class NAFC<Type> {
	
	private Type sample;
	private Type match;
	private List<Type> allDistractors = new LinkedList<Type>();
	
	public NAFC(Type sample, Type match, List<Type> distractors) {
		super();
		this.sample = sample;
		this.match = match;
		this.allDistractors = distractors;
	}
	
	public NAFC() {
	}

	public Type getSample() {
		return sample;
	}

	public void setSample(Type sample) {
		this.sample = sample;
	}

	public Type getMatch() {
		return match;
	}

	public void setMatch(Type match) {
		this.match = match;
	}

	public List<Type> getAllDistractors() {
		return allDistractors;
	}

	public void setAllDistractors(List<Type> distractors) {
		this.allDistractors = distractors;
	}
	
	
}
