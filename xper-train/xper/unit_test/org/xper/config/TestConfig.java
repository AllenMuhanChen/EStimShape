package org.xper.config;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.exception.DbException;
import org.xper.util.DbUtil;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class TestConfig {

    @ExternalValue("test.jdbc.driver")
    public String jdbcDriver;

    @ExternalValue("test.jdbc.url")
    public String jdbcUrl;

    @ExternalValue("test.jdbc.username")
    public String jdbcUserName;

    @ExternalValue("test.jdbc.password")
    public String jdbcPassword;

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


}
