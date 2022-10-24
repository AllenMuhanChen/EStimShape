package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.nafc.blockgen.NAFC;

public class Psychometric<Type> extends NAFC<Type>{
	private List<Type> psychometricDistractors = new LinkedList<Type>();
	private List<Type> randDistractors = new LinkedList<Type>();;
	
	public Psychometric(Type sample, Type match, List<Type> distractors, List<Type> psychometricDistractors,
			List<Type> randDistractors) {
		super(sample, match, distractors);
		this.psychometricDistractors = psychometricDistractors;
		this.randDistractors = randDistractors;
	}

	public Psychometric() {
	}


	public void addRandDistractor(Type randDistractor) {
		randDistractors.add(randDistractor);
		addToAllDistractors(randDistractor);
	}
	
	public void addPsychometricDistractor(Type psychometricDistractor) {
		psychometricDistractors.add(psychometricDistractor);
		addToAllDistractors(psychometricDistractor);
	}

	public List<Type> getPsychometricDistractors() {
		return psychometricDistractors;
	}

	public void setPsychometricDistractors(List<Type> psychometricDistractors) {
		this.psychometricDistractors = psychometricDistractors;
	}

	public List<Type> getRandDistractors() {
		return randDistractors;
	}

	public void setRandDistractors(List<Type> randDistractors) {
		this.randDistractors = randDistractors;
	}
	
	

}
