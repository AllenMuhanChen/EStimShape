package org.xper.sach.vo;


import java.util.prefs.Preferences;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.sach.gui.model.DataSourceVO;
import org.xper.sach.time.IndexedJdkTimeUtil;
import org.xper.util.DbUtil;


public class DataSourceLoader {
	
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
	
	public DataSourceLoader() {
		loadDataSourceParameters();
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
		} 
		return dbUtil;
	}
	
	public void close() {
		saveDataSourceParameters();
	}
	
}
