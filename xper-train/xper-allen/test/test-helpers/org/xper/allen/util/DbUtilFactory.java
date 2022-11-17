package org.xper.allen.util;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.xper.exception.DbException;

import java.beans.PropertyVetoException;

public class DbUtilFactory {

    public static final String IP = "172.30.6.80";

    public static MultiGaDbUtil createGaDbUtil(String database){

        MultiGaDbUtil dbUtil = new MultiGaDbUtil();
        dbUtil.setDataSource(createDataSource(database));
        return dbUtil;
    }

    private static ComboPooledDataSource createDataSource(String database) {
        ComboPooledDataSource source = new ComboPooledDataSource();
        try {
            source.setDriverClass("com.mysql.jdbc.Driver");
        } catch (PropertyVetoException e) {
            throw new DbException(e);
        }
        source.setJdbcUrl("jdbc:mysql://" + IP + "/" + database);
        source.setUser("xper_rw");
        source.setPassword("up2nite");
        return source;
    }
}
