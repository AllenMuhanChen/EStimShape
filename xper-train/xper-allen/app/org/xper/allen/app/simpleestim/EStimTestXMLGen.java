package org.xper.allen.app.simpleestim;

import java.io.File;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;

import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerConfigurationException;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.w3c.dom.Document;
import org.xper.allen.app.training.RandomCircleTrainingXMLGen;
import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.experiment.saccade.blockgen.EStimTrial;
import org.xper.allen.experiment.saccade.blockgen.TrainingTrial;
import org.xper.allen.specs.EStimObjData;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.SystemVariableContainer;

import com.thoughtworks.xstream.XStream;

/**
 * args[0]: Path of XML file to be printed
 * args[1]: number of stimuli to be desired
 * args[2]: chans: "{1,2,3,4,...}"
 * args[3]: float post_trigger_delay
 * args[4]: String trig_src
 */

public class EStimTestXMLGen extends RandomCircleTrainingXMLGen{
	transient static XStream s;
	static {
		s = new XStream();
		s.alias("EStimTrial", TrainingTrial.class);

		s.setMode(XStream.NO_REFERENCES);
	}


	public static void main(String[] args) {
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		//dataSource.setUrl("jdbc:mysql://10.0.0.197/v1microstim"); //WORKATHOME
		dataSource.setUrl("jdbc:mysql://172.30.6.27/v1microstim"); //RIG
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(dataSource);
		SystemVariableContainer systemVarContainer = createSysVarContainer(dbUtil);
		double monkey_screen_width = Double.parseDouble(systemVarContainer.get("xper_monkey_screen_width", 0));
		double monkey_screen_height = Double.parseDouble(systemVarContainer.get("xper_monkey_screen_height", 0));


		//Name of File
		if (args[0].isEmpty()) {
			DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyy-MM-dd-HH-mm-ss");
			LocalDateTime now = LocalDateTime.now();
			filepath = "doc/" + dtf.format(now)+".xml";
		}else {
			filepath = args[0];
		}
		//Number of Stimuli
		int numberStimuli = Integer.parseInt(args[1]);
		//EStimObjEntry Params
		String chans = args[2];
		float post_trigger_delay = Float.parseFloat(args[3]);
		String trig_src = args[4];
		String pulse_repetition = args[5];
		int num_pulses = Integer.parseInt(args[6]);
		float pulse_train_period;
		try {
		pulse_train_period = Float.parseFloat(args[7]);
		} catch (Exception e) {
			pulse_train_period = 0;
			System.out.println("Assuming Single Pulse");
		}
		float post_stim_refractory_period = Float.parseFloat(args[8]);
		String stim_shape = args[9];
		String stim_polarity = args[10];
		float d1 = Float.parseFloat(args[11]);
		float d2 = Float.parseFloat(args[12]);
		float dp;
		try {
		dp = Float.parseFloat(args[13]);
		} catch (Exception e) {
			dp = 0;
			System.out.println("Assuming No Delay");
		}
		float a1 = Float.parseFloat(args[14]);
		float a2 = Float.parseFloat(args[15]);
		boolean enable_amp_settle = Boolean.parseBoolean(args[16]);
		float pre_stim_amp_settle;
		float post_stim_amp_settle;
		boolean maintain_amp_settle_during_pulse_train;
		try {
		pre_stim_amp_settle = Float.parseFloat(args[17]);
		post_stim_amp_settle = Float.parseFloat(args[18]);
		maintain_amp_settle_during_pulse_train = Boolean.parseBoolean(args[19]);
		} catch (Exception e) {
			pre_stim_amp_settle = 0;
			post_stim_amp_settle = 0;
			maintain_amp_settle_during_pulse_train = false;
			System.out.println("Assuming No Amp Settle");
		}
		boolean enable_charge_recovery = Boolean.parseBoolean(args[20]);
		float post_stim_charge_recovery_on;
		float post_stim_charge_recovery_off;
		try {
		post_stim_charge_recovery_on = Float.parseFloat(args[21]);
		post_stim_charge_recovery_off = Float.parseFloat(args[22]);
		} catch (Exception e) {
			post_stim_charge_recovery_on = 0;
			post_stim_charge_recovery_off = 0;
			System.out.println("Assuming no Stim Charge Recovery");
		}
		
		//Default Params
		Coordinates2D targetEyeWinCoords = new Coordinates2D(0,5);
		double targetEyeWinSize = 3;
		double duration = 3000;
		String data = "EStimOnly Test Trial";

		//Generating eStimSpec
		EStimObjDataEntry eStimSpec = new EStimObjDataEntry();
		eStimSpec.setChans(chans);
		eStimSpec.set_post_trigger_delay(post_trigger_delay);
		eStimSpec.set_trig_src(trig_src);
		eStimSpec.setPulse_repetition(pulse_repetition);
		eStimSpec.set_num_pulses(num_pulses);
		eStimSpec.set_pulse_train_period(pulse_train_period);
		eStimSpec.set_post_stim_refractory_period(post_stim_refractory_period);
		eStimSpec.set_stim_shape(stim_shape);
		eStimSpec.set_stim_polarity(stim_polarity);
		eStimSpec.set_d1(d1);
		eStimSpec.set_d2(d2);
		eStimSpec.set_dp(dp);
		eStimSpec.set_a1(a1);
		eStimSpec.set_a2(a2);
		eStimSpec.setEnable_amp_settle(enable_amp_settle);
		eStimSpec.set_pre_stim_amp_settle(pre_stim_amp_settle);
		eStimSpec.set_post_stim_amp_settle(post_stim_amp_settle);
		eStimSpec.set_maintain_amp_settle_during_pulse_train(maintain_amp_settle_during_pulse_train);
		eStimSpec.setEnable_charge_recovery(enable_charge_recovery);
		eStimSpec.set_post_stim_charge_recovery_on(post_stim_charge_recovery_on);
		eStimSpec.set_post_stim_charge_recovery_off(post_stim_charge_recovery_off);
		
		//Generating XML String
		ArrayList<EStimTrial> trialList = new ArrayList<EStimTrial>();
		for (int i=0; i<numberStimuli; i++) {
			
			
			//
			EStimTrial eStimTrial = new EStimTrial(eStimSpec, targetEyeWinCoords, targetEyeWinSize, duration, data);
			trialList.add(eStimTrial);
		}
		String XML = s.toXML(trialList);
		System.out.println(XML);
		
		//Generating XML Document
		toXmlFile(XML, filepath);

	}
	
	public static void toXmlFile(String XML, String filepath) {
		Document doc = convertStringToXMLDocument(XML);
		TransformerFactory transformerFactory = TransformerFactory.newInstance();
		try {
			Transformer transformer = transformerFactory.newTransformer();
			DOMSource source = new DOMSource(doc);
			StreamResult result = new StreamResult(new File(filepath));
			//StreamResult result = new StreamResult(new File("doc/"+filename));
			try {
				transformer.transform(source, result);
			} catch (TransformerException e) {
				e.printStackTrace();
			}
		} catch (TransformerConfigurationException e) {
			e.printStackTrace();
		}

	}
	
	
	
}