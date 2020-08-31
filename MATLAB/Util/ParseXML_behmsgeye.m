function behmsgeye_msg_struct = ParseXML_behmsgeye(behmsgeye_msg)

% targetOn_tstamp = 1598651280635894;
% targetOff_tstamp = 1598651278976121;
% sqlQuery = "SELECT msg FROM behmsgeye WHERE tstamp<"+num2str(targetOn_tstamp)+" AND tstamp>"+num2str(targetOff_tstamp);
% behmsgeye_msgs = fetch(conn,sqlQuery);
% behmsgeye_msg = string(behmsgeye_msgs.msg(1));

behmsgeye_msg_struct = struct;
behmsgeye_msg_string = behmsgeye_msg{1};

%timestamp
name1 = '<timestamp>';
name2 = '</timestamp>';
indx1 = strfind(behmsgeye_msg, name1);
indx2 = strfind(behmsgeye_msg, name2 );
behmsgeye_msg_struct.timestamp = str2double(behmsgeye_msg_string([indx1+numel(name1):indx2-1]));

%id
name1 = '<id>';
name2 = '</id>';
indx1 = strfind(behmsgeye_msg, name1);
indx2 = strfind(behmsgeye_msg, name2 );
behmsgeye_msg_struct.id = behmsgeye_msg_string([indx1+numel(name1):indx2-1]);

%volt
name1 = '<volt>'; name2 = '</volt>';
indx1 = strfind(behmsgeye_msg, name1);
indx2 = strfind(behmsgeye_msg, name2);
tempstring = behmsgeye_msg_string([indx1+numel(name1):indx2-1]);
name1 = '<x>'; name2 = '</x>';
indx1 = strfind(tempstring, name1);
indx2 = strfind(tempstring, name2);
voltx = tempstring([indx1+numel(name1):indx2-1]);
name1 = '<y>'; name2 = '</y>';
indx1 = strfind(tempstring, name1);
indx2 = strfind(tempstring, name2);
volty = tempstring([indx1+numel(name1):indx2-1]);
behmsgeye_msg_struct.volt = [str2double(voltx), str2double(volty)];

%degree
name1 = '<degree>'; name2 = '</degree>';
indx1 = strfind(behmsgeye_msg, name1);
indx2 = strfind(behmsgeye_msg, name2);
tempstring = behmsgeye_msg_string([indx1+numel(name1):indx2-1]);
name1 = '<x>'; name2 = '</x>';
indx1 = strfind(tempstring, name1);
indx2 = strfind(tempstring, name2);
degreex = tempstring([indx1+numel(name1):indx2-1]);
name1 = '<y>'; name2 = '</y>';
indx1 = strfind(tempstring, name1);
indx2 = strfind(tempstring, name2);
degreey = tempstring([indx1+numel(name1):indx2-1]);
behmsgeye_msg_struct.degree = [str2double(degreex), str2double(degreey)];
end

