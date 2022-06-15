package org.xper.allen.nafc.blockgen;

public class ChoiceDistance {
	private double choiceDistanceLowerLim;
	private double choiceDistanceUpperLim;

	public ChoiceDistance(double choiceDistanceLowerLim, double choiceDistanceUpperLim) {
		this.choiceDistanceLowerLim = choiceDistanceLowerLim;
		this.choiceDistanceUpperLim = choiceDistanceUpperLim;
	}

	public double getChoiceDistanceLowerLim() {
		return choiceDistanceLowerLim;
	}

	public void setChoiceDistanceLowerLim(double choiceDistanceLowerLim) {
		this.choiceDistanceLowerLim = choiceDistanceLowerLim;
	}

	public double getChoiceDistanceUpperLim() {
		return choiceDistanceUpperLim;
	}

	public void setChoiceDistanceUpperLim(double choiceDistanceUpperLim) {
		this.choiceDistanceUpperLim = choiceDistanceUpperLim;
	}
}