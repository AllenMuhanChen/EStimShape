package org.xper.util;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.List;

import org.xper.db.vo.BehMsgEntry;

import junit.framework.TestCase;

public class SocketUtilTest extends TestCase {
	public void testEncodeDecode() throws IOException {
		ByteArrayOutputStream buf = new ByteArrayOutputStream();
		BehMsgEntry inMsg1 = new BehMsgEntry();
		inMsg1.setMsg("test message 1");
		inMsg1.setType("type 1");
		BehMsgEntry inMsg2 = new BehMsgEntry();
		inMsg2.setMsg("test message 2");
		inMsg2.setType("type 2");
		buf.write(SocketUtil.encodeBehMsgEntry(inMsg1));
		buf.write(SocketUtil.encodeBehMsgEntry(inMsg2));
		buf.close();
		
		List<BehMsgEntry> outMsg = SocketUtil.decodeBehMsgEntry(buf.toByteArray());
		
		assertEquals(2, outMsg.size());
		assertEquals(inMsg1.getMsg(), outMsg.get(0).getMsg());
		assertEquals(inMsg2.getMsg(), outMsg.get(1).getMsg());
	}
}
