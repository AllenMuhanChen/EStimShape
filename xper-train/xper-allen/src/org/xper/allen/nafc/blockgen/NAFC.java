package org.xper.allen.nafc.blockgen;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class NAFC<Type> {

	protected Type sample;
	protected Type match;
	protected List<Type> allDistractors = new LinkedList<Type>();

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

    protected void addToAllDistractors(Type distractor) {
        if(!allDistractors.contains(distractor))
            allDistractors.add(distractor);
    }

	public List<Type> getAllDistractors() {
		return Collections.unmodifiableList(allDistractors);
	}
}