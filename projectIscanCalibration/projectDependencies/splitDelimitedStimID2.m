function [prefix,run,gen,lin,stm] = splitDelimitedStimID2(descriptiveID)
	values 	= textscan(descriptiveID, '%s%s%s%s%s', 'delimiter', '_');
    
	prefix 	= values{1};
	run 	= values{2}; temp = textscan(run{1}, '%s%d', 'delimiter', '-'); run = temp{2};
    gen     = values{3}; temp = textscan(gen{1}, '%s%d', 'delimiter', '-'); gen = temp{2};
    lin     = values{4}; temp = textscan(lin{1}, '%s%d', 'delimiter', '-'); lin = temp{2};
    stm     = values{5}; temp = textscan(stm{1}, '%s%d', 'delimiter', '-'); stm = temp{2};
end

