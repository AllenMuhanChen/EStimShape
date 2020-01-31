/*
package org.xper.allen.config;

import org.xper.config.BaseConfig;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class AllenConfig extends BaseConfig{
	
	@Bean
	public AllenDbUtil allenDbUtil() {
		AllenDbUtil util = new AllenDbUtil();
		util.setDataSource(dataSource());
		return util;
	}
}
*/
package org.xper.allen.config;


import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class AllenConfig {
	@Autowired BaseConfig baseConfig;
		
	@Bean
	public AllenDbUtil allenDbUtil() {
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(baseConfig.dataSource());
		
		return dbUtil;
	}

}