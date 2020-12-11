function EStimOn_msg_struct = ParseXML_behmsg_EStimOn(EStimOn_msg)
EStimOn_msg_struct = struct;
EStimOn_msg_string = EStimOn_msg{1};

%timestamp
name1 = '<timestamp>';
name2 = '</timestamp>';
indx1 = strfind(EStimOn_msg_string, name1);
indx2 = strfind(EStimOn_msg_string, name2 );
EStimOn_msg_struct.timestamp = str2double(EStimOn_msg_string([indx1+numel(name1):indx2-1]));

%targetEyeWindowSize
name1 = '<targetEyeWindowSize>';
name2 = '</targetEyeWindowSize>';
indx1 = strfind(EStimOn_msg_string, name1);
indx2 = strfind(EStimOn_msg_string, name2 );
EStimOn_msg_struct.targetEyeWindowSize = str2double(EStimOn_msg_string([indx1+numel(name1):indx2-1]));

%eStimObjDataId
name1 = '<eStimObjDataId>';
name2 = '</eStimObjDataId>';
indx1 = strfind(EStimOn_msg_string, name1);
indx2 = strfind(EStimOn_msg_string, name2 );
EStimOn_msg_struct.eStimObjDataId = str2double(EStimOn_msg_string([indx1+numel(name1):indx2-1]));

%targetPos
name1 = '<targetPos>'; name2 = '</targetPos>';
indx1 = strfind(EStimOn_msg_string, name1);
indx2 = strfind(EStimOn_msg_string, name2);
tempstring = EStimOn_msg_string([indx1+numel(name1):indx2-1]);
name1 = '<x>'; name2 = '</x>';
indx1 = strfind(tempstring, name1);
indx2 = strfind(tempstring, name2);
targetPosx = tempstring([indx1+numel(name1):indx2-1]);
name1 = '<y>'; name2 = '</y>';
indx1 = strfind(tempstring, name1);
indx2 = strfind(tempstring, name2);
targetPosy = tempstring([indx1+numel(name1):indx2-1]);
EStimOn_msg_struct.targetPos = [str2double(targetPosx), str2double(targetPosy)];

end 