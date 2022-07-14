package org.xper.allen.nafc.blockgen;

import java.util.List;

public interface StimObjIds {

	List<Long> getAllDistractorsIds();

	Long getMatchId();

	Long getSampleId();
	
}