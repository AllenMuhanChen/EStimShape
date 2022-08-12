package org.xper.acq.player;

import org.xper.acq.vo.DigitalChannel;


public interface DigitalPlayer {
	public enum Type {Invalid, QuadCenter, QuadUp, QuadDown, Half, Full};
	
	/**
	 * Get the type of the channel. Different types are defined as constants in {@link DigitalChannel}
	 * 
	 * @return -1 if cannot determine the type of the channel.
	 */
	public int getType ();
	
	/**
	 * Get the first pulse before endSampleIndex going forward from current position.
	 * 
	 * @param edge Find the position of the up, down edge or center. Values defined in {@link DigitalChannel}.
	 * @param endSampleIndex
	 * @return -1 if fail to find the next pulse.
	 */
	public int nextPulse (DigitalChannel.EdgeType edge, int endSampleIndex);
	
	/**
	 * Get the first pulse after startSampleIndex going back from current position.
	 * 
	 * @param edge Find the position of the up, down edge or center. Values defined in {@link DigitalChannel}.
	 * @param startSampleIndex
	 * @return -1 if fail to find the next pulse.
	 */
	public int prevPulse (DigitalChannel.EdgeType edge, int startSampleIndex);
	
	/**
	 * Whether this digital player handles Up edge.
	 * 
	 * @return
	 */
	public boolean hasUp ();
	
	/**
	 * Whether this digital player handles Down edge.
	 * @return
	 */
	public boolean hasDown ();
	
	/**
	 * Whether this digital player handles Center of digital signal.
	 * @return
	 */
	public boolean hasCenter ();
}
