package org.xper.sach.analysis;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Font;
import java.awt.Image;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.ImageIcon;
import javax.swing.JTextField;

//import org.xper.sach.expt.behavior.AppConfig;
//import org.xper.sach.behavior.SachExptConfig;
//import myMathLib.JMatLinkLib;

import org.aspectj.weaver.patterns.ThisOrTargetAnnotationPointcut;
import org.springframework.config.java.context.JavaConfigApplicationContext;
//import org.xper.acq.counter.ClassicMarkStimExperimentSpikeCounter;
import org.xper.acq.counter.MarkEveryStepExperimentSpikeCounter;
import org.xper.acq.counter.TaskSpikeDataEntry;
import org.xper.db.vo.StimSpecEntry;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.Dependency;


//import shapeGen.ShapeGenForRotInv;
//import shapeGen.ShapeSpec;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;
import org.xper.sach.util.SachDbUtil;


public class SimpleHistogram {

	long startTime;
	long endTime; // these should be read from a file or cmd line later
	
	
	long[] stimIdList;
	Map<Long, FiringRasterInfo> firingInfoMap;
		//this will give us the map from stimId to firingInfo
	Map<Long, BsplineObjectSpec> shapeMap;
	Map<Long, Long> TaskId2StimId; 
	@Dependency
	SachDbUtil dbUtil;
	
	public void setDbUtil(SachDbUtil dbUtil_in) {
		this.dbUtil = dbUtil_in;
	}
	
	private void readShapeList()
	{
		//read all the task done which is in the [startTime, endTime] period
		int i;
		List<TaskDoneEntry> taskDoneList = 
				dbUtil.readTaskDoneByIdRange(startTime, endTime);		
		
		System.out.println( "task done list size  "+ taskDoneList.size());
		
		shapeMap = new  TreeMap<Long, BsplineObjectSpec>();
		firingInfoMap = new TreeMap<Long, FiringRasterInfo>();
		TaskId2StimId = new TreeMap<Long, Long>();
		stimIdList  = new long[2000];
		for (i=0; i< taskDoneList.size(); i++)
		{			
			TaskDoneEntry aTask = taskDoneList.get(i);
			System.out.print("task  " +i  +": ");
			System.out.println( aTask.getTaskId() + " " +aTask.getTstamp() + " " + aTask.getPart_done());
			if ( aTask.getPart_done() == 1)			
				System.out.println("task + " + aTask.getTaskId() + " is part done..");
			
			//this is debatable, maybe we want part_done info also?
			if ( aTask.getPart_done() == 0) // we are only interested in full done task
			{
				long stimId = dbUtil.getStimIdByTaskId(aTask.getTaskId());						
				TaskId2StimId.put(aTask.getTaskId(), stimId);
				
				if ( this.shapeMap.get(stimId) == null) // a new entry
				{
					StimSpecEntry x = dbUtil.getSpecByTaskId(aTask.getTaskId());
					String spec_str = x.getSpec();		
					BsplineObjectSpec nowSpec = BsplineObjectSpec.fromXml(spec_str);					
					shapeMap.put(stimId, nowSpec);
					stimIdList[ shapeMap.size()] = stimId;
					System.out.println("put in new shapeSpec");
//					System.out.println("the label is " + nowSpec.Label);
					FiringRasterInfo nowFiringInfo = new FiringRasterInfo();
					firingInfoMap.put(stimId,  nowFiringInfo);
				}
				else
				{
					//  System.out.println("the stim id " + stimId + " already exist");
					  // don't need to put in the shapeSpec again.
				}
			}
		}
		
		// debug, summary
		System.out.println("the # of task: "+ taskDoneList.size());
		System.out.println("# of distinct stim "+ shapeMap.size());								

		System.out.println("# of firing Info slot " + firingInfoMap.size());
	}
	
