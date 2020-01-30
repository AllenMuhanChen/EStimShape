package org.xper.experiment;

import java.util.Map;

import org.xper.Dependency;
import org.xper.db.vo.SystemVariable;
import org.xper.exception.VariableNotFoundException;
import org.xper.util.DbUtil;

public class DatabaseSystemVariableContainer implements SystemVariableContainer {
	@Dependency
	DbUtil dbUtil;
	
	Map<String, SystemVariable> vars;
	
	public DatabaseSystemVariableContainer (DbUtil dbUtil) {
		this.dbUtil = dbUtil;
		this.refresh();
	}

	public String get(String name, int index) {
		SystemVariable v = vars.get(name.trim());
		if (v == null) {
			throw new VariableNotFoundException(name);
		}
		return v.getValue(index);
	}

	public void refresh() {
		vars = dbUtil.readSystemVar("%");
	}
}
