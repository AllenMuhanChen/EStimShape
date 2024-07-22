package org.xper.allen.nafc.experiment.juice;

import java.sql.Timestamp;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.drawing.Context;
import org.xper.juice.Juice;


public class NAFCJuiceController implements ChoiceEventListener {

	@Dependency
	Juice juice;

	@Dependency
	int choiceCorrectMultiplier = 1;

	@Dependency
	double choiceCorrectMultiplierChance = 0;

	public Juice getJuice() {
		return juice;
	}

	public void setJuice(Juice juice) {
		this.juice = juice;
	}


	@Override
	public void choiceSelectionCorrect(long timestamp, int[] rewardList, Context context) {
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString());
		juice.deliver();
		for (int i = 0; i< choiceCorrectMultiplier-1; i++){
			if (Math.random() < choiceCorrectMultiplierChance){
				System.out.println("Multiplier Juice delivered @ " + new Timestamp(timestamp/1000).toString());
				juice.deliver();
			}
		}

	}


	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString());
		juice.deliver();
		for (int i = 0; i< choiceCorrectMultiplier-1; i++){
			if (Math.random() < choiceCorrectMultiplierChance){
				System.out.println("Multiplier Juice delivered @ " + new Timestamp(timestamp/1000).toString());
				juice.deliver();
			}
		}
	}

	@Override
	public void sampleOn(long timestamp, NAFCTrialContext context) {


	}

	@Override
	public void sampleOff(long timestamp) {
		// TODO Auto-generated method stub

	}

	@Override
	public void choicesOn(long timestamp, NAFCTrialContext context) {
		// TODO Auto-generated method stub

	}

	@Override
	public void choicesOff(long timestamp) {
		// TODO Auto-generated method stub

	}

	@Override
	public void choiceSelectionEyeFail(long timestamp) {
		// TODO Auto-generated method stub

	}
/*
	@Override
	public void choiceSelectionEyeBreak(long timestamp) {
		// TODO Auto-generated method stub

	}
*/
	@Override
	public void choiceSelectionSuccess(long timestamp, int choice) {
		// TODO Auto-generated method stub

	}


	@Override
	public void choiceSelectionNull(long timestamp) {
		// TODO Auto-generated method stub

	}


	@Override
	public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {
		// TODO Auto-generated method stub

	}

	@Override
	public void sampleEyeInHoldFail(long timestamp) {
		// TODO Auto-generated method stub

	}

	public int getChoiceCorrectMultiplier() {
		return choiceCorrectMultiplier;
	}

	public void setChoiceCorrectMultiplier(int choiceCorrectMultiplier) {
		this.choiceCorrectMultiplier = choiceCorrectMultiplier;
	}

	public double getChoiceCorrectMultiplierChance() {
		return choiceCorrectMultiplierChance;
	}

	public void setChoiceCorrectMultiplierChance(double choiceCorrectMultiplierChance) {
		this.choiceCorrectMultiplierChance = choiceCorrectMultiplierChance;
	}
}