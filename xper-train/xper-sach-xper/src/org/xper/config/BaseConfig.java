package org.xper.config;

import java.beans.PropertyVetoException;

import javax.sql.DataSource;

import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.exception.DbException;
import org.xper.experiment.DatabaseSystemVariableContainer;
import org.xper.experiment.SystemVariableContainer;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;

import com.mchange.v2.c3p0.ComboPooledDataSource;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class BaseConfig {
	
	@ExternalValue("jdbc.driver")
	public String jdbcDriver;

	@ExternalValue("jdbc.url")
	public String jdbcUrl;

	@ExternalValue("jdbc.username")
	public String jdbcUserName;

	@ExternalValue("jdbc.password")
	public String jdbcPassword;
	
	@ExternalValue("xper.native_library_path")
	public String nativeLibraryPath;

	@Bean
	public DbUtil dbUtil() {
		DbUtil util = new DbUtil();
		util.setDataSource(dataSource());
		return util;
	}

	@Bean
	public DataSource dataSource() {
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass(jdbcDriver);
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
		source.setJdbcUrl(jdbcUrl);
		source.setUser(jdbcUserName);
		source.setPassword(jdbcPassword);
		return source;
	}
	
	@Bean
	public TimeUtil localTimeUtil() {
		return new DefaultTimeUtil();
	}
	
	@Bean
	public SystemVariableContainer systemVariableContainer() {
		return new DatabaseSystemVariableContainer(dbUtil());
	}

}