	private void readSnapShot()
	{
		 // for all the shape in Shapespec map, 
		 //we'll check if they have the snapshot in database
		 //if not generate by oGLFrame similar procedure
		int i;
		
		//initialize the drawSnapShot module
		drawSnapShotModule shotModule =
			  new drawSnapShotModule("snap shot", 200,200);
	 	
		byte[] nowImgData = null;
		int nShapeToDraw = 0;
		BsplineObjectSpec[] shapeList = new BsplineObjectSpec[1000];
		ImgBinData[] imgDataList = new ImgBinData[1000];
		for (i=1; i<= shapeMap.size(); i++)
		{
				//check if this shape need to draw (not in db yet)
				long nowId = stimIdList[i];
				shapeList[i] = shapeMap.get(nowId);							
		}
		imgDataList = shotModule.drawSnapShotBySpec(shapeList, shapeMap.size());
						
	}
	
	private void writeFiringInfo2File()
	{
		String dirName = "./matlabSimpleAnalysis/";
		String fName1 = "generic.txt";
		String fName2 = "popShape.txt";
		String fName3 = "rotInvShape.txt";
		String nowFname;
		int i, j, k, counter = 1;
		
		//1. write firing info for generic shapes
		nowFname = dirName+fName1;
		try{
				BufferedWriter out = new BufferedWriter(new FileWriter(nowFname));
				counter = 1;
	        	for (i =1; i<= shapeMap.size(); i++)
	        	{
	        		long nowId = stimIdList[i];
	        		BsplineObjectSpec nowSpec = shapeMap.get(nowId);
//	        		if ( nowSpec.Label < 59999) // all generic and blank stimulus
//	        		{
//	        			out.write(Integer.toString(i) + "   "+ Long.toString(nowId) + "  "+ Long.toString(nowSpec.Label) +" \n");
//	        			counter++;
//	        			FiringRasterInfo nowInfo = this.firingInfoMap.get(nowId);
//	        			out.write("   "+ Integer.toString(nowInfo.nTrial) + " "+ Double.toString(nowInfo.avgFiringRate)
//	        				+ " "+ Double.toString(nowInfo.standardDev) +" \n");
//	        			for ( j =0 ; j< nowInfo.nTrial; j++)
//	        			{
//	        				out.write("        " + Integer.toString(nowInfo.nSpike[j]) + "   ");	        			
//	        				for ( k =0 ;k <nowInfo.nSpike[j]; k++)
//	        					out.write( Integer.toString(nowInfo.spikeEntry[j][k]) +" ");
//	        				out.write("\n");
//	        			}
//	        		}
					        	
	        	}
	        		        
	        	out.flush();	        
		}
		catch (Exception e) 
		   { System.out.println(e);}
		
		//2. write firing info for pop-coding shapes
		nowFname = dirName+fName2;
		try{
			BufferedWriter out = new BufferedWriter(new FileWriter(nowFname));
			counter = 1;
        	for (i =1; i<= shapeMap.size(); i++)
        	{
        		long nowId = stimIdList[i];
        		BsplineObjectSpec nowSpec = shapeMap.get(nowId);
//        		if ( nowSpec.Label >= 70000 && nowSpec.Label <=79999) // all pop shapes
//        		{
//        			out.write(Integer.toString(i) + "   "+ Long.toString(nowId) + "  "+ Long.toString(nowSpec.Label) +" \n");
//        			counter++;
//        			FiringRasterInfo nowInfo = this.firingInfoMap.get(nowId);
//        			out.write("   "+ Integer.toString(nowInfo.nTrial) + " "+ Double.toString(nowInfo.avgFiringRate)
//        				+ " "+ Double.toString(nowInfo.standardDev) +" \n");
//        			for ( j =0 ; j< nowInfo.nTrial; j++)
//        			{
//        				out.write("        " + Integer.toString(nowInfo.nSpike[j]) + "   ");	        			
//        				for ( k =0 ;k <nowInfo.nSpike[j]; k++)
//        					out.write( Integer.toString(nowInfo.spikeEntry[j][k]) +"  ");
//        				out.write("\n");
//        			}
//        		}
				        	
        	}
        		        
        	out.flush();	        
		}
		catch (Exception e) 
		{ System.out.println(e);}

		
		//3. write firing info for static rotInv shapes
		//4. write firing info for animated rotInv shapes

		nowFname = dirName+fName3;
		try{
			BufferedWriter out = new BufferedWriter(new FileWriter(nowFname));
			counter = 1;
        	for (i =1; i<= shapeMap.size(); i++)
        	{
        		long nowId = stimIdList[i];
        		BsplineObjectSpec nowSpec = shapeMap.get(nowId);
//        		if ( nowSpec.Label >= 80000 && nowSpec.Label <=89999) // static rot-inv
//        		{
//        			out.write(Integer.toString(i) + "   "+ Long.toString(nowId) + "  "+ Long.toString(nowSpec.Label) +" \n");
//        			counter++;
//        			FiringRasterInfo nowInfo = this.firingInfoMap.get(nowId);
//        			out.write("   "+ Integer.toString(nowInfo.nTrial) + " "+ Double.toString(nowInfo.avgFiringRate)
//        				+ " "+ Double.toString(nowInfo.standardDev) +" \n");
//        			for ( j =0 ; j< nowInfo.nTrial; j++)
//        			{
//        				out.write("        " + Integer.toString(nowInfo.nSpike[j]) + "   ");	        			
//        				for ( k =0 ;k <nowInfo.nSpike[j]; k++)
//        					out.write( Integer.toString(nowInfo.spikeEntry[j][k]) +"  ");
//        				out.write("\n");
//        			}
//        		}
				        	
        	}
        	
        	for (i =1; i<= shapeMap.size(); i++)
        	{
        		long nowId = stimIdList[i];
        		BsplineObjectSpec nowSpec = shapeMap.get(nowId);
//        		if ( nowSpec.Label >= 90000 ) // dynamic rot-inv
//        		{
//        			out.write(Integer.toString(counter) + "   "+ Long.toString(nowId) + "  "+ Long.toString(nowSpec.Label) +" \n");
//        			counter++;
//        			FiringRasterInfo nowInfo = this.firingInfoMap.get(nowId);
//        			out.write("   "+ Integer.toString(nowInfo.nTrial) + " "+ Double.toString(nowInfo.avgFiringRate)
//        				+ " "+ Double.toString(nowInfo.standardDev) +" \n");
//        			for ( j =0 ; j< nowInfo.nTrial; j++)
//        			{
//        				out.write("        " + Integer.toString(nowInfo.nSpike[j]) + "   ");	        			
//        				for ( k =0 ;k <nowInfo.nSpike[j]; k++)
//        					out.write( Integer.toString(nowInfo.spikeEntry[j][k]) +"  ");
//        				out.write("\n");
//        			}
//        		}
				        	
        	}

        		        
        	out.flush();	        
		}
		catch (Exception e) 
		{ System.out.println(e);}

		

	}
	
