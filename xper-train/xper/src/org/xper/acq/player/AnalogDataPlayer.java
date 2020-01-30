package org.xper.acq.player;

import java.util.List;

import org.xper.db.vo.AcqDataEntry;

public class AnalogDataPlayer implements AnalogPlayer {

	protected List<AcqDataEntry> m_data;

	protected int m_pos;

	public AnalogDataPlayer(List<AcqDataEntry> data) {
		m_data = data;
		reset();
	}

	public void reset() {
		m_pos = 0;
	}

	public boolean seekBeginWith(int sampleIndex) {
		if (m_data.size() <= 0)
			return false;

		int curIndex = getData().getSampleInd();
		if (curIndex == sampleIndex) {
			return true;
		}
		if (curIndex > sampleIndex) {
			while (getData().getSampleInd() >= sampleIndex) {
				if (!rewind())
					return false;
			}
			forward();
		} else {
			while (getData().getSampleInd() < sampleIndex) {
				if (!forward())
					return false;
			}
		}
		return true;

	}

	public boolean seekEndWith(int sampleIndex) {
		if (m_data.size() <= 0)
			return false;

		int curIndex = getData().getSampleInd();
		if (curIndex > sampleIndex) {
			while (getData().getSampleInd() > sampleIndex) {
				if (!rewind())
					return false;
			}
		} else {
			while (getData().getSampleInd() <= sampleIndex) {
				if (!forward())
					return false;
			}
			rewind();
		}
		return true;
	}

	public int getPosition() {
		return m_pos;
	}

	/**
	 * Forward one position.
	 */
	public boolean forward() {
		if (m_pos >= m_data.size() - 1) {
			return false;
		} else {
			m_pos++;
			return true;
		}
	}

	/**
	 * Rewind one position
	 */
	public boolean rewind() {
		if (m_pos <= 0) {
			return false;
		} else {
			m_pos--;
			return true;
		}
	}

	/**
	 * Forward one position, return the data.
	 */
	public AcqDataEntry next() {
		if (forward()) {
			return getData();
		} else {
			return null;
		}
	}

	/**
	 * Rewind one position, return the data
	 */
	public AcqDataEntry prev() {
		if (rewind()) {
			return getData();
		} else {
			return null;
		}
	}

	/**
	 * Get the data at the current position.
	 */
	public AcqDataEntry getData() {
		return m_data.get(m_pos);
	}
	
	/**
	 * Get the data at pos.
	 */
	public AcqDataEntry getData (int pos) {
		return m_data.get(pos);
	}

	/**
	 * Get the last sample index of the data.
	 */
	public int getEndSampleIndex() {
		return m_data.get(m_data.size() - 1).getSampleInd();
	}
}
