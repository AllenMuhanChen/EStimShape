package org.xper.sach.analysis;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Font;
import java.awt.Image;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.ImageIcon;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;

public class GUI_SimpleHistogram implements ActionListener {

	//JButton bt1, bt2, bt3, bt4, bt5, bt6, bt7;
	JButton retrieveTimeBtn;
	JButton showPopRespBtn;
	JButton showTop20RespBtn;
	JButton showAllRespBtn;
	JButton showRotInvRespBtn;
	JLabel myLabel;
	JPanel aPanel;
	JFrame main_frame;
	//bt1, generate static shape
	//bt2, generate animated shape
	//bt3, switch the showing length design

	// Create a text field with some initial text
	JTextArea textfield;
	JScrollPane scrollPane;
	SimpleHistogram simpHistFather;

	JTextField starttime_field;
	JTextField endtime_field;
	JLabel starttime_label, endtime_label;

	public void setParent(SimpleHistogram in_obj) {
		this.simpHistFather = in_obj;
	}
	
	public void gox() {	
		Font nowFont = new Font("Serif", Font.BOLD, 18);
		main_frame = new JFrame();
		main_frame.setTitle("Simple Statistics Viewing Center");
		//main_frame.setBounds(10, 10, 900, 700);
		aPanel = new JPanel();
		aPanel.setBackground( Color.GRAY);

		aPanel.setBounds(0,0,1000,1000);
		aPanel.setLayout(null);

		main_frame.getContentPane().add(BorderLayout.CENTER, aPanel);


		// two textField to input the start, and end time
		starttime_label = new JLabel("Start Time:");
		starttime_label.setBounds(50 , 20, 100, 30);
		starttime_label.setFont(nowFont);
		endtime_label = new JLabel("End Time:");
		endtime_label.setBounds(250, 20, 100,30);
		endtime_label.setFont(nowFont);

		starttime_field = new JTextField("0");
		starttime_field.setBounds(50, 60, 150, 30);
		endtime_field = new JTextField("0");
		endtime_field.setBounds(250, 60, 150, 30);

		aPanel.add(starttime_label);
		aPanel.add(endtime_label);
		aPanel.add(starttime_field);
		aPanel.add(endtime_field);

		retrieveTimeBtn = new JButton("Retrieve");
		retrieveTimeBtn.setBounds( 420, 60, 90,30);
		retrieveTimeBtn.addActionListener(this);
		aPanel.add(retrieveTimeBtn);

		showPopRespBtn = new JButton("Pop Resp");
		showPopRespBtn.setBounds(50,110, 120,30);
		showPopRespBtn.addActionListener(this);
		aPanel.add(showPopRespBtn);

		showTop20RespBtn = new JButton("Top 20 Resp");
		showTop20RespBtn.setBounds(50,160, 120,30);
		showTop20RespBtn.addActionListener(this);
		aPanel.add(showTop20RespBtn);

		showAllRespBtn = new JButton("All Resp");
		showAllRespBtn.setBounds(50,210,120,30);
		showAllRespBtn.addActionListener(this);
		aPanel.add(showAllRespBtn);

		showRotInvRespBtn = new JButton("Rot Inv");
		showRotInvRespBtn.setBounds(50,260,120,30);
		showRotInvRespBtn.addActionListener(this);
		aPanel.add(showRotInvRespBtn);


		textfield = new JTextArea("Init the program...");		
		textfield.setFont(nowFont);
		scrollPane = new JScrollPane(textfield);
		scrollPane.setBounds(600, 300, 400, 400);
		aPanel.add(scrollPane);
		/*
			bt1 = new JButton("Gen Rnd Static Shape");
			bt1.setBounds(10,10, 200,40);
			bt2 = new JButton("Gen Rnd Animated Shape");
			bt2.setBounds(10,70,200,40);

			bt3 = new JButton("Switch Trial Setup");
			bt3.setBounds(10,250,200,40);

			bt4 = new JButton("Gen 15 Static Views");
			bt4.setBounds(10,130,200,40);

			bt5 = new JButton("Gen Animated Views");
			bt5.setBounds(10,190,200,40);

			bt6 = new JButton("Toggle rotate alternative");
			bt6.setBounds(10,310,200,40);

			bt7 = new JButton("Toggle rotate direction");
			bt7.setBounds(10,370,200,40);

			bt1.addActionListener(this);
			bt2.addActionListener(this);
			bt3.addActionListener(this);
			bt4.addActionListener(this);
			bt5.addActionListener(this);
			bt6.addActionListener(this);
			bt7.addActionListener(this);

			aPanel.add(bt1);
			aPanel.add(bt2);
			aPanel.add(bt3);
			aPanel.add(bt4);
			aPanel.add(bt5);
			aPanel.add(bt6);
			aPanel.add(bt7);
		 */

		//			main_frame.getContentPane().add(BorderLayout.EAST, button);
		//			main_frame.getContentPane().add(BorderLayout.WEST, bt2);

		main_frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		main_frame.setSize(1100,800);
		main_frame.setVisible(true);

	}

