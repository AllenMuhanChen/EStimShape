package org.xper.sach.util;

import java.beans.PropertyVetoException;

import javax.sql.DataSource;
import javax.swing.JOptionPane;

import org.xper.exception.DbException;
import org.xper.sach.gui.model.DataSourceVO;
import org.xper.sach.gui.view.DataSourceDialog;
import org.xper.sach.vo.DataSourceLoader;

import com.mchange.v2.c3p0.ComboPooledDataSource;

public class CreateDbDataSource {

	DataSource dataSource;
	
	public CreateDbDataSource() {
		
		dataSource = makeDataSource();
	}
	
	public DataSource makeDataSource() {
				
		DataSourceLoader dsLoader = new DataSourceLoader();
		DataSourceVO initValue =  dsLoader.getDataSourceVO();
		DataSourceDialog dialog = new DataSourceDialog(null, initValue);
		
		boolean done = false;
		while (!done) {
			DataSourceVO result = dialog.showDialog();
			if (result == null) {
				return null;
			} else {
				String error = dsLoader.setAndTestDataSourceVO(result);
				if (error == null) {
					done = true;
				} else {
					JOptionPane.showMessageDialog(null, error, "Error", JOptionPane.ERROR_MESSAGE);
				}
			}
		}
		
		String jdbcUrl = "jdbc:mysql://" + dsLoader.getDataSourceVO().getHost() + "/" + dsLoader.getDataSourceVO().getDatabase();
		
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass("com.mysql.jdbc.Driver");
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
		source.setJdbcUrl(jdbcUrl);
		source.setUser(dsLoader.getDataSourceVO().getUserName());
		source.setPassword(dsLoader.getDataSourceVO().getPassword());
		dsLoader.close();
		
		return source;
		
	}
	
	public DataSource getDataSource() {
		return dataSource;
	}
	
	
}
