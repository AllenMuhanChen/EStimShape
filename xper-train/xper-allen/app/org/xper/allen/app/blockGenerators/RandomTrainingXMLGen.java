package org.xper.allen.app.blockGenerators;

import java.io.File;
import java.io.StringReader;
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
import org.xper.allen.app.blockGenerators.trials.Trial;
import org.xper.allen.specs.GaussSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.experiment.DatabaseSystemVariableContainer;
import org.xper.experiment.SystemVariableContainer;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

import com.thoughtworks.xstream.XStream;

/**
 * Generates stimuli based on random parameters. In this case: 1) random location & 2) random brightness. 
 * @param args[0]: Path of XML file to be printed
 * 		  args[1]: number of stimuli desired<br>
 * 		  args[2]: range of brightness of stimuli desired (between 0 and 1) <br>
 * 		  args[3]: range of size of stimuli desired <br>
 * 		  args[4]: size of targetWindow desired <br>
 * 		  args[5]: range of xLocations desired. If null, will default to entire screen. 
 * 		  args[6]: range of yLocations desired. If null, will default to entire screen. 
 * @author allenchen
 *
 */
public class RandomTrainingXMLGen {
	static ArrayList<Double> xLim = new ArrayList<Double>();
	static ArrayList<Double> yLim = new ArrayList<Double>();
	static XStream s = new XStream();
	
	public static void main(String[] args) {
	//DB set-up
		DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName("com.mysql.jdbc.Driver");
		dataSource.setUrl("jdbc:mysql://172.30.6.27/v1microstim");
		dataSource.setUsername("xper_rw");
		dataSource.setPassword("up2nite");
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(dataSource);
		SystemVariableContainer systemVarContainer = createSysVarContainer(dbUtil);
		double monkey_screen_width = Double.parseDouble(systemVarContainer.get("xper_monkey_screen_width", 0));
		double monkey_screen_height = Double.parseDouble(systemVarContainer.get("xper_monkey_screen_height", 0));
		TimeUtil timeUtil = new DefaultTimeUtil();
		
	//Arguments
		//Name of File
		String filepath = args[0];
		//Number of Stimuli
		int numberStimuli = Integer.parseInt(args[1]);
		//Brightness Range
		ArrayList<Double> brightnessLim = argsToArrayListDouble(args[2]);
		//Size Range
		ArrayList<Double> sizeLim = argsToArrayListDouble(args[3]);
		//Location Lims
		if (args.length == 6) { //Location Range Given
			xLim = argsToArrayListDouble(args[4]);
			yLim = argsToArrayListDouble(args[5]);
		}
		else {
			xLim.add(-1*monkey_screen_width/4); 
			xLim.add(monkey_screen_width/4);
			yLim.add(-1*monkey_screen_height/2);
			yLim.add(monkey_screen_height/2);
		}
		
	//Generating XML String
		ArrayList<GaussSpec> gaussList = new ArrayList<GaussSpec>();
		
		s.alias("GaussSpec", GaussSpec.class);
		s.setMode(XStream.NO_REFERENCES);
		
		
		for (int i=0; i<numberStimuli; i++) {
			
			//StimObjData
			ArrayList<GaussSpec> gaussSpecs = new ArrayList<GaussSpec>();
			double randXCenter = ThreadLocalRandom.current().nextDouble(xLim.get(0), xLim.get(1));
			double randYCenter = ThreadLocalRandom.current().nextDouble(yLim.get(0), yLim.get(1));
			double randSize = ThreadLocalRandom.current().nextDouble(sizeLim.get(0), sizeLim.get(1));
			System.out.println(brightnessLim.get(0));
			System.out.println(brightnessLim.get(1));
			double randBrightness = ThreadLocalRandom.current().nextDouble(brightnessLim.get(0), brightnessLim.get(1));
			
			GaussSpec randGaussSpec = new GaussSpec(randXCenter, randYCenter, randSize, randBrightness);
			gaussList.add(randGaussSpec);
		}
		String XML = s.toXML(gaussList);
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
}
