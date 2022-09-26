package org.xper.util;

import java.util.ArrayList;
import java.util.List;

import org.xper.acq.counter.SessionSpikeData;
import org.xper.acq.counter.TaskSpikeDataEntry;
import org.xper.acq.counter.TrialStageData;
import org.xper.acq.player.DigitalChannelPlayer;
import org.xper.acq.player.DigitalPlayer;
import org.xper.acq.player.HalfDigitalChannelPlayer;
import org.xper.acq.player.QuadCenterDigitalChannelPlayer;
import org.xper.acq.player.QuadDownDigitalChannelPlayer;
import org.xper.acq.player.QuadUpDigitalChannelPlayer;
import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;
import org.xper.exception.InvalidAcqDataException;
import org.xper.exception.NoMoreAcqDataException;

@SuppressWarnings("deprecation")
public class AcqUtil {
	public static DigitalChannelPlayer getDigitalPlayer (List<AcqDataEntry> data, int chan, DigitalPlayer.Type type) {
		DigitalChannelPlayer player = null;
		int data_type = -1;
		switch (type) {
			case QuadCenter:
				player = new QuadCenterDigitalChannelPlayer (data, chan);
	  			data_type = player.getType();
				if (data_type != -1 && data_type != DigitalChannel.PULSE_CENTER) {
					throw new InvalidAcqDataException ("Data type invalid: " + data_type + " Expect: " + DigitalChannel.PULSE_CENTER);
				}
				return player;
			case QuadUp:
				player = new QuadUpDigitalChannelPlayer (data, chan);
	  			data_type = player.getType();
	  			if (data_type != -1 && data_type != DigitalChannel.PULSE_UP) {
	  				throw new InvalidAcqDataException ("Data type invalid: " + data_type + " Expect: " + DigitalChannel.PULSE_UP);
				}
				return player;
			case QuadDown:
				player = new QuadDownDigitalChannelPlayer (data, chan);
	  			data_type = player.getType();
	  			if (data_type != -1 && data_type != DigitalChannel.PULSE_DOWN) {
	  				throw new InvalidAcqDataException ("Data type invalid: " + data_type + " Expect: " + DigitalChannel.PULSE_DOWN);
				}
				return player;
			case Half:
				player = new HalfDigitalChannelPlayer (data, chan);
	  			data_type = player.getType();
	  			if (data_type != -1 && data_type != DigitalChannel.DOWN && data_type != DigitalChannel.UP) {
	  				throw new InvalidAcqDataException ("Data type invalid: " + data_type + " Expect: " + DigitalChannel.DOWN + " or " + DigitalChannel.UP);
				}
				return player;
			case Full:
				player = new DigitalChannelPlayer (data, chan);
	  			data_type = player.getType();
	  			if (data_type != -1 && data_type != DigitalChannel.ONE && data_type != DigitalChannel.ZERO) {
	  				throw new InvalidAcqDataException ("Data type invalid: " + data_type + " Expect: " + DigitalChannel.ONE + " or " + DigitalChannel.ZERO);
				}
				return player;
			case Invalid:
			default:
		}
		return player;

	}
	
	public static SessionSpikeData countSessionSpike (List<AcqDataEntry> acq_data, 
			int dataChan, int evenMarkerChan, int oddMarkerChan,
			DigitalPlayer.Type dataChannelType,
			DigitalPlayer.Type evenMarkerChannelType,
			DigitalPlayer.Type oddMarkerChannelType, double freq) {
		return countSessionSpike(acq_data, 
				dataChan, evenMarkerChan, oddMarkerChan, 
				dataChannelType, evenMarkerChannelType, oddMarkerChannelType, 
				freq, Integer.MAX_VALUE);
	}
	
	/**
	 * Count spikes for one session.
	 * 
	 * @param acq_data AcqData for this session
	 * @param dataChan
	 * @param evenMarkerChan
	 * @param oddMarkerChan
	 * @param dataChannelType
	 * @param evenMarkerChannelType
	 * @param oddMarkerChannelType
	 * @param freq
	 * @param maxStages Maximum stages to count for this session.
	 * @return
	 */
	public static SessionSpikeData countSessionSpike (List<AcqDataEntry> acq_data, 
			int dataChan, int evenMarkerChan, int oddMarkerChan,
			DigitalPlayer.Type dataChannelType,
			DigitalPlayer.Type evenMarkerChannelType,
			DigitalPlayer.Type oddMarkerChannelType, double freq, int maxStages) {
		
		SessionSpikeData ret = new SessionSpikeData();
		ret.setSampleFrequency(freq);
		
		DigitalChannelPlayer data_player;
		DigitalChannelPlayer even_marker_player;
		DigitalChannelPlayer odd_marker_player;
		
		data_player = AcqUtil.getDigitalPlayer (acq_data, dataChan, dataChannelType);
		even_marker_player = AcqUtil.getDigitalPlayer (acq_data, evenMarkerChan, evenMarkerChannelType);
		odd_marker_player = AcqUtil.getDigitalPlayer (acq_data, oddMarkerChan, oddMarkerChannelType);
		if (!even_marker_player.hasUp() || !odd_marker_player.hasUp() ||
				!even_marker_player.hasDown() || !odd_marker_player.hasDown()) {
			throw new InvalidAcqDataException("Even and odd marker channels must record up and down edge.");
		}
		DigitalChannelPlayer [] player = new DigitalChannelPlayer[] {even_marker_player, odd_marker_player};
	
		int [] pos = new int[] {-1, -1};

		boolean doneStages = false;
		while (!doneStages) {
			try {
				doneStages = AcqUtil.taskAdvance(player, pos);
				TaskSpikeDataEntry s = AcqUtil.countSpike (data_player, pos, freq, 0, 0);
				TrialStageData d = new TrialStageData();
				d.setSpikeData(s.getSpikeData());
				d.setStartSampleIndex(s.getStartSampleIndex());
				d.setStopSampleIndex(s.getStopSampleIndex());
				ret.addTrialStageData(d);
				ret.addSpikePerSec(s.getSpikePerSec());
				
				if (ret.getTrialStageData().size() >= maxStages) {
					break;
				}
			} catch (NoMoreAcqDataException e) {
				break;
			}
		}
		
		return ret;
	}
	
