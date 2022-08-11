package org.xper.sach.config;

import java.beans.PropertyVetoException;

import javax.sql.DataSource;
import javax.swing.JOptionPane;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;

import org.xper.config.BaseConfig;
import org.xper.exception.DbException;
import org.xper.sach.analysis.BehavAnalysisFrame;
import org.xper.sach.gui.model.DataSourceVO;
import org.xper.sach.gui.view.DataSourceDialog;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.vo.DataSourceLoader;

import com.mchange.v2.c3p0.ComboPooledDataSource;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(BaseConfig.class)
public class SachBehAnalysisConfig {
	@Autowired BaseConfig baseConfig;
	
	@Bean
	public DataSource dataSource() {
	
		String jdbcUrl = baseConfig.jdbcUrl;
		
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
		
		jdbcUrl = "jdbc:mysql://" + dsLoader.getDataSourceVO().getHost() + "/" + dsLoader.getDataSourceVO().getDatabase();
		
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass(baseConfig.jdbcDriver);
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
		source.setJdbcUrl(jdbcUrl);
		source.setUser(dsLoader.getDataSourceVO().getUserName());
		source.setPassword(dsLoader.getDataSourceVO().getPassword());
		dsLoader.close();
		
		return source;
		
		
//		// ---- ask which db to use:
//		char c = SachIOUtil.prompt("-- Use default DB '" + jdbcUrl + "'? (y/n)");
//		
//		if (c != 'y') {
//			// ask for db, set db, show db name:				
//			jdbcUrl = "jdbc:mysql://" + SachIOUtil.promptString(
//					"-- Input the requested DB url (i.e. '192.168.1.1/sach_2014_03_14_testing')\n");					
//		}
//		System.out.println("-- Using DB url: " + jdbcUrl);
//
//		ComboPooledDataSource source = new ComboPooledDataSource();
//		try {
//			source.setDriverClass(baseConfig.jdbcDriver);
//		} catch (PropertyVetoException e) {
//			throw new DbException(e);
//		}
//		source.setJdbcUrl(jdbcUrl);
//		source.setUser(baseConfig.jdbcUserName);
//		source.setPassword(baseConfig.jdbcPassword);
//		return source;
	}
	
	//@Bean
	public SachDbUtil dbUtil() {
		SachDbUtil util = new SachDbUtil();
		util.setDataSource(dataSource());
		return util;
	}
	
//	@Bean
//	public SocketTimeClient timeClient() {
//		SocketTimeClient client = new SocketTimeClient(acqServerHost);
//		return client;
//	}
	
	@Bean
	public BehavAnalysisFrame setBehavAnal() {						// used for analysis window
		BehavAnalysisFrame anal = new BehavAnalysisFrame();
		anal.setDbUtil(dbUtil());
		//anal.setGlobalTimeUtil(timeClient());
		return anal;
	}

}
