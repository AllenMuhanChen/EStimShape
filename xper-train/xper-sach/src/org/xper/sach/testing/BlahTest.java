package org.xper.sach.testing;

import java.beans.PropertyVetoException;
import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.dom4j.Document;
import org.dom4j.Node;

import javax.sql.DataSource;

import org.w3c.dom.NodeList;
import org.xper.exception.DbException;
import org.xper.sach.util.ListUtil;
import org.xper.sach.util.SachMathUtil;
import org.xper.util.DbUtil;
import org.xper.util.XmlUtil;

import com.mchange.v2.c3p0.ComboPooledDataSource;


public class BlahTest {


	DbUtil dbUtil;
	
	public void setDbUtil(DbUtil dbUtil_in) {
		this.dbUtil = dbUtil_in;
	}

	public static void main(String[] args) {
		
		BlahTest test = new BlahTest();

		test.setDbUtil(test.dbUtil());
		
		long taskID = test.dbUtil.readTaskDoneMaxId(); 
		
		String spec = test.dbUtil.getSpecByTaskId(taskID).getSpec();
		System.out.println(spec);
		Document specDoc = XmlUtil.parseSpec(spec);
		
//		System.out.println(specDoc.selectSingleNode("reward").toString());
		//Node.ELEMENT_NODE

		// get list of nodes
		System.out.println(specDoc.node(0).getNodeTypeName());
		
		System.out.println(specDoc.node(0).getName());
		
		//System.out.println(specDoc.node(0).selectNodes("object").toString());

		//System.out.println(specDoc.);
		
		int[] cats = new int[2];

		List<Node> nList = ListUtil.castList(Node.class, specDoc.node(0).selectNodes("object"));
		
		for (int n = 0; n < nList.size(); n++) {
			
			Node node = nList.get(n);
			
			System.out.println(node.selectSingleNode("category").getText());

			cats[n] = Integer.parseInt(node.selectSingleNode("category").getText());			

		}
		
		
		System.out.println(Arrays.toString(cats));
		for (int m=0;m<cats.length;m++) {
			System.out.println(cats[m]);

		}

				
				
		//Node node = specDoc.selectSingleNode("doRandom");
		//System.out.println(node.toString());

		
		
	}
	
	

	// the following is to set the dbutil during testing, otherwise it is set via the config file(s)
	public DbUtil dbUtil() {
		DbUtil util = new DbUtil();
		util.setDataSource(dataSource());
		return util;
	}

	public DataSource dataSource() {
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass("com.mysql.jdbc.Driver");
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
		source.setJdbcUrl("jdbc:mysql://localhost/xper_sach_testing");
		source.setUser("xper_rw");
		source.setPassword("up2nite");
		return source;
	}

	
	
}
