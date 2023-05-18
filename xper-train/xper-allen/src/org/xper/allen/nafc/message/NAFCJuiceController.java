package org.xper.allen.nafc.message;

import java.sql.Timestamp;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.juice.Juice;


public class NAFCJuiceController implements ChoiceEventListener {

	@Dependency
	Juice juice;

	public Juice getJuice() {
		return juice;
	}

	public void setJuice(Juice juice) {
		this.juice = juice;
	}


	@Override
	public void choiceSelectionCorrect(long timestamp, int[] rewardList) {
		juice.deliver();
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString() + "because animal correctly chose.");

	}


	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {
		juice.deliver();
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString() + "because animal is rewarded by default.");
	}

	@Override
	public void sampleOn(long timestamp, NAFCTrialContext context) {
		// TODO Auto-generated method stub

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


}