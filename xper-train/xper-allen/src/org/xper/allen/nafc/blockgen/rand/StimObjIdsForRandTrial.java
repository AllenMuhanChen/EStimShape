package org.xper.allen.nafc.blockgen.rand;

import java.util.ArrayList;
import java.util.List;

public class StimObjIdsForRandTrial {
	private Long sampleId;
	private Long matchId;
	private List<Long> allDistractorIds;
	private List<Long> qmDistractorIds;
	private List<Long> randDistractorIds;

	public StimObjIdsForRandTrial() {
		this.allDistractorIds = new ArrayList<Long>();
		this.qmDistractorIds = new ArrayList<Long>();
		this.randDistractorIds = new ArrayList<Long>();
	}

	public Long getSampleId() {
		return sampleId;
	}

	public void setSampleId(Long sampleId) {
		this.sampleId = sampleId;
	}

	public Long getMatchId() {
		return matchId;
	}

	public void setMatchId(Long matchId) {
		this.matchId = matchId;
	}

	public List<Long> getAllDistractorIds() {
		return allDistractorIds;
	}

	public void setAllDistractorIds(List<Long> distractorsIds) {
		this.allDistractorIds = distractorsIds;
	}

	public List<Long> getQmDistractorIds() {
		return qmDistractorIds;
	}

	public void setQmDistractorIds(List<Long> qmDistractorIds) {
		this.qmDistractorIds = qmDistractorIds;
	}

	public List<Long> getRandDistractorIds() {
		return randDistractorIds;
	}

	public void setRandDistractorIds(List<Long> randDistractorIds) {
		this.randDistractorIds = randDistractorIds;
	}
}