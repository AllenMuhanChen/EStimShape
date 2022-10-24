package org.xper.allen.nafc.blockgen;

import java.util.List;

import org.xper.drawing.Coordinates2D;

public class NAFCCoordinates {
	private Coordinates2D sampleCoords;
	private Coordinates2D matchCoords;
	private List<Coordinates2D> distractorCoords;

	public NAFCCoordinates() {
	}

	public Coordinates2D getSampleCoords() {
		return sampleCoords;
	}

	public void setSampleCoords(Coordinates2D sampleCoords) {
		this.sampleCoords = sampleCoords;
	}

	public Coordinates2D getMatchCoords() {
		return matchCoords;
	}

	public void setMatchCoords(Coordinates2D matchCoords) {
		this.matchCoords = matchCoords;
	}

	public List<Coordinates2D> getDistractorCoords() {
		return distractorCoords;
	}

	public void setDistractorCoords(List<Coordinates2D> distractorCoords) {
		this.distractorCoords = distractorCoords;
	}
}