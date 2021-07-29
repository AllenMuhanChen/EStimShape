package org.xper.allen.twoac;

import java.util.List;


import org.xper.classic.vo.TrialContext;

public class TwoACEventUtil {

	public static void fireSampleOnEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.sampleOn(timestamp, currentContext);
			}
	}	
	
	public static void fireSampleOffEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.sampleOff(timestamp);
			}
	}	
	
	public static void fireChoicesOnEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choicesOn(timestamp, currentContext);
			}
	}	
	
	public static void fireChoicesOffEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choicesOff(timestamp);
			}
	}
	
	public static void fireChoiceSelectionEyeFailEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionEyeFail(timestamp);
			}
	}
	
	public static void fireChoiceSelectionEyeBreakEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionEyeBreak(timestamp);
			}
	}
	
	public static void fireChoiceSelectionOneEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionOne(timestamp);
			}
	}
	
	public static void fireChoiceSelectionTwoEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionTwo(timestamp);
			}
	}
	
	public static void fireChoiceSelectionNullEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionNull(timestamp);
			}
	}
	
	public static void fireChoiceSelectionCorrectEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionCorrect(timestamp);
			}
	}
	
	public static void fireChoiceSelectionIncorrectEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionIncorrect(timestamp);
			}
	}
	
	public static void fireChoiceSelectionDefaultCorrectEvent(long timestamp,
			List<?extends ChoiceEventListener> choiceEventListeners,
			TrialContext currentContext) {
		
			for (ChoiceEventListener listener: choiceEventListeners) {
				listener.choiceSelectionDefaultCorrect(timestamp);
			}
	}
}