	public void actionPerformed(ActionEvent event) {
		if (event.getSource()== retrieveTimeBtn)
		{
			// get the time info from start to end
			//String str1 = this.starttime_field.getText();
			long st = Long.parseLong( starttime_field.getText());
			long et = Long.parseLong( endtime_field.getText());
			System.out.println("st: " + st);
			if ( st != 0)
				this.simpHistFather.startTime = st;
			if ( et != 0)
				this.simpHistFather.endTime = et;
			System.out.println("hihi");
			//this.simpHistFather.retrieveDataFromDB();
			System.out.println("hihi2");
			textfield.append("\nStart retrieve shape info...");
			System.out.println("hihi3");

		}		
		else if ( event.getSource() == this.showPopRespBtn)
		{
			textfield.append("\nShow Population resp...");
			//				 JMatLinkLib.startJMatEngine();
			//				 JMatLinkLib.eval("cd ./matlabSimpleAnalysis;" +
			//						 " showPopResp;" + "cd ..");


		}		
		else if ( event.getSource() == this.showTop20RespBtn)
		{
			textfield.append("\nShow Top 20 resp...");
			//				 JMatLinkLib.startJMatEngine();
			//				 JMatLinkLib.eval("cd ./matlabSimpleAnalysis;" +
			//						 " showTop20Resp;" + "cd ..");				
		}
		else if (event.getSource() == this.showAllRespBtn) 
		{
			textfield.append("\nShow All resp...");
			//				JMatLinkLib.startJMatEngine();
			//				JMatLinkLib.eval("cd ./matlabSimpleAnalysis;" +
			//						 " showAllResp;" + "cd ..");
		}

		else if ( event.getSource() == this.showRotInvRespBtn) 
		{
			textfield.append("\nShow Rotation Inv analysis...");		
		}
		/*
			else if ( event.getSource() == bt6)
			{

				textfield.append("\n change rotate o");
			}
			else if ( event.getSource() == bt7)
			{

				textfield.append("\n change rotate dir CW to ");
			}
		 */
	}


	public void addPicture(byte[] picImgByte) {
		int x = 100, y = 600;
		ImageIcon imgIcon = new ImageIcon( picImgByte);

		//try to scale
		Image tempImg = imgIcon.getImage();
		int hints = Image.SCALE_AREA_AVERAGING;
		int width = 100;
		int height = 100;
		imgIcon = new ImageIcon( tempImg.getScaledInstance(width, height, hints));

		// Somewhere later in the code ...
		myLabel = new JLabel();		
		myLabel.setBounds(10, 10, width, height);

		//create a new window to show!
		myLabel.setIcon(imgIcon);



		JFrame frame1 = new JFrame();
		frame1.setTitle("pic1");
		JPanel xPanel = new JPanel();
		xPanel.setBackground( Color.DARK_GRAY);

		xPanel.add(myLabel);

		xPanel.setBounds(0,0,400,400);
		xPanel.setLayout(null);

		frame1.getContentPane().add(BorderLayout.CENTER, xPanel);					
		frame1.setSize(400,400);
		frame1.setLocation(1300, 100);
		frame1.setVisible(true);

	}
	
	public static void main(String[] args) {
		GUI_SimpleHistogram gui_frame = new GUI_SimpleHistogram();
		
		//gui_frame.setParent(this);
		gui_frame.gox();
		
	}

}