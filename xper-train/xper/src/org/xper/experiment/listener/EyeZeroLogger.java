package org.xper.experiment.listener;

import java.util.HashMap;
import java.util.Map;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.zero.EyeZeroMessageListener;
import org.xper.util.DbUtil;

public class EyeZeroLogger implements EyeZeroMessageListener,
		ExperimentEventListener {
	static Logger logger = Logger.getLogger(EyeZeroLogger.class);
	
	@Dependency
	DbUtil dbUtil;
	@Dependency
	Map<String, String> dbVariableMap;
	
	HashMap<String, Coordinates2D> savedZero = new HashMap<String, Coordinates2D> ();

	public void eyeZeroMessage(long timestamp, String id, Coordinates2D zero) {
		Coordinates2D z = savedZero.get(id);
		if (z == null) {
			z = new Coordinates2D();
			savedZero.put(id, z);
		}
		z.setX(zero.getX());
		z.setY(zero.getY());
		if (logger.isDebugEnabled()) {
			logger.debug(id + ": " + zero.getX() + ", " + zero.getY());
		}
	}

	public void experimentStart(long timestamp) {
	}

	public void experimentStop(long timestamp) {
		for (Map.Entry<String, Coordinates2D> ent : savedZero.entrySet()) {
			String id = ent.getKey();
			Coordinates2D value = ent.getValue();
			String dbKey = dbVariableMap.get(id);
			dbUtil.writeSystemVar(dbKey, 0, String.valueOf(value.getX()), timestamp);
			dbUtil.writeSystemVar(dbKey, 1, String.valueOf(value.getY()), timestamp);
		}
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public Map<String, String> getDbVariableMap() {
		return dbVariableMap;
	}

	public void setDbVariableMap(Map<String, String> dbVariableMap) {
		this.dbVariableMap = dbVariableMap;
	}

}
