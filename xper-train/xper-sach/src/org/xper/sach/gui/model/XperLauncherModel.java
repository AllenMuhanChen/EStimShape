package org.xper.sach.gui.model;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeSet;
import java.util.prefs.BackingStoreException;
import java.util.prefs.Preferences;

import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.db.vo.SystemVariable;
import org.xper.sach.gui.exception.ConfigException;
import org.xper.sach.time.IndexedJdkTimeUtil;
import org.xper.util.DbUtil;


public class XperLauncherModel {
	
	ArrayList<VariableSet> variableSets;
	
	Map<String, SystemVariable> allVariables = new HashMap<String, SystemVariable>();
	
	DbUtil dbUtil;
	
	IndexedJdkTimeUtil timeUtil = new IndexedJdkTimeUtil();
	
	DriverManagerDataSource dataSource;
	
	String hostName;
	String database;
	String userName;
	String password;
	
	void loadDataSourceParameters() {
		Preferences prefs = Preferences.userNodeForPackage(this.getClass());
		Preferences dPrefs = prefs.node("DataSourceParameters");
		hostName = dPrefs.get("HostName", "localhost");
		database = dPrefs.get("Database", "");
		userName = dPrefs.get("UserName", "xper_rw");
		password = dPrefs.get("Password", "up2nite");
	}
	
	void saveDataSourceParameters() {
		Preferences prefs = Preferences.userNodeForPackage(this.getClass());
		Preferences dPrefs = prefs.node("DataSourceParameters");
		dPrefs.put("HostName", hostName);
		dPrefs.put("Database", database);
		dPrefs.put("UserName", userName);
		dPrefs.put("Password", password);
	}
	
	void loadVariableSets() {
		Preferences prefs = Preferences.userNodeForPackage(this.getClass());
		Preferences vPrefs = prefs.node("VariableSets");
		try {
			variableSets = new ArrayList<VariableSet>();
			String[] variableSetNames = vPrefs.childrenNames();
			for (String variableSetName : variableSetNames) {
				TreeSet<String> variableSet = new TreeSet<String>();
				variableSets.add(new VariableSet(variableSetName, variableSet));
				Preferences varPrefs = vPrefs.node(variableSetName);
				String[] variables = varPrefs.childrenNames();
				for (String variable : variables) {
					variableSet.add(variable);
				}
			}
		} catch (BackingStoreException e) {
			throw new ConfigException("Cannot load system variable sets.");
		}
	}
	
	void saveVariableSets() {
		Preferences prefs = Preferences.userNodeForPackage(this.getClass());
		Preferences vPrefs = prefs.node("VariableSets");
		try {
			String[] children = vPrefs.childrenNames();
			for (String child : children) {
				vPrefs.node(child).removeNode();
			}
			if (variableSets != null) {
				for (VariableSet ent : variableSets) {
					String variableSetName = ent.getName();
					TreeSet<String> variableSet = ent.getVariables();
					Preferences varPrefs = vPrefs.node(variableSetName);
					for(String variable : variableSet) {
						varPrefs.node(variable);
					}
				}
			}
		} catch (BackingStoreException e) {
			throw new ConfigException("Cannot save system variable sets.");
		}	
	}
	
	public XperLauncherModel() {
		loadDataSourceParameters();
		loadVariableSets();
	}
	
	public DataSourceVO getDataSourceVO () {
		return new DataSourceVO(hostName, database, userName, password);
	}
	
	/**
	 * 
	 * @param vo
	 * @return error message. null is succeed.
	 */
	public String setAndTestDataSourceVO (DataSourceVO vo) {
		hostName = vo.getHost();
		database = vo.getDatabase();
		userName = vo.getUserName();
		password = vo.getPassword();
		
		dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://" + hostName + "/" + database);
		dataSource.setUsername(userName);
		dataSource.setPassword(password);
		
		try {
			getDbUtil();
			return null;
		} catch (Exception e) {
			return e.getMessage().substring(0, 256) + "...";
		}
	}
	
	public DbUtil getDbUtil() {
		if (dbUtil == null) {
			dbUtil = new DbUtil(dataSource);
			reloadSystemVar();
		} 
		return dbUtil;
	}
	
	public void reloadSystemVar() {
		allVariables = dbUtil.readSystemVar("%");
	}
	
	public void close() {
		saveVariableSets();
		saveDataSourceParameters();
	}
	
	public VariableSet getVariableSet(String name) {
		for (VariableSet set : variableSets) {
			if (set.getName().equals(name)) {
				return set;
			}
		}
		return null;
	}
	
	public void renameVariableSet (int index, String newName) {
		variableSets.get(index).setName(newName);
	}
	
	public void insertVariableSet (int index, String name) {
		variableSets.add(index, new VariableSet(name, new TreeSet<String>()));
	}

	public void removeVariableSet (int index) {
		variableSets.remove(index);
	}

	public ArrayList<VariableSet> getVariableSets() {
		return variableSets;
	}

	public void setVariableSets(ArrayList<VariableSet> variableSets) {
		this.variableSets = variableSets;
	}

	public Map<String, SystemVariable> getAllVariables() {
		return allVariables;
	}

	public void setAllVariables(Map<String, SystemVariable> allVariables) {
		this.allVariables = allVariables;
	}

	public void writeSystemVar(String variableName, int i, String string) {
		getDbUtil().writeSystemVar(variableName, i, string, timeUtil.currentTimeMicros());
	}
	
}
