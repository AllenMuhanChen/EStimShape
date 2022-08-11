package org.xper.sach.gui.view;

import java.util.List;

import javax.swing.table.AbstractTableModel;

import org.xper.db.vo.AcqSessionEntry;
import org.xper.sach.gui.model.XperLauncherModel;

public class AcqSessionTableModel extends AbstractTableModel {
	private static final long serialVersionUID = -8029930615916700534L;
	String [] columnNames = {"Start Time", "Stop Time"};
	List<AcqSessionEntry> rows;
	
	XperLauncherModel model;
	
	public AcqSessionTableModel(XperLauncherModel model) {
		this.model = model;
		rows = model.getDbUtil().readAcqSession(0, Long.MAX_VALUE);
	}
	
	public String getColumnName(int column) {
		return columnNames[column];
	}
	
	public void filter (long start, long stop) {
		rows = model.getDbUtil().readAcqSession(start, stop);
	}

	public int getColumnCount() {
		return columnNames.length;
	}

	public int getRowCount() {
		return rows.size();
	}

	public Object getValueAt(int row, int col) {
		AcqSessionEntry r = (AcqSessionEntry)rows.get(row);
		if (r == null) {
			return "";
		}
		switch(col) {
			case 0:
				return r.getStartTime();
			case 1:
				return r.getStopTime();
			default:
				return "";
		}
	}

	@Override
	public Class<?> getColumnClass(int columnIndex) {
		return Long.class;
	}

}
