package org.xper.sach.util;


import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.Circle;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.sach.vo.SachExperimentState;
import org.xper.sach.vo.SachTrialContext;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.ThreadUtil;

import javax.sound.midi.*;

public class SachExperimentUtil {
	
	public static boolean isTargetOn (SachTrialContext context) {
		//if (context.getSlideIndex() == context.getCountObjects() - 1) {
		if ((context.getTargetIndex() >= 0) && (context.getSlideIndex() == context.getCountObjects() - 1)) {	// this actually asks if this is the target, and not just the last slide
			return true;
		} else {
			return false;
		}
	}

	public static boolean isLastSlide (SachTrialContext context) {
		if (context.getSlideIndex() == context.getCountObjects() - 1) {
			return true;
		} else {
			return false;
		}
	}

	public static boolean isTargetTrial (SachTrialContext context) {
		if (context.getTargetIndex() >= 0) {
			return true;
		} else {
			return false;
		}
	}

	public static void drawTargetEyeWindow(AbstractRenderer renderer, Coordinates2D pos, double size, RGBColor targetColor) {
		Circle eyeWin = new Circle();
		eyeWin.setSolid(false);

		double x = renderer.deg2mm(pos.getX());
		double y = renderer.deg2mm(pos.getY());
		double s = renderer.deg2mm(size);

		SachGLUtil.drawCircle(eyeWin, x, y, s, targetColor.getRed(), targetColor.getGreen(), targetColor.getBlue());
	}
	
	public static void waitTimeoutPenaltyDelay(SachExperimentState state, ThreadHelper threadHelper) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		
		// -shs: wait for timeout penalty delay after trial failure
		long timeout = state.getTimeoutPenaltyDelay();
		
		if (timeout > 0) {
			playNotes(timeout);
			
			long current = timeUtil.currentTimeMicros();
			System.out.println("--TIMEOUT: " + timeout + "--");
			ThreadUtil.sleepOrPinUtil(current+timeout*1000,state,threadHelper);
		}
	}
	
	public static void playNotes(long noteLevel) {
		int note = (int)Math.floor(((double)noteLevel/1425) + 75 - 1.05263);
		try {
			Synthesizer synthesizer = MidiSystem.getSynthesizer();
			synthesizer.open();
			MidiChannel channel = synthesizer.getChannels()[0];

			for (int ii=0; ii<1; ii++) {
				note--;
				try {
					channel.noteOn(note, 50);
					Thread.sleep(150);
				} catch (InterruptedException e) {
					e.printStackTrace();
				} finally {
					channel.noteOff(note);
				}
			}

		} catch (MidiUnavailableException e) {
			e.printStackTrace();
		}
	}
	
	public static void playSingleNote(int note,int time) {
		try {
			Synthesizer synthesizer = MidiSystem.getSynthesizer();
			synthesizer.open();
			MidiChannel channel = synthesizer.getChannels()[0];

			try {
				channel.noteOn(note, 50);
				Thread.sleep(time);
			} catch (InterruptedException e) {
				e.printStackTrace();
			} finally {
				channel.noteOff(note);
			}

		} catch (MidiUnavailableException e) {
			e.printStackTrace();
		}
	}
	
	
}