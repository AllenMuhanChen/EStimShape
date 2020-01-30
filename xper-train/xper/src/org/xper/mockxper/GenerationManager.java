package org.xper.mockxper;

import org.xper.Dependency;
import org.xper.db.vo.GenerationInfo;
import org.xper.util.DbUtil;

/**
 * Factory class for {@link MockGeneration}.
 *
 */
public class GenerationManager {
	@Dependency
	DbUtil dbUtil;
	
	public GenerationManager (DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	
	/**
	 * Get the current ready generation in database.
	 * 
	 */
	
	public MockGeneration getCurrentGenerationInDb () {
		GenerationInfo newGenDef = dbUtil.readReadyGenerationInfo();
		MockGeneration newGen = new MockGeneration(newGenDef);
		newGen.setDbUtil(dbUtil);
		return newGen;
	}
}
