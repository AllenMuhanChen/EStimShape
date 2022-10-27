function [animal,unit,expt,genNum,stimNum] = splitDelimitedStimID(stimID)
	values 	= textscan(stimID{1}, '%s%s%s%d%d', 'delimiter', '_');
	animal 	= values{1};
	unit 	= values{2};
	expt 	= values{3};
	genNum 	= values{4};
	stimNum = values{5};	
end