	/**
	 * Advance one task, get back the start and stop positions of the stimulus.
	 *  
	 * @param player player[0] is the current player, player[1] is the next player
	 * @param pos pos[0] is start position, pos[1] is stop position
	 * 
	 * @return true if this session is done, pos[] returned specifies the last phase.
	 */
	
	public static boolean taskAdvance (DigitalChannelPlayer[] player, int [] pos) {
	   pos[0] = player [0].nextPulse(DigitalChannel.EdgeType.Up, Integer.MAX_VALUE);
	   int next_start = player[1].nextPulse(DigitalChannel.EdgeType.Up, Integer.MAX_VALUE);

	   if (pos[0] == -1 && next_start == -1) {
		   throw new NoMoreAcqDataException("Cannot find next stimulus in marker channel: start " + pos[0] + "; next start " + next_start + 
				   				" current player " + player[0].getPosition() + " next player " + player[1].getPosition());
	   }

	   boolean lastPhase = false;
	   // At most one of the following is true
	   if (pos[0] == -1) {
		   pos[0] = player[0].getEndSampleIndex();
		   lastPhase = true;
	   }
	   if (next_start == -1) {
		   next_start = player[1].getEndSampleIndex();
		   lastPhase = true;
	   }

	   // switch player if next stimulus happen in the other marker channel
	   if (next_start < pos[0]) {
		   DigitalChannelPlayer temp_player = player[0];
		   player[0] = player[1];
		   player[1] = temp_player;

		   int temp = pos[0];
		   pos[0] = next_start;
		   next_start = temp;
	   }

	   int next_down = player[1].lookAhead(DigitalChannel.EdgeType.Down);
	   if (next_down == -1) {
		   player[0].seekEndWith(player[0].getEndSampleIndex());
		   pos[1] = player[0].prevPulse(DigitalChannel.EdgeType.Down, pos[0]);
		   if (pos[1] == -1 || pos[0] >= pos[1]) {
			   pos[1] = player[0].getEndSampleIndex();
			   player[0].seekEndWith(pos[1]);
		   }
	   } else {
		   player[0].seekEndWith((next_start+next_down)/2);
		   pos[1] = player[0].prevPulse(DigitalChannel.EdgeType.Down, pos[0]);
		   if (pos[1] == -1 || pos[0] >= pos[1]) {
			   // This could happen if the some program crashes leaving one of the AcqSessions unclosed (with stop time as Maximum Long Integer Value).
			   throw new InvalidAcqDataException ("AcqData corrupted or one of the AcqSessions is not closed: start " + pos[0] + " stop " + pos[1]);
		   }
	   }
	   
	   /*if (pos[0] >= pos[1]) {
		   if (!lastPhase) {
			   // This could happen if the some program crashes leaving one of the AcqSessions unclosed (with stop time as Maximum Long Integer Value).
			   throw new InvalidAcqDataException ("AcqData corrupted or one of the AcqSessions is not closed: start " + pos[0] + " stop " + pos[1]);
		   } else {
			   // Last phase could possible missing the down edge, use end sample index instead of the down edge index.
			   pos[1] = next_start;
		   }
	   }*/
	   
	   // Next stimulus should happen in the other marker channel
	   DigitalChannelPlayer temp_player = player[0];
	   player[0] = player[1];
	   player[1] = temp_player;
	   
	   return lastPhase;
	}
	
	/**
	 * Get the spike information for one task.
	 * 
	 * @param data_player
	 * @param pos
	 * @param freq
	 * @param leftMove Move the left edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabilization time et al.
	 * @param rightMove Move the right edge of the stimulus data frame in ms, can be negative or positive to account for response latency, stabilization time et al.
	 */
	public static TaskSpikeDataEntry countSpike (DigitalChannelPlayer data_player, int [] pos, double freq, double leftMove, double rightMove) {
		TaskSpikeDataEntry ent = new TaskSpikeDataEntry ();
		
		int leftDisp = (int)(leftMove * freq / 1000.0 + 0.5);
		int rightDisp = (int)(rightMove * freq / 1000.0 + 0.5);
		List <Integer> samples = new ArrayList<Integer>();
		int left = pos[0]+leftDisp;
		int right = pos[1] + rightDisp;
		
		data_player.seekBeginWith(left);
		int sampleInd = data_player.nextPulse(DigitalChannel.EdgeType.Center, right);
		while ( sampleInd != -1) {
			samples.add(sampleInd);
			sampleInd = data_player.nextPulse(DigitalChannel.EdgeType.Center, right);
		}
		double spike_rate = 0;
		if (right > left) {
			spike_rate = (double) (samples.size()) / ((double) (right - left) / (double)(freq));
		}
		ent.setStartSampleIndex(left);
		ent.setStopSampleIndex(right);
		ent.setSampleFrequency(freq);
		ent.setSpikePerSec(spike_rate);
		ent.setSpikeData(new int[samples.size()]);
		for (int i = 0; i < samples.size(); i ++) {
			ent.getSpikeData()[i] = samples.get(i);
		}
		return ent;
	}

}
