package org.xper.sach.gui.view;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JTextField;

import org.xper.sach.gui.model.DataSourceVO;

public class DataSourceDialog extends JDialog {
	
	private DataSourceVO result = null;

	private static final long serialVersionUID = 1L;

	private JPanel jContentPane = null;

	private JPanel parameterPanel = null;

	private JPanel commandPanel = null;

	private JButton okButton = null;

	private JButton cancelButton = null;

	private JLabel hostLabel = null;

	private JLabel dbLabel = null;

	private JLabel userLabel = null;

	private JLabel passwordLabel = null;

	private JTextField hostTextField = null;

	private JTextField dbTextField = null;

	private JTextField userTextField = null;

	private JPasswordField passwordField = null;

	/**
	 * @param owner
	 */
	public DataSourceDialog(Frame owner, DataSourceVO initValue) {
		super(owner, true);
		initialize();
		getHostTextField().setText(initValue.getHost());
		getDbTextField().setText(initValue.getDatabase());
		getUserTextField().setText(initValue.getUserName());
		getPasswordField().setText(initValue.getPassword());
	}

	/**
	 * This method initializes this
	 * 
	 * @return void
	 */
	private void initialize() {
		this.setSize(300, 200);
		this.setTitle("Experiment Launcher");
		this.setContentPane(getJContentPane());
		pack();
		setLocationRelativeTo(getOwner());
	}

	/**
	 * This method initializes jContentPane
	 * 
	 * @return javax.swing.JPanel
	 */
	private JPanel getJContentPane() {
		if (jContentPane == null) {
			jContentPane = new JPanel();
			jContentPane.setLayout(new BorderLayout());
			jContentPane.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
			jContentPane.add(getParameterPanel(), BorderLayout.CENTER);
			jContentPane.add(getCommandPanel(), BorderLayout.SOUTH);
		}
		return jContentPane;
	}

