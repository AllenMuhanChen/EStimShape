package org.xper.allen.app.stimInserters;

import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.experiment.GaussianSpecGenerator;

//Generates ands Inserts a Specified Gauss spec into StimObjData
public class InsertGaussian {

	public static void main(String[] args) {
		//Setting up DataSource
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://localhost:3306/V1Microstim?useSSL=false");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");
		AllenDbUtil dbutil = new AllenDbUtil();
		dbutil.setDataSource(dataSource);
		
		//Main Code
		//Generate Gaussian
		GaussianSpecGenerator generator = new GaussianSpecGenerator();
		
		//MODIFY PARAMS HERE
		generator.setSize(100);
	
		
		//Insert
		String spec = generator.generateStimSpec();
		dbutil.writeStimObjData(0, spec, "Default Stimulus");
		System.out.println("Finished Generating");
	}

}