	public void retrieveDataFromDB()
	{
		readShapeList();
		
		//2. read/generate the snapshot from database
		   // if the snapshot exist, read it out
		   // if not exist, generate, and save to database
		readSnapShot();
		
		//3. we then can read the spike rate for task
		//    and then use taskId2StimId to register the spike rate.
		MarkEveryStepExperimentSpikeCounter spikeCounter = new MarkEveryStepExperimentSpikeCounter();
		spikeCounter.setDbUtil(dbUtil);

		int dataChan = 7;
//		SortedMap<Long, TaskSpikeDataEntry> SpikeEntry =			
//		//	spikeCounter.getTaskSpikeByGeneration(genId, dataChan, 0,0);
//			spikeCounter.getTaskSpikeByIdRange(startTime, endTime, dataChan,0,0);
						
					
//		System.out.printf("Size of SpikeEntry = %d\n", SpikeEntry.size());
//		int counter = 0;
//		for (SortedMap.Entry<Long, TaskSpikeDataEntry> entry : SpikeEntry.entrySet())
//		{
//				TaskSpikeDataEntry nowDataEntry = entry.getValue();				
//				long taskId = nowDataEntry.getTaskId();
//				double spk = nowDataEntry.getSpikePerSec();
//	
//				long stimId = TaskId2StimId.get(taskId);
//				ShapeSpec nowSpec = shapeMap.get(stimId);
//				//put in the new spike value into this stimId shape
//				//nowSpec.addSpikeRateInfo(spk);
//				
//				FiringRasterInfo nowInfo = firingInfoMap.get(stimId);
//				nowInfo.addTrial(nowDataEntry.getSpikeData(),
//						nowDataEntry.getStartSampleIndex(), nowDataEntry.getStopSampleIndex(),
//						nowDataEntry.getSpikePerSec());
//				
//				//System.out.println("Taks id " + taskId + " with spk = " + spk);
//				/*
//				counter++;
//				if ( counter < 10)
//				{
//					
//					double xbc = nowDataEntry.getStopSampleIndex() - nowDataEntry.getStartSampleIndex();
//					xbc *=40;
//					System.out.println("total ns  " + xbc);
//					
//				}
//				*/
//		}
		
		
		
		
		writeFiringInfo2File();
		
		System.out.println("");
		
		
		//debug, see the info in ShapeSpec
		
		int i;
		for (i=1; i<= shapeMap.size(); i++)
		{
				//check if this shape need to draw (not in db yet)
				long nowId = stimIdList[i];
				BsplineObjectSpec nowSpec = shapeMap.get(nowId);
				
				System.out.println("stim id : "+ nowId);
//				System.out.println("label: "+ nowSpec.Label);
				/*
				for (int j = 0; j< nowSpec.nSpikeRateCount; j++)
					System.out.print("s " + nowSpec.spikeRate_list[j]);
				System.out.println("\n avg spk:  " +nowSpec.avgSpikeRate);
				
				FiringRasterInfo nowInfo = this.firingInfoMap.get(nowId);
				for (int j =0 ; j< nowInfo.nTrial; j++)
				{
					System.out.println("s " + nowInfo.spikeRate[j]);
					for (int k =0 ;k <nowInfo.nSpike[j]; k++)
						System.out.print( nowInfo.spikeEntry[j][k] +"  ");
				}
				System.out.println("\n avg spk " + nowInfo.avgFiringRate);	
				 */
		}
		
		
	}
	
