function stimObjData_struct = ParseXML_stimObjData(stimObjData_spec)

% targetOn_tstamp = 1598651280635894;
% targetOff_tstamp = 1598651278976121;
% sqlQuery = "SELECT msg FROM behmsgeye WHERE tstamp<"+num2str(targetOn_tstamp)+" AND tstamp>"+num2str(targetOff_tstamp);
% behmsgeye_msgs = fetch(conn,sqlQuery);
% behmsgeye_msg = string(behmsgeye_msgs.msg(1));

stimObjData_struct = struct;
stimObjData_spec_string = stimObjData_spec{1};

%xCenter
name1 = '<xCenter>';
name2 = '</xCenter>';
indx1 = strfind(stimObjData_spec, name1);
indx2 = strfind(stimObjData_spec, name2);
stimObjData_struct.xCenter = str2double(stimObjData_spec_string([indx1+numel(name1):indx2-1]));

%yCenter
name1 = '<yCenter>';
name2 = '</yCenter>';
indx1 = strfind(stimObjData_spec, name1);
indx2 = strfind(stimObjData_spec, name2);
stimObjData_struct.yCenter = str2double(stimObjData_spec_string([indx1+numel(name1):indx2-1]));

%size
name1 = '<size>';
name2 = '</size>';
indx1 = strfind(stimObjData_spec, name1);
indx2 = strfind(stimObjData_spec, name2);
stimObjData_struct.size = str2double(stimObjData_spec_string([indx1+numel(name1):indx2-1]));

%brightness
name1 = '<brightness>';
name2 = '</brightness>';
indx1 = strfind(stimObjData_spec, name1);
indx2 = strfind(stimObjData_spec, name2);
stimObjData_struct.brightness = str2double(stimObjData_spec_string([indx1+numel(name1):indx2-1]));


end

