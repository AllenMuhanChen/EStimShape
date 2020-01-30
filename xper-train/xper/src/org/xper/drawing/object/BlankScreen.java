package org.xper.drawing.object;

import java.util.List;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public class BlankScreen implements Drawable {
	
	@Dependency
	List<Integer> clearBufferList;
	
	int clearMask = GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT;

	/**
	 * @param context ignored.
	 */
	public void draw(Context context) {
		GL11.glClear(clearMask);
	}
	
	public List<Integer> getClearBufferList() {
		return clearBufferList;
	}

	public void setClearBufferList(List<Integer> clearBufferList) {
		this.clearBufferList = clearBufferList;

		this.clearMask = this.clearBufferList.get(0);
		for (int i = 1; i < this.clearBufferList.size(); i++) {
			this.clearMask |= this.clearBufferList.get(i);
		}
	}
}
