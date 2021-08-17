package org.xper.allen.nafc;

import java.sql.Timestamp;

import org.xper.Dependency;
import org.xper.allen.saccade.console.TargetEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
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
	public void choiceSelectionCorrect(long timestamp) {
		juice.deliver();
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString() + "because animal correctly chose.");
		
	}


	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {
		juice.deliver();
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString() + "because animal is correct by default.");
	}

	@Override
	public void sampleOn(long timestamp, TrialContext context) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void sampleOff(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void choicesOn(long timestamp, TrialContext context) {
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

	@Override
	public void choiceSelectionEyeBreak(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void choiceSelectionOne(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void choiceSelectionTwo(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void choiceSelectionNull(long timestamp) {
		// TODO Auto-generated method stub
		
	}


	@Override
	public void choiceSelectionIncorrect(long timestamp) {
		// TODO Auto-generated method stub
		
	}


}
