/**
 * 
 */
package org.xper.sach.gui.model;

public class DataSourceVO {
	String host;
	String database;
	String userName;
	String password;
	public DataSourceVO(String host, String database, String userName, String password) {
		super();
		this.host = host;
		this.database = database;
		this.userName = userName;
		this.password = password;
	}
	public String getDatabase() {
		return database;
	}
	public void setDatabase(String database) {
		this.database = database;
	}
	public String getHost() {
		return host;
	}
	public void setHost(String host) {
		this.host = host;
	}
	public String getPassword() {
		return password;
	}
	public void setPassword(String password) {
		this.password = password;
	}
	public String getUserName() {
		return userName;
	}
	public void setUserName(String userName) {
		this.userName = userName;
	}
}