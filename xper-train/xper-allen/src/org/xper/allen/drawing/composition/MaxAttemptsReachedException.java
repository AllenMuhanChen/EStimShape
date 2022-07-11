package org.xper.allen.drawing.composition;

public class MaxAttemptsReachedException extends RuntimeException {
	public MaxAttemptsReachedException(String step, int nTries) {
		super("Max attempts reached at step " + step + " after " + nTries + " attempts");
	}
}