	/**
	 * This method initializes parameterPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getParameterPanel() {
		if (parameterPanel == null) {
			GridBagConstraints gridBagConstraints4 = new GridBagConstraints();
			gridBagConstraints4.ipady = 0;
			gridBagConstraints4.anchor = GridBagConstraints.EAST;
			gridBagConstraints4.insets = new Insets(0, 0, 5, 5);
			GridBagConstraints gridBagConstraints31 = new GridBagConstraints();
			gridBagConstraints31.gridx = 0;
			gridBagConstraints31.insets = new Insets(0, 0, 5, 5);
			gridBagConstraints31.anchor = GridBagConstraints.EAST;
			gridBagConstraints31.gridy = 3;
			GridBagConstraints gridBagConstraints21 = new GridBagConstraints();
			gridBagConstraints21.gridx = 0;
			gridBagConstraints21.insets = new Insets(0, 0, 5, 5);
			gridBagConstraints21.anchor = GridBagConstraints.EAST;
			gridBagConstraints21.gridy = 2;
			GridBagConstraints gridBagConstraints11 = new GridBagConstraints();
			gridBagConstraints11.gridx = 0;
			gridBagConstraints11.ipady = 0;
			gridBagConstraints11.insets = new Insets(0, 0, 5, 5);
			gridBagConstraints11.anchor = GridBagConstraints.EAST;
			gridBagConstraints11.gridy = 1;
			userLabel = new JLabel();
			userLabel.setText("User Name:");
			userLabel.setFont(new Font("Dialog", Font.PLAIN, 12));
			userLabel.setAlignmentX(RIGHT_ALIGNMENT);
			dbLabel = new JLabel();
			dbLabel.setText("Database:");
			dbLabel.setFont(new Font("Dialog", Font.PLAIN, 12));
			dbLabel.setAlignmentX(RIGHT_ALIGNMENT);
			hostLabel = new JLabel();
			hostLabel.setText("Host:");
			hostLabel.setAlignmentX(RIGHT_ALIGNMENT);
			hostLabel.setFont(new Font("Dialog", Font.PLAIN, 12));
			passwordLabel = new JLabel();
			passwordLabel.setText("Password:");
			passwordLabel.setFont(new Font("Dialog", Font.PLAIN, 12));
			passwordLabel.setAlignmentX(RIGHT_ALIGNMENT);
			GridBagConstraints gridBagConstraints3 = new GridBagConstraints();
			gridBagConstraints3.fill = GridBagConstraints.VERTICAL;
			gridBagConstraints3.gridx = 1;
			gridBagConstraints3.gridy = 3;
			gridBagConstraints3.insets = new Insets(0, 0, 5, 0);
			gridBagConstraints3.weightx = 1.0;
			GridBagConstraints gridBagConstraints2 = new GridBagConstraints();
			gridBagConstraints2.fill = GridBagConstraints.VERTICAL;
			gridBagConstraints2.gridx = 1;
			gridBagConstraints2.gridy = 2;
			gridBagConstraints2.insets = new Insets(0, 0, 5, 0);
			gridBagConstraints2.weightx = 1.0;
			GridBagConstraints gridBagConstraints1 = new GridBagConstraints();
			gridBagConstraints1.fill = GridBagConstraints.VERTICAL;
			gridBagConstraints1.gridx = 1;
			gridBagConstraints1.gridy = 1;
			gridBagConstraints1.ipady = 0;
			gridBagConstraints1.insets = new Insets(0, 0, 5, 0);
			gridBagConstraints1.weightx = 1.0;
			GridBagConstraints gridBagConstraints = new GridBagConstraints();
			gridBagConstraints.fill = GridBagConstraints.VERTICAL;
			gridBagConstraints.ipady = 0;
			gridBagConstraints.insets = new Insets(0, 0, 5, 0);
			gridBagConstraints.weightx = 1.0;
			parameterPanel = new JPanel();
			parameterPanel.setBorder(BorderFactory.createTitledBorder("Connect to MySQL Database"));
			parameterPanel.setLayout(new GridBagLayout());
			parameterPanel.add(hostLabel, gridBagConstraints4);
			parameterPanel.add(dbLabel, gridBagConstraints11);
			parameterPanel.add(userLabel, gridBagConstraints21);
			parameterPanel.add(passwordLabel, gridBagConstraints31);
			parameterPanel.add(getHostTextField(), gridBagConstraints);
			parameterPanel.add(getDbTextField(), gridBagConstraints1);
			parameterPanel.add(getUserTextField(), gridBagConstraints2);
			parameterPanel.add(getPasswordField(), gridBagConstraints3);
		}
		return parameterPanel;
	}

	/**
	 * This method initializes commandPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getCommandPanel() {
		if (commandPanel == null) {
			commandPanel = new JPanel();
			commandPanel.setLayout(new BoxLayout(commandPanel, BoxLayout.LINE_AXIS));
			commandPanel.add(Box.createHorizontalGlue());
			commandPanel.add(getOkButton());
			commandPanel.add(Box.createRigidArea(new Dimension(5, 0)));
			commandPanel.add(getCancelButton());
		}
		return commandPanel;
	}

	/**
	 * This method initializes okButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getOkButton() {
		if (okButton == null) {
			okButton = new JButton();
			okButton.setText("OK");
			okButton.setFont(new Font("Dialog", Font.PLAIN, 12));
			okButton.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					String host = getHostTextField().getText();
					String db = getDbTextField().getText();
					String user = getUserTextField().getText();
					String password = new String(getPasswordField().getPassword());
					result = new DataSourceVO(host, db, user, password);
					setVisible(false);
				}
			});
		}
		return okButton;
	}

	/**
	 * This method initializes cancelButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getCancelButton() {
		if (cancelButton == null) {
			cancelButton = new JButton();
			cancelButton.setFont(new Font("Dialog", Font.PLAIN, 12));
			cancelButton.setText("Cancel");
			cancelButton.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					setVisible(false);
				}
			});
		}
		return cancelButton;
	}

	/**
	 * This method initializes hostTextField	
	 * 	
	 * @return javax.swing.JTextField	
	 */
	private JTextField getHostTextField() {
		if (hostTextField == null) {
			hostTextField = new JTextField();
			hostTextField.setPreferredSize(new Dimension(200, 20));
		}
		return hostTextField;
	}

	/**
	 * This method initializes dbTextField	
	 * 	
	 * @return javax.swing.JTextField	
	 */
	private JTextField getDbTextField() {
		if (dbTextField == null) {
			dbTextField = new JTextField();
			dbTextField.setPreferredSize(new Dimension(200, 20));
		}
		return dbTextField;
	}

	/**
	 * This method initializes userTextField	
	 * 	
	 * @return javax.swing.JTextField	
	 */
	private JTextField getUserTextField() {
		if (userTextField == null) {
			userTextField = new JTextField();
			userTextField.setPreferredSize(new Dimension(200, 20));
		}
		return userTextField;
	}

	/**
	 * This method initializes passwordField	
	 * 	
	 * @return javax.swing.JPasswordField	
	 */
	private JPasswordField getPasswordField() {
		if (passwordField == null) {
			passwordField = new JPasswordField();
			passwordField.setPreferredSize(new Dimension(200, 20));
		}
		return passwordField;
	}
	
	public DataSourceVO showDialog() {
		result = null;
		setVisible(true);
		return result;
	}
}
