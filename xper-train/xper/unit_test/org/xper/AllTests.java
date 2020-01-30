package org.xper;

import java.awt.Dimension;
import java.awt.EventQueue;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyEvent;
import java.awt.event.WindowEvent;
import java.lang.reflect.Modifier;
import java.util.Enumeration;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.UIManager;

import junit.framework.Test;
import junit.framework.TestSuite;
import junit.runner.ClassPathTestCollector;
import junit.runner.TestCollector;

import org.apache.log4j.Logger;
import org.xper.util.GuiUtil;

public class AllTests {

	static Logger logger = Logger.getLogger(AllTests.class);
	
	static {
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e1) {}
		
		final Object done = new Object();
		
		final JFrame frame = new JFrame("Choose DAQ driver");
		frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		frame.setLocationRelativeTo(null);
		frame.setResizable(false);
		
		JPanel panel1 = new JPanel();
		panel1.setLayout(new BoxLayout(panel1, BoxLayout.LINE_AXIS));
		
		panel1.add(new JLabel("DAQ driver: "));
		panel1.add(Box.createRigidArea(new Dimension(5, 0)));
		
		final String NONE = "None";
		final String NI = "NI";
		final String COMDI = "Comedi";
		final String [] drivers = {NONE, NI, COMDI};
		final JComboBox driverList = new JComboBox(drivers);
		driverList.setSelectedIndex(0);
		driverList.setEditable(false);
		panel1.add(driverList);
		panel1.add(Box.createRigidArea(new Dimension(5, 0)));
		
		final JTextField driverName = new JTextField(10);
		driverName.setEnabled(false);
		panel1.add(driverName);
		panel1.add(Box.createRigidArea(new Dimension(5, 0)));
		
		JPanel panel2 = new JPanel ();
		panel2.setLayout(new BoxLayout(panel2, BoxLayout.LINE_AXIS));
		
		final JButton runButton = new JButton("Run Test");
		runButton.setMnemonic(KeyEvent.VK_ENTER);
		panel2.add(runButton);
		panel2.add(Box.createRigidArea(new Dimension(5, 0)));
		
		JButton exitButton = new JButton("    Exit     ");
		exitButton.setMnemonic(KeyEvent.VK_ESCAPE);
		panel2.add(exitButton);
		
		JPanel panel = new JPanel ();
		panel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
		panel.setLayout(new BoxLayout(panel, BoxLayout.PAGE_AXIS));
		
		panel.add(panel1);
		panel.add(Box.createRigidArea(new Dimension(0, 10)));
		panel.add(panel2);
		
		frame.getContentPane().add(panel);
		
		driverList.addActionListener(new ActionListener (){
			public void actionPerformed(ActionEvent e) {
				int selected = driverList.getSelectedIndex();
				if (drivers[selected].equalsIgnoreCase(NONE)) {
					driverName.setText("");
					driverName.setEnabled(false);
				} else if (drivers[selected].equalsIgnoreCase(NI)) {
					driverName.setText("Dev1");
					driverName.setEnabled(true);
				} else if (drivers[selected].equalsIgnoreCase(COMDI)) {
					driverName.setText("/dev/comedi0");
					driverName.setEnabled(true);
				}
			}});
		
		runButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent evt) {
            	int selected = driverList.getSelectedIndex();
            	if (drivers[selected].equalsIgnoreCase(NI)) {
            		System.setProperty("ni_device", driverName.getText());
            	} else if (drivers[selected].equalsIgnoreCase(COMDI)) {
            		System.setProperty("comedi_device", driverName.getText());
            	}
                synchronized (done) {
					done.notify();
				}
                EventQueue.invokeLater(new Runnable(){
					public void run() {
						frame.dispose();
					}});
            }
        });
		
		exitButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent evt) {
            	frame.dispatchEvent(new WindowEvent(frame, WindowEvent.WINDOW_CLOSING));
            }
        });
		
		GuiUtil.makeDisposeOnEscapeKey(frame);
		
		frame.pack();
		frame.setVisible(true);
		
		EventQueue.invokeLater(new Runnable(){
			public void run() {
				runButton.requestFocusInWindow();
			}});
		
		synchronized (done) {
			try {
				done.wait();
			} catch (InterruptedException e) {
			}
		}
	}

	private static class ClassFileDetector extends ClassPathTestCollector {
		protected boolean isTestClass(String classFileName) {
			return classFileName.endsWith(SUFFIX + ".class")
					&& isValidTest(classNameFromFile(classFileName));
		}
	}

	public static final String SUFFIX = "Test";
	public static final String PACKAGE_NAME = AllTests.class.getPackage()
			.getName();

	private static void addTestsToSuite(TestCollector collector, TestSuite suite) {
		Enumeration<?> e = collector.collectTests();
		while (e.hasMoreElements()) {
			String name = (String) e.nextElement();
			try {
				suite.addTestSuite(Class.forName(name));
			} catch (ClassNotFoundException e1) {
				System.err.println("Cannot load test: " + e1);
			}
		}
	}

	private static boolean isValidTest(String name) {
		try {
			Class<?> claz = Class.forName(name);
			boolean isManualTest = claz.isAnnotationPresent(ManualTest.class);
			boolean isNiTest = claz.isAnnotationPresent(NiTest.class);
			boolean isComediTest = claz.isAnnotationPresent(ComediTest.class);
			boolean isValid = name.endsWith(SUFFIX)
					&& ((claz.getModifiers() & Modifier.ABSTRACT) == 0)
					&& ((claz.getPackage().getName()
							.contains(PACKAGE_NAME)))
					&& (!claz.isAnnotation())
					&& (!isNiTest || System.getProperty("ni_device") != null )
					&& (!isComediTest || System.getProperty("comedi_device") != null )
					&& (!isManualTest);
			
			if (isValid) {
				logger.info(name);
			} else {
				if (!claz.isAnnotation()) {
					logger.info(" =============> Skip " +
						(isManualTest ? "Manual" : "") +
						(isNiTest ? "NI" : "") + 
						(isComediTest ? "Comedi" : "") +
						" Test: " + name + " <============= ");
				}
			}
			
			return isValid;
		} catch (ClassNotFoundException e) {
			System.err.println(e.toString());
			return false;
		}
	}

	public static Test suite() {
		TestSuite suite = new TestSuite(AllTests.class.getName());
		addTestsToSuite(new ClassFileDetector(), suite);
		if (suite.countTestCases() == 0) {
			throw new Error("There are no test cases to run");
		} else {
			return suite;
		}
	}
}
