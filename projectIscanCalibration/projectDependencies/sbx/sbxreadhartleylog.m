function log = sbxreadhartleylog(fname)

fn = [fname '.log_07'];
fid = fopen(fn,'r');
l = fgetl(fid);
k=0;

log = {};
while(l~=-1)
    k = str2num(l(2:end));
    log{k+1} = [];
    e = [];
    l = fgetl(fid);
    while(l~=-1 & l(1)~='T')
        e = [e ; str2num(l)];
        l = fgetl(fid);
    end
    log{k+1} = table(e(:,1),e(:,2),e(:,3),e(:,4),...
    'VariableNames',{'frame' 'sign' 'kx' 'ky'});
end

sbx = load(fname);
scanbox_frame = sbx.info.frame(2:end-1);

% add sbxframe to all logs...

k = 1;
for j = 1: length(log)
    ov_frame = log{j}.frame;
    fit = polyfit(ov_frame,scanbox_frame(k:k+length(ov_frame)-1),1);           % from ov to sbx
    t = table(floor(polyval(fit,ov_frame)),'VariableName',{'sbxframe'});
    log{j} = [log{j} t];
end

