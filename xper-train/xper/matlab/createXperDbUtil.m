function [dbUtil, spikeCounter] = createXperDbUtil (host, database, user, passwd)
%Create java object to access Xper database.
dataSource = org.springframework.jdbc.datasource.DriverManagerDataSource();
dataSource.setDriverClassName('com.mysql.jdbc.Driver');
dataSource.setUrl(['jdbc:mysql://' host '/' database ]);
dataSource.setUsername(user);
dataSource.setPassword(passwd);

dbUtil = org.xper.util.DbUtil();
dbUtil.setDataSource(dataSource);

spikeCounter = org.xper.acq.counter.ClassicMarkStimExperimentSpikeCounter();
spikeCounter.setDbUtil(dbUtil);