	public void showSimpleHistogram()
	{
				
		System.out.println("Show simple histogram analysis");
		
		//debug
		
		startTime = 1229014195192000L;
		
		endTime =   2229014195196000L;
		
		startTime =  1229380332545000L;
		endTime =    2229375191109000L;
	
		GUI_SimpleHistogram gui_frame = new GUI_SimpleHistogram();		
		gui_frame.setParent(this);
		gui_frame.gox();
	
		
		
	}
	
	public static void main(String[] args) 
	{
		GUI_SimpleHistogram gui_frame = new GUI_SimpleHistogram();
		
		//gui_frame.setParent(this);
		gui_frame.gox();
		
	}
}


//class GUI_SimpleHistogram implements ActionListener  
//{		
//	//JButton bt1, bt2, bt3, bt4, bt5, bt6, bt7;
//	JButton retrieveTimeBtn;
//	JButton showPopRespBtn;
//	JButton showTop20RespBtn;
//	JButton showAllRespBtn;
//	JButton showRotInvRespBtn;
//	JLabel myLabel;
//	JPanel aPanel;
//	JFrame main_frame;
//	//bt1, generate static shape
//	//bt2, generate animated shape
//	//bt3, switch the showing length design
//	
//	// Create a text field with some initial text
//    JTextArea textfield;
//    JScrollPane scrollPane;
//	SimpleHistogram simpHistFather;
//	
//    JTextField starttime_field;
//    JTextField endtime_field;
//    JLabel starttime_label, endtime_label;
//	
//    public void setParent(SimpleHistogram in_obj)
//    {
//    	this.simpHistFather = in_obj;
//    }
//    
//	public void gox()
//	{	
//		Font nowFont = new Font("Serif", Font.BOLD, 18);
//		main_frame = new JFrame();
//		main_frame.setTitle("Simple Statistics Viewing Center");
//		//main_frame.setBounds(10, 10, 900, 700);
//		aPanel = new JPanel();
//		aPanel.setBackground( Color.GRAY);
//
//		aPanel.setBounds(0,0,1000,1000);
//		aPanel.setLayout(null);
//		
//		main_frame.getContentPane().add(BorderLayout.CENTER, aPanel);
//	
//
//		// two textField to input the start, and end time
//		starttime_label = new JLabel("Start Time:");
//		starttime_label.setBounds(50 , 20, 100, 30);
//		starttime_label.setFont(nowFont);
//		endtime_label = new JLabel("End Time:");
//		endtime_label.setBounds(250, 20, 100,30);
//		endtime_label.setFont(nowFont);
//		
//		starttime_field = new JTextField("0");
//		starttime_field.setBounds(50, 60, 150, 30);
//		endtime_field = new JTextField("0");
//		endtime_field.setBounds(250, 60, 150, 30);
//		
//		aPanel.add(starttime_label);
//		aPanel.add(endtime_label);
//		aPanel.add(starttime_field);
//		aPanel.add(endtime_field);
//
//		retrieveTimeBtn = new JButton("Retrieve");
//		retrieveTimeBtn.setBounds( 420, 60, 90,30);
//		retrieveTimeBtn.addActionListener(this);
//		aPanel.add(retrieveTimeBtn);
//
//		showPopRespBtn = new JButton("Pop Resp");
//		showPopRespBtn.setBounds(50,110, 120,30);
//		showPopRespBtn.addActionListener(this);
//		aPanel.add(showPopRespBtn);
//	
//		showTop20RespBtn = new JButton("Top 20 Resp");
//		showTop20RespBtn.setBounds(50,160, 120,30);
//		showTop20RespBtn.addActionListener(this);
//		aPanel.add(showTop20RespBtn);
//		
//	    showAllRespBtn = new JButton("All Resp");
//	    showAllRespBtn.setBounds(50,210,120,30);
//	    showAllRespBtn.addActionListener(this);
//	    aPanel.add(showAllRespBtn);
//	    
//		showRotInvRespBtn = new JButton("Rot Inv");
//		showRotInvRespBtn.setBounds(50,260,120,30);
//		showRotInvRespBtn.addActionListener(this);
//		aPanel.add(showRotInvRespBtn);
//		
//		
//		textfield = new JTextArea("Init the program...");		
//		textfield.setFont(nowFont);
//	    scrollPane = new JScrollPane(textfield);
//	    scrollPane.setBounds(600, 300, 400, 400);
//	    aPanel.add(scrollPane);
//	  /*
//		bt1 = new JButton("Gen Rnd Static Shape");
//		bt1.setBounds(10,10, 200,40);
//		bt2 = new JButton("Gen Rnd Animated Shape");
//		bt2.setBounds(10,70,200,40);
//		
//		bt3 = new JButton("Switch Trial Setup");
//		bt3.setBounds(10,250,200,40);
//		
//		bt4 = new JButton("Gen 15 Static Views");
//		bt4.setBounds(10,130,200,40);
//		
//		bt5 = new JButton("Gen Animated Views");
//		bt5.setBounds(10,190,200,40);
//		
//		bt6 = new JButton("Toggle rotate alternative");
//		bt6.setBounds(10,310,200,40);
//		
//		bt7 = new JButton("Toggle rotate direction");
//		bt7.setBounds(10,370,200,40);
//
//		bt1.addActionListener(this);
//		bt2.addActionListener(this);
//		bt3.addActionListener(this);
//		bt4.addActionListener(this);
//		bt5.addActionListener(this);
//		bt6.addActionListener(this);
//		bt7.addActionListener(this);
//				
//		aPanel.add(bt1);
//		aPanel.add(bt2);
//		aPanel.add(bt3);
//		aPanel.add(bt4);
//		aPanel.add(bt5);
//		aPanel.add(bt6);
//		aPanel.add(bt7);
//		*/
//		
////		main_frame.getContentPane().add(BorderLayout.EAST, button);
////		main_frame.getContentPane().add(BorderLayout.WEST, bt2);
//		
//		main_frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
//		main_frame.setSize(1100,800);
//		main_frame.setVisible(true);
//		
//			
//			
//			
//	}
//	public void actionPerformed(ActionEvent event)
//	{
//		if (event.getSource()== retrieveTimeBtn)
//		{
//			 // get the time info from start to end
//			 //String str1 = this.starttime_field.getText();
//			 long st = Long.parseLong( starttime_field.getText());
//			 long et = Long.parseLong( endtime_field.getText());
//			 System.out.println("st: " + st);
//			 if ( st != 0)
//				 this.simpHistFather.startTime = st;
//			 if ( et != 0)
//				 this.simpHistFather.endTime = et;
//			 System.out.println("hihi");
//			 //this.simpHistFather.retrieveDataFromDB();
//			 System.out.println("hihi2");
//		     textfield.append("\nStart retrieve shape info...");
//		     System.out.println("hihi3");
//		
//		}		
//		else if ( event.getSource() == this.showPopRespBtn)
//		{
//			 textfield.append("\nShow Population resp...");
////			 JMatLinkLib.startJMatEngine();
////			 JMatLinkLib.eval("cd ./matlabSimpleAnalysis;" +
////					 " showPopResp;" + "cd ..");
//			 
//		
//		}		
//		else if ( event.getSource() == this.showTop20RespBtn)
//		{
//			 textfield.append("\nShow Top 20 resp...");
////			 JMatLinkLib.startJMatEngine();
////			 JMatLinkLib.eval("cd ./matlabSimpleAnalysis;" +
////					 " showTop20Resp;" + "cd ..");				
//		}
//		else if (event.getSource() == this.showAllRespBtn) 
//		{
//			textfield.append("\nShow All resp...");
////			JMatLinkLib.startJMatEngine();
////			JMatLinkLib.eval("cd ./matlabSimpleAnalysis;" +
////					 " showAllResp;" + "cd ..");
//		}
//		
//		else if ( event.getSource() == this.showRotInvRespBtn) 
//		{
//			textfield.append("\nShow Rotation Inv analysis...");		
//		}
//		/*
//		else if ( event.getSource() == bt6)
//		{
//		
//			textfield.append("\n change rotate o");
//		}
//		else if ( event.getSource() == bt7)
//		{
//		
//			textfield.append("\n change rotate dir CW to ");
//		}
//		*/
//	}
//
//	    
//	public void addPicture(byte[] picImgByte)
//	{
//		 int x = 100, y = 600;
//		 ImageIcon imgIcon = new ImageIcon( picImgByte);
//		 
//		 //try to scale
//		 Image tempImg = imgIcon.getImage();
//		 int hints = Image.SCALE_AREA_AVERAGING;
//		 int width = 100;
//		 int height = 100;
//		 imgIcon = new ImageIcon( tempImg.getScaledInstance(width, height, hints));
//				 
//		 // Somewhere later in the code ...
//		 myLabel = new JLabel();		
//		 myLabel.setBounds(10, 10, width, height);
//		 
//		 //create a new window to show!
//		 myLabel.setIcon(imgIcon);
//
//		 
//
//		 JFrame frame1 = new JFrame();
//			frame1.setTitle("pic1");
//		 JPanel xPanel = new JPanel();
//		 xPanel.setBackground( Color.DARK_GRAY);
//		 
//		 xPanel.add(myLabel);
//
//		 xPanel.setBounds(0,0,400,400);
//		 xPanel.setLayout(null);
//			
//		frame1.getContentPane().add(BorderLayout.CENTER, xPanel);					
//		frame1.setSize(400,400);
//		frame1.setLocation(1300, 100);
//		frame1.setVisible(true);
//			
//
//	}
//	
//}




