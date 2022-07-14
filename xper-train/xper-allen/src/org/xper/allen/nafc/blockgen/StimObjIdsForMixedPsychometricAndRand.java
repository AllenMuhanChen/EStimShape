package org.xper.allen.nafc.blockgen;

import java.util.List;

public class StimObjIdsForMixedPsychometricAndRand implements StimObjIds {
	public Long sampleId;
	public Long matchId;
	public List<Long> allDistractorsIds;
	public List<Long> psychometricDistractorsIds;
	public List<Long> randDistractorsIds;

	public StimObjIdsForMixedPsychometricAndRand(List<Long> allDistractorsIds, List<Long> psychometricDistractorsIds,
			List<Long> randDistractorsIds) {
		this.allDistractorsIds = allDistractorsIds;
		this.psychometricDistractorsIds = psychometricDistractorsIds;
		this.randDistractorsIds = randDistractorsIds;
	}

	@Override
	public Long getSampleId() {
		return sampleId;
	}

	public void setSampleId(Long sampleId) {
		this.sampleId = sampleId;
	}

	@Override
	public Long getMatchId() {
		return matchId;
	}

	public void setMatchId(Long matchId) {
		this.matchId = matchId;
	}

	@Override
	public List<Long> getAllDistractorsIds() {
		return allDistractorsIds;
	}

	public void setAllDistractorsIds(List<Long> allDistractorsIds) {
		this.allDistractorsIds = allDistractorsIds;
	}

	public List<Long> getPsychometricDistractorsIds() {
		return psychometricDistractorsIds;
	}

	public void setPsychometricDistractorsIds(List<Long> psychometricDistractorsIds) {
		this.psychometricDistractorsIds = psychometricDistractorsIds;
	}

	public List<Long> getRandDistractorsIds() {
		return randDistractorsIds;
	}

	public void setRandDistractorsIds(List<Long> randDistractorsIds) {
		this.randDistractorsIds = randDistractorsIds;
	}
}