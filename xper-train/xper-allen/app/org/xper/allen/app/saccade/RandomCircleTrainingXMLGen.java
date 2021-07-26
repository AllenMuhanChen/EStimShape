package org.xper.allen.app.saccade;

import java.io.File;
import java.io.StringReader;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.concurrent.ThreadLocalRandom;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerConfigurationException;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.w3c.dom.Document;
import org.xml.sax.InputSource;
import org.xper.allen.saccade.blockgen.TrainingTrial;
import org.xper.allen.specs.GaussSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.DatabaseSystemVariableContainer;
import org.xper.experiment.SystemVariableContainer;
import com.thoughtworks.xstream.XStream;

/**
 * Generates stimuli based on random parameters. In this case: 1) random location & 2) random brightness. 
 * @param args[0]: Path of XML file to be printed
 * 		  args[1]: number of stimuli desired<br>
 * 		  args[2]: range of brightness of stimuli desired (between 0 and 1) <br>
 * 		  args[3]: range of size of stimuli desired (diameter in visual angles)<br>
 * 		  args[4]: The range of radius away from the center of the screen that the stimulus should be. 
 * 		  args[5]: range of durations desired. 
 * 		  args[6]: Size of targetEyeWinSize in radius degrees of visual angle 
 * 		  args[7]: String for "Data" column of StimObjData 
 * @author allenchen
 *
 */
public class RandomCircleTrainingXMLGen {
	protected static ArrayList<Double> xLim = new ArrayList<Double>();
	protected static ArrayList<Double> yLim = new ArrayList<Double>();
	protected static String filepath;
	transient static XStream s;
	static {
		s = new XStream();
		s.alias("VisualTrial", TrainingTrial.class);

		s.setMode(XStream.NO_REFERENCES);
	}
	protected static double distance;
	
	public static void main(String[] args) {
	//DB set-up
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
		distance = Double.parseDouble(systemVarContainer.get("xper_monkey_screen_distance", 0));
		
	//Arguments
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
		//Brightness Range
		ArrayList<Double> brightnessLim = argsToArrayListDouble(args[2]);
		//Size Range
		ArrayList<Double> sizeLim = argsToArrayListDouble(args[3]);
		//Location Range
		System.out.println("The Screen is: "+mm2deg(monkey_screen_width/2) + "x" + mm2deg(monkey_screen_height) + "in visual degrees");
		ArrayList<Double> radiusLim = argsToArrayListDouble(args[4]);
		//Duration Range
		ArrayList<Double> durationLim = argsToArrayListDouble(args[5]);
		//TargetEyeWinSize 
		double targetEyeWinRadius = Double.parseDouble(args[6]);
		//Data
		String data = args[7];
		
	//Generating XML String
		ArrayList<TrainingTrial> trialList = new ArrayList<TrainingTrial>();
		for (int i=0; i<numberStimuli; i++) {
			
			//GaussSpec
			double randSize = inclusiveRandomDouble(sizeLim.get(0), sizeLim.get(1));
			ArrayList<Double> randXY = randomWithinRadius(radiusLim);
			double randXCenter = randXY.get(0);
			double randYCenter = randXY.get(1); 
			double randBrightness = inclusiveRandomDouble(brightnessLim.get(0), brightnessLim.get(1));
			
			//StimSpec
			double randDuration = inclusiveRandomDouble(durationLim.get(0),durationLim.get(1));
			//targetEyeWinSize
			double targetEyeWinSize = targetEyeWinRadius;

			
			//targetEyeWinCoords
			Coordinates2D targetEyeWinCoords = new Coordinates2D(randXCenter, randYCenter);
			
			//Generating Trial Object to be added to trialList that will be Serialized
			GaussSpec randGaussSpec = new GaussSpec(randXCenter, randYCenter, randSize, randBrightness);
			TrainingTrial randVisualTrial = new TrainingTrial(randGaussSpec, randDuration, targetEyeWinCoords, targetEyeWinSize, data);
			trialList.add(randVisualTrial);
		}
		String XML = s.toXML(trialList);
		System.out.println(XML);
		
	//Generating XML Document
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
	
	public static double inclusiveRandomDouble(double val1, double val2) {
		if (val2>val1){
			return ThreadLocalRandom.current().nextDouble(val1, val2);
		}
		else {
			return val1;
		}

	}
	
	public static ArrayList<Double> randomWithinRadius(ArrayList<Double> radiusLim) {
		
		double r = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * (radiusLim.get(1)-radiusLim.get(0)) + radiusLim.get(0);
		double theta = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
		
		double x = 0 + r * Math.cos(theta);
		double y = 0 + r * Math.sin(theta);
		ArrayList<Double> output = new ArrayList<Double>(); 
		output.add(x); 
		output.add(y);
		return output;
	}
	
	public static SystemVariableContainer createSysVarContainer(AllenDbUtil dbUtil) {
		return new DatabaseSystemVariableContainer(dbUtil);
	}
	
	public static ArrayList<Double> argsToArrayListDouble(String arg){
		String[] elements = arg.split(",");
		ArrayList<Double> output = new ArrayList<Double>();
		for (String s:elements) {
			output.add(Double.parseDouble(s));
		}
		return output;
	}

	public static Document convertStringToXMLDocument(String XML) {
		DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
		DocumentBuilder builder = null;
		try {
			builder = factory.newDocumentBuilder();
			Document doc = builder.parse(new InputSource(new StringReader(XML)));
			return doc;
		}
		catch(Exception e) {
			e.printStackTrace();
		}
		return null;
	}
	
	public static double mm2deg(double mm) {
		return Math.atan(mm / distance) * 180.0 / Math.PI;
	}
}
